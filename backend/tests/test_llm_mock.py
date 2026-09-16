from __future__ import annotations

import pytest

from skillforge.llm.mock import MockProvider
from skillforge.llm.types import Message


def test_mock_provider_returns_scripted_text():
    provider = MockProvider(script=["Hello there"])
    response = provider.complete([Message(role="user", content="hi")])

    assert response.text == "Hello there"
    assert response.tool_calls == []
    assert response.usage.input_tokens >= 0
    assert response.usage.output_tokens > 0


def test_mock_provider_returns_scripted_tool_call():
    provider = MockProvider(
        script=[
            {
                "tool_calls": [
                    {"name": "issue_refund", "arguments": {"order_id": "A1", "amount": 10}}
                ]
            }
        ]
    )
    response = provider.complete([Message(role="user", content="refund order A1")])

    assert response.text is None
    assert len(response.tool_calls) == 1
    call = response.tool_calls[0]
    assert call.name == "issue_refund"
    assert call.arguments == {"order_id": "A1", "amount": 10}


def test_mock_provider_consumes_script_in_order():
    provider = MockProvider(script=["first", "second"])

    first = provider.complete([Message(role="user", content="a")])
    second = provider.complete([Message(role="user", content="b")])

    assert first.text == "first"
    assert second.text == "second"
    assert len(provider.calls) == 2


def test_mock_provider_raises_when_script_exhausted():
    provider = MockProvider(script=["only one"])
    provider.complete([Message(role="user", content="a")])

    with pytest.raises(IndexError):
        provider.complete([Message(role="user", content="b")])
