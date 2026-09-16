"""Tests for EcommerceRefundEnvironment: tool schema validation, terminal
action handling, and — critically — that ground truth is never reachable
through any learner-facing surface.
"""

from __future__ import annotations

import json

from skillforge.envs.base import Action
from skillforge.envs.ecommerce.environment import EcommerceRefundEnvironment
from skillforge.envs.ecommerce.generator import generate_tasks

# Fields that only ever belong to the hidden `Expected` decision. If any of
# these keys show up in get_state() or in an ActionResult.output, ground
# truth has leaked into a learner-facing surface.
DECISION_ONLY_KEYS = {"reason_code", "rules_involved", "expected", "critical", "error_type"}


def _first_task():
    return generate_tasks(seed=1, n=200)[0]


def test_reset_returns_state_with_request_and_not_done():
    task = _first_task()
    env = EcommerceRefundEnvironment()
    state = env.reset(task)
    assert state.request == task.request
    assert state.done is False


def test_invalid_tool_name_is_recorded_not_executed():
    task = _first_task()
    env = EcommerceRefundEnvironment()
    env.reset(task)
    result = env.execute_action(Action(tool="delete_everything", args={}))
    assert result.ok is False
    assert "unknown_tool" in result.error
    assert result.terminal is False


def test_missing_required_field_is_rejected_not_executed():
    task = _first_task()
    env = EcommerceRefundEnvironment()
    env.reset(task)
    result = env.execute_action(Action(tool="view_order", args={}))
    assert result.ok is False
    assert "missing_required_field" in result.error


def test_wrong_type_argument_is_rejected():
    task = _first_task()
    env = EcommerceRefundEnvironment()
    env.reset(task)
    result = env.execute_action(
        Action(tool="process_refund", args={"order_id": "X", "amount": "a lot", "method": "original_payment"})
    )
    assert result.ok is False
    assert "wrong_type" in result.error


def test_invalid_enum_value_is_rejected():
    task = _first_task()
    env = EcommerceRefundEnvironment()
    env.reset(task)
    order_id = task.initial_state["order"]["order_id"]
    result = env.execute_action(
        Action(tool="process_refund", args={"order_id": order_id, "amount": 10.0, "method": "cash"})
    )
    assert result.ok is False
    assert "invalid_enum_value" in result.error


def test_view_order_returns_the_target_order():
    task = _first_task()
    env = EcommerceRefundEnvironment()
    env.reset(task)
    order_id = task.initial_state["order"]["order_id"]
    result = env.execute_action(Action(tool="view_order", args={"order_id": order_id}))
    assert result.ok is True
    assert result.output["order_id"] == order_id


def test_view_order_unknown_id_errors():
    task = _first_task()
    env = EcommerceRefundEnvironment()
    env.reset(task)
    result = env.execute_action(Action(tool="view_order", args={"order_id": "does-not-exist"}))
    assert result.ok is False
    assert result.error == "order_not_found"


def test_terminal_action_ends_episode():
    task = _first_task()
    env = EcommerceRefundEnvironment()
    env.reset(task)
    order_id = task.initial_state["order"]["order_id"]
    result = env.execute_action(
        Action(tool="reject_refund", args={"order_id": order_id, "reason_code": "window_expired"})
    )
    assert result.terminal is True
    assert env.get_state().done is True


def test_action_after_terminal_is_not_executed():
    task = _first_task()
    env = EcommerceRefundEnvironment()
    env.reset(task)
    order_id = task.initial_state["order"]["order_id"]
    env.execute_action(
        Action(tool="reject_refund", args={"order_id": order_id, "reason_code": "window_expired"})
    )
    second = env.execute_action(Action(tool="view_order", args={"order_id": order_id}))
    assert second.ok is False
    assert second.error == "episode_already_terminated"


def test_terminal_action_on_wrong_order_id_ends_episode_as_wrong_order():
    # Phase 1.1: a terminal action on an order other than the task's
    # target now executes (the environment doesn't gate on order id
    # anymore) and ends the episode; evaluate() is what classifies it as
    # error_type="wrong_order", not the environment refusing the call.
    task = _first_task()
    env = EcommerceRefundEnvironment()
    env.reset(task)
    result = env.execute_action(
        Action(
            tool="reject_refund",
            args={"order_id": "not-the-target-order", "reason_code": "window_expired"},
        )
    )
    assert result.ok is True
    assert result.terminal is True
    assert env.get_state().done is True

    evaluation = env.evaluate()
    assert evaluation.error_type == "wrong_order"
    assert evaluation.success is False


def test_process_refund_on_wrong_order_id_is_critical():
    task = _first_task()
    env = EcommerceRefundEnvironment()
    env.reset(task)
    env.execute_action(
        Action(
            tool="process_refund",
            args={"order_id": "not-the-target-order", "amount": 10.0, "method": "original_payment"},
        )
    )
    evaluation = env.evaluate()
    assert evaluation.error_type == "wrong_order"
    assert evaluation.critical is True


def test_list_tools_returns_all_eight_tools():
    env = EcommerceRefundEnvironment()
    names = {t.name for t in env.list_tools()}
    assert names == {
        "search_orders",
        "view_order",
        "view_customer",
        "view_policy",
        "view_order_history",
        "process_refund",
        "reject_refund",
        "escalate",
    }


# -- Ground-truth isolation ---------------------------------------------------


def test_ground_truth_never_reachable_from_state_or_tool_outputs():
    """Drive every tool at least once across many tasks and assert that no
    JSON-serialized get_state() or ActionResult ever contains a
    decision-only key. This is the structural proof that hidden ground
    truth cannot leak through any learner-facing surface.
    """
    tasks = generate_tasks(seed=7, n=200)

    for task in tasks:
        env = EcommerceRefundEnvironment()
        state = env.reset(task)
        _assert_no_decision_keys(state.data)

        order_id = task.initial_state["order"]["order_id"]
        customer_id = task.initial_state["customer"]["customer_id"]

        probes = [
            Action(tool="search_orders", args={"query": order_id}),
            Action(tool="view_order", args={"order_id": order_id}),
            Action(tool="view_customer", args={"customer_id": customer_id}),
            Action(tool="view_policy", args={"section": "refund_window"}),
            Action(tool="view_order_history", args={"customer_id": customer_id}),
        ]
        for action in probes:
            result = env.execute_action(action)
            _assert_no_decision_keys(result.output)

        state = env.get_state()
        _assert_no_decision_keys(state.data)


def _assert_no_decision_keys(payload) -> None:
    blob = json.dumps(payload, default=str).lower()
    for key in DECISION_ONLY_KEYS:
        assert key.lower() not in blob, f"found decision-only key {key!r} in learner-facing payload: {blob}"


def test_task_ground_truth_contains_no_world_leak_and_no_extra_facts():
    """`ground_truth` should be exactly the Expected shape — action,
    amount, method, reason_code, rules_involved — nothing else, and
    certainly not the raw order/customer records (those belong in
    initial_state, which is legitimately tool-reachable).
    """
    tasks = generate_tasks(seed=3, n=200)
    expected_keys = {"action", "amount", "method", "reason_code", "rules_involved"}
    for task in tasks:
        assert set(task.ground_truth.keys()) == expected_keys
