"""Recorded/fake-SDK-payload tests for OpenAIProvider/AnthropicProvider.

No API key or network access required: the SDK client objects are
constructed with a fake key (never a real credential) and their
`.create()` methods are monkeypatched with hand-built response doubles
that mimic the real SDK response shape.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import anthropic
import openai
import pytest

from skillforge.llm.anthropic_provider import AnthropicProvider
from skillforge.llm.openai_provider import OpenAIProvider
from skillforge.llm.types import Message, ToolCall, ToolSpec

FAKE_KEY = "fake-test-key-not-a-real-credential"


# -- Anthropic ----------------------------------------------------------------


def _anthropic_text_response(text="hello", model="claude-sonnet-5"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        model=model,
    )


def _anthropic_tool_use_response(calls, model="claude-sonnet-5"):
    blocks = [SimpleNamespace(type="tool_use", id=c[0], name=c[1], input=c[2]) for c in calls]
    return SimpleNamespace(
        content=blocks,
        usage=SimpleNamespace(input_tokens=20, output_tokens=8),
        model=model,
    )


def test_anthropic_normalizes_text_response():
    provider = AnthropicProvider(api_key=FAKE_KEY)
    provider._client.messages.create = Mock(return_value=_anthropic_text_response("hi there"))
    result = provider.complete([Message(role="user", content="hello")])
    assert result.text == "hi there"
    assert result.tool_calls == []
    assert result.usage.input_tokens == 10


def test_anthropic_normalizes_multiple_tool_calls_in_one_turn():
    provider = AnthropicProvider(api_key=FAKE_KEY)
    calls = [("t1", "view_order", {"order_id": "A"}), ("t2", "view_customer", {"customer_id": "B"})]
    provider._client.messages.create = Mock(return_value=_anthropic_tool_use_response(calls))
    result = provider.complete(
        [Message(role="user", content="hi")],
        tools=[ToolSpec(name="view_order"), ToolSpec(name="view_customer")],
    )
    assert result.text is None
    assert len(result.tool_calls) == 2
    assert result.tool_calls[0].name == "view_order"
    assert result.tool_calls[1].arguments == {"customer_id": "B"}


def test_anthropic_request_batches_multiple_tool_results_into_one_user_message():
    provider = AnthropicProvider(api_key=FAKE_KEY)
    mock_create = Mock(return_value=_anthropic_text_response("ok"))
    provider._client.messages.create = mock_create

    messages = [
        Message(role="system", content="sys"),
        Message(role="user", content="req"),
        Message(
            role="assistant",
            content="",
            tool_calls=[ToolCall(id="t1", name="view_order", arguments={"order_id": "A"})],
        ),
        Message(role="tool", tool_call_id="t1", name="view_order", content='{"ok": true}'),
        Message(role="tool", tool_call_id="t2", name="view_customer", content="failed", is_error=True),
    ]
    provider.complete(messages)

    sent = mock_create.call_args.kwargs
    assert sent["system"] == "sys"
    assistant_msg = sent["messages"][1]
    assert assistant_msg["role"] == "assistant"
    assert assistant_msg["content"][0]["type"] == "tool_use"
    tool_result_msg = sent["messages"][2]
    assert tool_result_msg["role"] == "user"
    assert len(tool_result_msg["content"]) == 2
    assert tool_result_msg["content"][0]["tool_use_id"] == "t1"
    assert tool_result_msg["content"][1].get("is_error") is True


def test_anthropic_retries_transient_errors_then_succeeds(monkeypatch):
    monkeypatch.setattr("skillforge.llm.retry.time.sleep", lambda _s: None)
    provider = AnthropicProvider(api_key=FAKE_KEY)
    err = anthropic.APIConnectionError(request=Mock())
    provider._client.messages.create = Mock(side_effect=[err, err, _anthropic_text_response("recovered")])
    result = provider.complete([Message(role="user", content="hi")])
    assert result.text == "recovered"
    assert provider._client.messages.create.call_count == 3


def test_anthropic_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setattr("skillforge.llm.retry.time.sleep", lambda _s: None)
    provider = AnthropicProvider(api_key=FAKE_KEY)
    err = anthropic.APIConnectionError(request=Mock())
    provider._client.messages.create = Mock(side_effect=err)
    with pytest.raises(anthropic.APIConnectionError):
        provider.complete([Message(role="user", content="hi")])
    assert provider._client.messages.create.call_count == 4  # 1 + 3 retries


# -- OpenAI ---------------------------------------------------------------------


def _openai_response(content=None, tool_calls=None, model="gpt-4o-mini"):
    tc_objs = None
    if tool_calls:
        tc_objs = [
            SimpleNamespace(id=c[0], function=SimpleNamespace(name=c[1], arguments=c[2]))
            for c in tool_calls
        ]
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=tc_objs))],
        usage=SimpleNamespace(prompt_tokens=15, completion_tokens=6),
        model=model,
    )


def test_openai_normalizes_text_response():
    provider = OpenAIProvider(api_key=FAKE_KEY)
    provider._client.chat.completions.create = Mock(return_value=_openai_response(content="hi"))
    result = provider.complete([Message(role="user", content="hello")])
    assert result.text == "hi"
    assert result.tool_calls == []


def test_openai_normalizes_multiple_tool_calls_in_one_turn():
    provider = OpenAIProvider(api_key=FAKE_KEY)
    calls = [("c1", "view_order", '{"order_id": "A"}'), ("c2", "view_customer", '{"customer_id": "B"}')]
    provider._client.chat.completions.create = Mock(return_value=_openai_response(tool_calls=calls))
    result = provider.complete([Message(role="user", content="hi")])
    assert len(result.tool_calls) == 2
    assert result.tool_calls[0] == ToolCall(id="c1", name="view_order", arguments={"order_id": "A"})


def test_openai_request_includes_tool_call_id_on_tool_messages():
    provider = OpenAIProvider(api_key=FAKE_KEY)
    mock_create = Mock(return_value=_openai_response(content="ok"))
    provider._client.chat.completions.create = mock_create

    messages = [
        Message(role="user", content="req"),
        Message(
            role="assistant",
            content="",
            tool_calls=[ToolCall(id="c1", name="view_order", arguments={"order_id": "A"})],
        ),
        Message(role="tool", tool_call_id="c1", name="view_order", content='{"ok": true}'),
    ]
    provider.complete(messages)

    sent = mock_create.call_args.kwargs["messages"]
    assert sent[1]["tool_calls"][0]["id"] == "c1"
    assert sent[1]["tool_calls"][0]["function"]["arguments"] == '{"order_id": "A"}'
    assert sent[2]["role"] == "tool"
    assert sent[2]["tool_call_id"] == "c1"


def test_openai_retries_transient_errors_then_succeeds(monkeypatch):
    monkeypatch.setattr("skillforge.llm.retry.time.sleep", lambda _s: None)
    provider = OpenAIProvider(api_key=FAKE_KEY)
    err = openai.APITimeoutError(request=Mock())
    provider._client.chat.completions.create = Mock(
        side_effect=[err, err, _openai_response(content="recovered")]
    )
    result = provider.complete([Message(role="user", content="hi")])
    assert result.text == "recovered"
    assert provider._client.chat.completions.create.call_count == 3


def test_openai_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setattr("skillforge.llm.retry.time.sleep", lambda _s: None)
    provider = OpenAIProvider(api_key=FAKE_KEY)
    err = openai.APITimeoutError(request=Mock())
    provider._client.chat.completions.create = Mock(side_effect=err)
    with pytest.raises(openai.APITimeoutError):
        provider.complete([Message(role="user", content="hi")])
    assert provider._client.chat.completions.create.call_count == 4
