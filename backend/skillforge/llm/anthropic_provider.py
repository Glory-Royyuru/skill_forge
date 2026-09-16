"""Anthropic-backed LLMProvider.

The `anthropic` package is imported lazily inside __init__ (not at module
import time) so the rest of the codebase — and the whole test suite — can
import this module without the package installed or an API key set.
"""

from __future__ import annotations

import time
from typing import Any

from skillforge.llm.base import LLMProvider
from skillforge.llm.types import LLMResponse, Message, TokenUsage, ToolCall, ToolSpec

_ANTHROPIC_MAX_TOKENS_DEFAULT = 4096


class AnthropicProvider(LLMProvider):
    provider_name = "anthropic"

    def __init__(self, api_key: str, default_model: str = "claude-sonnet-5"):
        if not api_key:
            raise ValueError("AnthropicProvider requires an API key.")
        try:
            from anthropic import Anthropic
        except ImportError as exc:  # pragma: no cover - exercised only without the dep installed
            raise ImportError(
                "The 'anthropic' package is required to use AnthropicProvider."
            ) from exc
        self._client = Anthropic(api_key=api_key)
        self._default_model = default_model

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> LLMResponse:
        resolved_model = model or self._default_model
        system, converted = _split_system(messages)
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
        # Note: Anthropic's Messages API has no `seed` parameter (unlike
        # OpenAI's); it is accepted here for interface parity but ignored.

        start = time.perf_counter()
        response = self._client.messages.create(**kwargs)
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


def _split_system(messages: list[Message]) -> tuple[str | None, list[dict]]:
    system_parts = [m.content for m in messages if m.role == "system"]
    system = "\n".join(system_parts) if system_parts else None
    converted = []
    for m in messages:
        if m.role == "system":
            continue
        # Anthropic has no "tool" role message shape identical to OpenAI's;
        # a fuller tool-result mapping lands with the Phase 2 learner loop.
        role = "user" if m.role == "tool" else m.role
        converted.append({"role": role, "content": m.content})
    return system, converted


def _to_anthropic_tool(tool: ToolSpec) -> dict:
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.parameters,
    }
