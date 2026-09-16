"""LoggingLLMClient: wraps any LLMProvider so every call is recorded to the
`llm_calls` table (role, tokens, latency, cost estimate) and, optionally,
served from a ResponseCache keyed by a hash of the request.

This is the call path both Teacher and Learner agents use in later phases
— they never talk to a raw LLMProvider directly, so logging can't be
skipped by accident.
"""

from __future__ import annotations

from typing import Literal

from sqlalchemy.orm import Session as DBSession

from skillforge.db.models import LLMCall
from skillforge.llm.base import LLMProvider
from skillforge.llm.cache import ResponseCache, request_hash
from skillforge.llm.pricing import estimate_cost
from skillforge.llm.types import LLMResponse, Message, ToolSpec

Role = Literal["teacher", "learner"]


class LoggingLLMClient:
    def __init__(
        self,
        provider: LLMProvider,
        db: DBSession,
        role: Role,
        session_id: int | None = None,
        cache: ResponseCache | None = None,
    ):
        self._provider = provider
        self._db = db
        self._role = role
        self._session_id = session_id
        self._cache = cache

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> LLMResponse:
        cache_key = None
        if self._cache is not None:
            cache_key = request_hash(messages, tools, model, temperature, seed)
            cached = self._cache.get(cache_key)
            if cached is not None:
                self._log(cached, cache_hit=True)
                return cached

        response = self._provider.complete(
            messages, tools=tools, model=model, temperature=temperature, seed=seed
        )

        if self._cache is not None and cache_key is not None:
            self._cache.set(cache_key, response)

        self._log(response, cache_hit=False)
        return response

    def _log(self, response: LLMResponse, cache_hit: bool) -> None:
        cost = estimate_cost(
            response.model, response.usage.input_tokens, response.usage.output_tokens
        )
        call = LLMCall(
            session_id=self._session_id,
            role=self._role,
            provider=self._provider.provider_name,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=response.latency_ms,
            cost=cost,
            cache_hit=cache_hit,
        )
        self._db.add(call)
        self._db.commit()
