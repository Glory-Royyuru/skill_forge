"""An optional response cache keyed by a hash of the request.

Process-local and in-memory for now; the interface is intentionally
narrow (`get`/`set`/`clear`) so it can be swapped for a persistent backend
later without touching call sites.
"""

from __future__ import annotations

import hashlib
import json

from skillforge.llm.types import LLMResponse, Message, ToolSpec


def request_hash(
    messages: list[Message],
    tools: list[ToolSpec] | None,
    model: str | None,
    temperature: float,
    seed: int | None,
) -> str:
    payload = {
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "tool_call_id": m.tool_call_id,
                "name": m.name,
            }
            for m in messages
        ],
        "tools": [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in (tools or [])
        ],
        "model": model,
        "temperature": temperature,
        "seed": seed,
    }
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


class ResponseCache:
    def __init__(self) -> None:
        self._store: dict[str, LLMResponse] = {}

    def get(self, key: str) -> LLMResponse | None:
        return self._store.get(key)

    def set(self, key: str, response: LLMResponse) -> None:
        self._store[key] = response

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)
