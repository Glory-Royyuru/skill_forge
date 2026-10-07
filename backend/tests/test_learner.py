from __future__ import annotations

from skillforge.agents.learner import run_learner
from skillforge.envs.ecommerce.environment import EcommerceRefundEnvironment
from skillforge.envs.ecommerce.generator import generate_tasks
from skillforge.llm.client import LoggingLLMClient
from skillforge.llm.mock import MockProvider

TASK = generate_tasks(seed=1, n=200)[0]
ORDER_ID = TASK.initial_state["order"]["order_id"]


def _client(db, provider):
    session = db.session()
    return LoggingLLMClient(provider, session, role="learner")


def test_learner_stops_on_terminal_action(db):
    provider = MockProvider(
        script=[
            {"tool_calls": [{"name": "view_order", "arguments": {"order_id": ORDER_ID}}]},
            {"tool_calls": [{"name": "escalate", "arguments": {"order_id": ORDER_ID, "reason_code": "x"}}]},
        ]
    )
    env = EcommerceRefundEnvironment()
    run = run_learner(env, TASK, _client(db, provider), "system prompt")
    assert run.stop_reason == "terminal"
    assert run.steps_taken == 2
    assert len(run.trajectory) == 2
    assert run.trajectory[-1]["terminal"] is True


def test_learner_records_malformed_tool_call_as_a_step(db):
    provider = MockProvider(
        script=[
            {"tool_calls": [{"name": "not_a_real_tool", "arguments": {}}]},
            {"tool_calls": [{"name": "escalate", "arguments": {"order_id": ORDER_ID, "reason_code": "x"}}]},
        ]
    )
    env = EcommerceRefundEnvironment()
    run = run_learner(env, TASK, _client(db, provider), "system prompt")
    assert run.malformed_calls == 1
    assert run.steps_taken == 2
    assert run.trajectory[0]["ok"] is False
    assert run.stop_reason == "terminal"


def test_learner_hits_max_steps_without_terminal_action(db):
    provider = MockProvider(
        script=[{"tool_calls": [{"name": "view_order", "arguments": {"order_id": ORDER_ID}}]}] * 3
    )
    env = EcommerceRefundEnvironment()
    run = run_learner(env, TASK, _client(db, provider), "system prompt", max_steps=3)
    assert run.stop_reason == "max_steps"
    assert run.steps_taken == 3


def test_learner_stops_on_no_tool_call(db):
    provider = MockProvider(script=["I'm not sure what to do."])
    env = EcommerceRefundEnvironment()
    run = run_learner(env, TASK, _client(db, provider), "system prompt")
    assert run.steps_taken == 1
    assert run.stop_reason == "max_steps"


def test_learner_enforces_token_budget(db):
    provider = MockProvider(
        script=[{"tool_calls": [{"name": "view_order", "arguments": {"order_id": ORDER_ID}}]}] * 5
    )
    env = EcommerceRefundEnvironment()
    run = run_learner(env, TASK, _client(db, provider), "system prompt", token_budget=1)
    assert run.stop_reason == "budget_exhausted"
    assert run.steps_taken == 1


def test_learner_never_sees_ground_truth_in_messages(db):
    call = {"name": "escalate", "arguments": {"order_id": ORDER_ID, "reason_code": "x"}}
    provider = MockProvider(script=[{"tool_calls": [call]}])
    env = EcommerceRefundEnvironment()
    run = run_learner(env, TASK, _client(db, provider), "system prompt")
    blob = str(run.messages) + str(run.trajectory)
    assert "rules_involved" not in blob
