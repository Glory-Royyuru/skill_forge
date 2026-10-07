"""Learner agent: a real LLM tool-calling loop over an Environment.

Receives only the task request, tool specs, and a condition-specific
system prompt — never `task.ground_truth`, evaluator output, or
`rules_involved`. Terminates on a successful terminal action, hitting
`max_steps`, or exhausting a token/cost budget.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from skillforge.envs.base import Action, Environment, Task
from skillforge.llm.pricing import estimate_cost
from skillforge.llm.types import Message

MAX_STEPS = 15
TERMINAL_TOOLS = {"process_refund", "reject_refund", "escalate"}


@dataclass
class LearnerRun:
    trajectory: list[dict[str, Any]] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    steps_taken: int = 0
    malformed_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    stop_reason: str = "max_steps"  # terminal | max_steps | budget_exhausted


def _tool_result_text(ok: bool, output: Any, error: str | None) -> str:
    if ok:
        return str(output)
    return f"error: {error}"


def run_learner(
    env: Environment,
    task: Task,
    llm_client: Any,  # LoggingLLMClient-like: .complete(...) -> LLMResponse
    system_prompt: str,
    *,
    model: str | None = None,
    seed: int | None = None,
    max_steps: int = MAX_STEPS,
    token_budget: float | None = None,
    cost_budget: float | None = None,
) -> LearnerRun:
    env.reset(task)
    tools = env.list_tools()

    messages: list[Message] = [
        Message(role="system", content=system_prompt),
        Message(role="user", content=task.request),
    ]
    run = LearnerRun()

    for _step in range(max_steps):
        response = llm_client.complete(messages, tools=tools, model=model, temperature=0.0, seed=seed)
        run.steps_taken += 1
        run.input_tokens += response.usage.input_tokens
        run.output_tokens += response.usage.output_tokens
        run.cost += estimate_cost(response.model, response.usage.input_tokens, response.usage.output_tokens)

        if token_budget is not None and (run.input_tokens + run.output_tokens) > token_budget:
            run.stop_reason = "budget_exhausted"
            break
        if cost_budget is not None and run.cost > cost_budget:
            run.stop_reason = "budget_exhausted"
            break

        if not response.tool_calls:
            messages.append(Message(role="assistant", content=response.text or ""))
            run.messages.append({"role": "assistant", "content": response.text})
            run.stop_reason = "max_steps"
            break

        messages.append(
            Message(role="assistant", content=response.text or "", tool_calls=response.tool_calls)
        )
        run.messages.append(
            {
                "role": "assistant",
                "content": response.text,
                "tool_calls": [
                    {"id": c.id, "name": c.name, "arguments": c.arguments} for c in response.tool_calls
                ],
            }
        )

        ended = False
        for call in response.tool_calls:
            result = env.execute_action(Action(tool=call.name, args=call.arguments))
            if not result.ok:
                run.malformed_calls += 1
            run.trajectory.append(
                {
                    "tool": call.name,
                    "args": call.arguments,
                    "ok": result.ok,
                    "output": result.output,
                    "error": result.error,
                    "terminal": result.terminal,
                }
            )
            content = _tool_result_text(result.ok, result.output, result.error)
            messages.append(
                Message(
                    role="tool", tool_call_id=call.id, name=call.name, content=content, is_error=not result.ok
                )
            )
            run.messages.append(
                {"role": "tool", "tool_call_id": call.id, "name": call.name, "content": content}
            )
            if result.ok and result.terminal:
                ended = True

        if ended:
            run.stop_reason = "terminal"
            break
    return run


__all__ = ["LearnerRun", "run_learner", "TERMINAL_TOOLS"]
