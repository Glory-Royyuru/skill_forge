from __future__ import annotations

from skillforge.db.models import LLMCall
from skillforge.llm.cache import ResponseCache
from skillforge.llm.client import LoggingLLMClient
from skillforge.llm.mock import MockProvider
from skillforge.llm.types import Message


def test_logging_llm_client_writes_llm_calls_row(db):
    provider = MockProvider(script=["Hi"], model="mock-learner")

    with db.session() as session:
        client = LoggingLLMClient(provider, session, role="learner")
        response = client.complete([Message(role="user", content="hello")])

        assert response.text == "Hi"

        rows = session.query(LLMCall).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.role == "learner"
        assert row.provider == "mock"
        assert row.model == "mock-learner"
        assert row.cache_hit is False
        assert row.session_id is None
        assert row.cost == 0.0


def test_logging_llm_client_tags_session_and_role(db):
    provider = MockProvider(script=["Plan: ..."], model="mock-teacher")

    with db.session() as session:
        client = LoggingLLMClient(provider, session, role="teacher", session_id=42)
        client.complete([Message(role="user", content="extract a skill")])

        row = session.query(LLMCall).one()
        assert row.role == "teacher"
        assert row.session_id == 42


def test_logging_llm_client_cache_hit_skips_provider(db):
    provider = MockProvider(script=["Hi"], model="mock-learner")
    cache = ResponseCache()

    with db.session() as session:
        client = LoggingLLMClient(provider, session, role="learner", cache=cache)
        msg = [Message(role="user", content="same question")]

        first = client.complete(msg)
        second = client.complete(msg)

        # Only one item was scripted; a second real call would raise
        # IndexError, so getting a matching response back proves the cache
        # served it without touching the provider.
        assert first.text == second.text == "Hi"

        rows = session.query(LLMCall).order_by(LLMCall.id).all()
        assert len(rows) == 2
        assert rows[0].cache_hit is False
        assert rows[1].cache_hit is True
