"""A deterministic, scripted LLMProvider for tests and offline runs.

Every test and CI run in this repo must work with zero API keys, so
MockProvider is the default provider for teacher/learner agents unless a
real one is explicitly configured.
"""

from __future__ import annotations

import time
from typing import Any

from skillforge.llm.base import LLMProvider
from skillforge.llm.types import LLMResponse, Message, TokenUsage, ToolCall

# One scripted item is consumed per complete() call, in order. An item is
# one of:
#   - a plain string                          -> returned as response text
#   - {"text": "..."}                          -> returned as response text
#   - {"tool_calls": [{"name": ..., "arguments": {...}}, ...]}
#   - an LLMResponse                           -> returned mostly as-is
ScriptItem = str | dict[str, Any] | LLMResponse


class MockProvider(LLMProvider):
    provider_name = "mock"

    def __init__(self, script: list[ScriptItem] | None = None, model: str = "mock-model"):
        self._script: list[ScriptItem] = list(script or [])
        self._index = 0
        self._default_model = model
        # Every request this provider has seen, for assertions in tests.
        self.calls: list[dict[str, Any]] = []

    def add_response(self, item: ScriptItem) -> None:
        self._script.append(item)

    def complete(
        self,
        messages: list[Message],
        tools=None,
        model: str | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> LLMResponse:
        start = time.perf_counter()
        self.calls.append(
            {
                "messages": messages,
                "tools": tools,
                "model": model,
                "temperature": temperature,
                "seed": seed,
            }
        )
        if self._index >= len(self._script):
            raise IndexError(
                f"MockProvider script exhausted after {self._index} call(s); "
                "add more scripted responses via `script=` or `add_response()`."
            )
        item = self._script[self._index]
        self._index += 1

        resolved_model = model or self._default_model
        latency_ms = (time.perf_counter() - start) * 1000

        if isinstance(item, LLMResponse):
            item.model = item.model or resolved_model
            item.latency_ms = latency_ms
            return item

        if isinstance(item, str):
            return LLMResponse(
                text=item,
                tool_calls=[],
                usage=TokenUsage(
                    input_tokens=_estimate_tokens(messages),
                    output_tokens=_estimate_tokens_text(item),
                ),
                model=resolved_model,
                latency_ms=latency_ms,
            )

        if isinstance(item, dict):
            text = item.get("text")
            raw_tool_calls = item.get("tool_calls") or []
            tool_calls = [
                ToolCall(
                    id=tc.get("id", f"call_{i}"),
                    name=tc["name"],
                    arguments=tc.get("arguments", {}),
                )
                for i, tc in enumerate(raw_tool_calls)
            ]
            usage = item.get("usage") or TokenUsage(
                input_tokens=_estimate_tokens(messages),
                output_tokens=_estimate_tokens_text(text or ""),
            )
            return LLMResponse(
                text=text,
                tool_calls=tool_calls,
                usage=usage,
                model=resolved_model,
                latency_ms=latency_ms,
            )

        raise TypeError(f"Unsupported scripted response type: {type(item)!r}")


def _estimate_tokens_text(text: str) -> int:
    # A cheap, deterministic stand-in for a real tokenizer. MockProvider
    # never calls out to anything, so this just needs to be stable.
    return max(1, len(text) // 4) if text else 0


def _estimate_tokens(messages: list[Message]) -> int:
    return sum(_estimate_tokens_text(m.content) for m in messages)
