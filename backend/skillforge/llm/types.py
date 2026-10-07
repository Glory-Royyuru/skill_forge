"""Normalized types shared by every LLM provider implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    role: Role
    content: str = ""
    # Populated on role="tool" replies, echoing the tool_call this answers.
    tool_call_id: str | None = None
    name: str | None = None
    # role="tool": marks this result as an error (maps to Anthropic's
    # tool_result.is_error; OpenAI has no equivalent field, so the error is
    # conveyed via `content` text only for that provider).
    is_error: bool = False
    # role="assistant": tool calls the model made this turn, so a later
    # `complete()` call can replay full history to either provider.
    tool_calls: list[ToolCall] | None = None


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolSpec:
    name: str
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class LLMResponse:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    model: str = ""
    raw: Any = None
    latency_ms: float = 0.0
    cache_hit: bool = False
