"""Anthropic-backed LLMProvider.

The `anthropic` package is imported lazily inside __init__ (not at module
import time) so the rest of the codebase — and the whole test suite — can
import this module without the package installed or an API key set.
"""

from __future__ import annotations

import time
from typing import Any

from skillforge.llm.base import LLMProvider
from skillforge.llm.retry import call_with_retry
from skillforge.llm.types import LLMResponse, Message, TokenUsage, ToolCall, ToolSpec

_ANTHROPIC_MAX_TOKENS_DEFAULT = 4096


class AnthropicProvider(LLMProvider):
    provider_name = "anthropic"

    def __init__(self, api_key: str, default_model: str = "claude-sonnet-5"):
        if not api_key:
            raise ValueError("AnthropicProvider requires an API key.")
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - exercised only without the dep installed
            raise ImportError(
                "The 'anthropic' package is required to use AnthropicProvider."
            ) from exc
        self._client = anthropic.Anthropic(api_key=api_key)
        self._default_model = default_model
        self._retryable = (
            anthropic.RateLimitError,
            anthropic.APIConnectionError,
            anthropic.APITimeoutError,
            anthropic.InternalServerError,
        )

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> LLMResponse:
        del seed  # Anthropic's Messages API has no `seed` parameter.
        resolved_model = model or self._default_model
        system, converted = _to_anthropic_messages(messages)
        kwargs: dict[str, Any] = {
            "model": resolved_model,
            "max_tokens": _ANTHROPIC_MAX_TOKENS_DEFAULT,
            "temperature": temperature,
            "messages": converted,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = [_to_anthropic_tool(t) for t in tools]

        start = time.perf_counter()
        response = call_with_retry(lambda: self._client.messages.create(**kwargs), self._retryable)
        latency_ms = (time.perf_counter() - start) * 1000

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=block.input or {})
                )

        usage = TokenUsage(
            input_tokens=response.usage.input_tokens if response.usage else 0,
            output_tokens=response.usage.output_tokens if response.usage else 0,
        )
        return LLMResponse(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            usage=usage,
            model=response.model or resolved_model,
            raw=response,
            latency_ms=latency_ms,
        )


def _to_anthropic_messages(messages: list[Message]) -> tuple[str | None, list[dict]]:
    """Full tool_use/tool_result round-trip, not just role renaming:
    - assistant messages with `tool_calls` become text + tool_use blocks.
    - consecutive role="tool" messages (multiple results for one assistant
      turn — i.e. multiple tool calls in one turn) are batched into a
      single user message with multiple tool_result blocks, since that's
      what the Messages API requires.
    """
    system_parts = [m.content for m in messages if m.role == "system"]
    system = "\n".join(system_parts) if system_parts else None
    non_system = [m for m in messages if m.role != "system"]

    converted: list[dict] = []
    i = 0
    while i < len(non_system):
        m = non_system[i]
        if m.role == "tool":
            block_group = []
            while i < len(non_system) and non_system[i].role == "tool":
                tm = non_system[i]
                block: dict[str, Any] = {
                    "type": "tool_result",
                    "tool_use_id": tm.tool_call_id,
                    "content": tm.content,
                }
                if tm.is_error:
                    block["is_error"] = True
                block_group.append(block)
                i += 1
            converted.append({"role": "user", "content": block_group})
            continue
        if m.role == "assistant" and m.tool_calls:
            content: list[dict] = []
            if m.content:
                content.append({"type": "text", "text": m.content})
            for tc in m.tool_calls:
                content.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
            converted.append({"role": "assistant", "content": content})
            i += 1
            continue
        converted.append({"role": m.role, "content": m.content})
        i += 1
    return system, converted


def _to_anthropic_tool(tool: ToolSpec) -> dict:
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.parameters,
    }
