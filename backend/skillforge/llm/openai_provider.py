"""OpenAI-backed LLMProvider.

The `openai` package is imported lazily inside __init__ (not at module
import time) so the rest of the codebase — and the whole test suite — can
import this module without the package installed or an API key set.
"""

from __future__ import annotations

import json
import time
from typing import Any

from skillforge.llm.base import LLMProvider
from skillforge.llm.types import LLMResponse, Message, TokenUsage, ToolCall, ToolSpec


class OpenAIProvider(LLMProvider):
    provider_name = "openai"

    def __init__(self, api_key: str, default_model: str = "gpt-4o-mini"):
        if not api_key:
            raise ValueError("OpenAIProvider requires an API key.")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - exercised only without the dep installed
            raise ImportError(
                "The 'openai' package is required to use OpenAIProvider."
            ) from exc
        self._client = OpenAI(api_key=api_key)
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
        kwargs: dict[str, Any] = {
            "model": resolved_model,
            "messages": [_to_openai_message(m) for m in messages],
            "temperature": temperature,
        }
        if seed is not None:
            kwargs["seed"] = seed
        if tools:
            kwargs["tools"] = [_to_openai_tool(t) for t in tools]

        start = time.perf_counter()
        response = self._client.chat.completions.create(**kwargs)
        latency_ms = (time.perf_counter() - start) * 1000

        choice = response.choices[0]
        text = choice.message.content
        tool_calls = [
            ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=json.loads(tc.function.arguments or "{}"),
            )
            for tc in (choice.message.tool_calls or [])
        ]

        usage = TokenUsage(
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
        )
        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            usage=usage,
            model=response.model or resolved_model,
            raw=response,
            latency_ms=latency_ms,
        )


def _to_openai_message(message: Message) -> dict:
    payload: dict[str, Any] = {"role": message.role, "content": message.content}
    if message.role == "tool":
        payload["tool_call_id"] = message.tool_call_id
        if message.name:
            payload["name"] = message.name
    return payload


def _to_openai_tool(tool: ToolSpec) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }
