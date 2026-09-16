"""The provider-agnostic LLM interface every implementation follows."""

from __future__ import annotations

from abc import ABC, abstractmethod

from skillforge.llm.types import LLMResponse, Message, ToolSpec


class LLMProvider(ABC):
    """Common interface implemented by OpenAIProvider, AnthropicProvider,
    and MockProvider."""

    provider_name: str = "base"

    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> LLMResponse:
        raise NotImplementedError
