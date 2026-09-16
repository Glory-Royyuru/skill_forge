"""Unit tests for `evaluate_attempt`, independent of the environment
plumbing (built directly from an Expected + a hand-written trajectory)."""

from __future__ import annotations

from skillforge.envs.base import Action, ActionResult
from skillforge.envs.ecommerce.evaluator import evaluate_attempt
from skillforge.envs.ecommerce.policy import Expected

TARGET_ORDER_ID = "ORD-1"


def _process(order_id=TARGET_ORDER_ID, amount=100.0, method="original_payment", ok=True, terminal=True):
    return (
        Action(tool="process_refund", args={"order_id": order_id, "amount": amount, "method": method}),
        ActionResult(ok=ok, tool="process_refund", terminal=terminal),
    )


def _reject(order_id=TARGET_ORDER_ID, reason_code="window_expired", ok=True, terminal=True):
    return (
        Action(tool="reject_refund", args={"order_id": order_id, "reason_code": reason_code}),
        ActionResult(ok=ok, tool="reject_refund", terminal=terminal),
    )


def _escalate(order_id=TARGET_ORDER_ID, reason_code="high_value", ok=True, terminal=True):
    return (
        Action(tool="escalate", args={"order_id": order_id, "reason_code": reason_code}),
        ActionResult(ok=ok, tool="escalate", terminal=terminal),
    )


def _evaluate(expected, trajectory, target_order_id=TARGET_ORDER_ID):
    return evaluate_attempt(expected, trajectory, target_order_id)


def test_exact_match_process_refund_is_success():
    expected = Expected(action="process_refund", amount=100.0, method="original_payment", reason_code=None)
    trajectory = [_process(amount=100.0, method="original_payment")]
    result = _evaluate(expected, trajectory)
    assert result.success is True
    assert result.score == 1.0
    assert result.critical is False
    assert result.error_type is None


def test_amount_within_tolerance_still_succeeds():
    expected = Expected(action="process_refund", amount=100.00, method="original_payment", reason_code=None)
    trajectory = [_process(amount=100.005, method="original_payment")]
    result = _evaluate(expected, trajectory)
    assert result.success is True


def test_amount_just_outside_tolerance_fails():
    expected = Expected(action="process_refund", amount=100.00, method="original_payment", reason_code=None)
    trajectory = [_process(amount=100.02, method="original_payment")]
    result = _evaluate(expected, trajectory)
    assert result.success is False
    assert result.error_type == "wrong_amount"
    assert result.critical is True  # wrong amount on an issued refund


def test_wrong_method_is_critical_and_scored_half():
    expected = Expected(action="process_refund", amount=100.0, method="store_credit", reason_code=None)
    trajectory = [_process(amount=100.0, method="original_payment")]
    result = _evaluate(expected, trajectory)
    assert result.success is False
    assert result.error_type == "wrong_method"
    assert result.critical is True
    assert result.score == 0.5  # correct decision type, wrong parameters


def test_reject_when_expected_process_is_critical():
    expected = Expected(action="process_refund", amount=100.0, method="original_payment", reason_code=None)
    trajectory = [_reject(reason_code="window_expired")]
    result = _evaluate(expected, trajectory)
    assert result.success is False
    assert result.critical is False  # no money issued, just a wrong (overly cautious) call
    assert result.error_type == "wrong_decision"


def test_process_when_expected_reject_is_critical():
    expected = Expected(action="reject_refund", amount=None, method=None, reason_code="window_expired")
    trajectory = [_process(amount=100.0, method="original_payment")]
    result = _evaluate(expected, trajectory)
    assert result.success is False
    assert result.critical is True  # money issued when it should not have been
    assert result.error_type == "wrong_decision"


def test_process_when_expected_escalate_is_critical_and_missed_escalation():
    expected = Expected(action="escalate", amount=None, method=None, reason_code="high_value")
    trajectory = [_process(amount=600.0, method="original_payment")]
    result = _evaluate(expected, trajectory)
    assert result.success is False
    assert result.critical is True
    assert result.error_type == "missed_escalation"


def test_reject_when_expected_escalate_is_missed_escalation_but_not_critical():
    expected = Expected(action="escalate", amount=None, method=None, reason_code="high_value")
    trajectory = [_reject(reason_code="window_expired")]
    result = _evaluate(expected, trajectory)
    assert result.success is False
    assert result.critical is False
    assert result.error_type == "missed_escalation"


def test_exact_match_reject_is_success():
    expected = Expected(action="reject_refund", amount=None, method=None, reason_code="already_refunded")
    trajectory = [_reject(reason_code="already_refunded")]
    result = _evaluate(expected, trajectory)
    assert result.success is True
    assert result.score == 1.0


def test_reject_with_wrong_reason_code_is_wrong_reason_code_not_success():
    expected = Expected(action="reject_refund", amount=None, method=None, reason_code="already_refunded")
    trajectory = [_reject(reason_code="window_expired")]
    result = _evaluate(expected, trajectory)
    assert result.success is False
    assert result.error_type == "wrong_reason_code"
    assert result.score == 0.5  # correct decision type (reject/escalate), wrong reason code
    assert result.critical is False


def test_escalate_with_wrong_reason_code_is_wrong_reason_code_not_success():
    expected = Expected(action="escalate", amount=None, method=None, reason_code="frequent_refunds")
    trajectory = [_escalate(reason_code="high_value")]
    result = _evaluate(expected, trajectory)
    assert result.success is False
    assert result.error_type == "wrong_reason_code"
    assert result.score == 0.5
    assert result.critical is False


def test_no_terminal_action_at_all():
    expected = Expected(action="process_refund", amount=100.0, method="original_payment", reason_code=None)
    trajectory = [
        (
            Action(tool="view_order", args={"order_id": TARGET_ORDER_ID}),
            ActionResult(ok=True, tool="view_order"),
        )
    ]
    result = _evaluate(expected, trajectory)
    assert result.success is False
    assert result.score == 0.0
    assert result.critical is False
    assert result.error_type == "no_final_action"


def test_only_invalid_terminal_attempts_is_invalid_tool_sequence():
    # A schema-invalid terminal call (missing a required field) never
    # executes, so it can't end the episode — distinct from wrong_order,
    # which is a real (executed) terminal action on the wrong order.
    expected = Expected(action="process_refund", amount=100.0, method="original_payment", reason_code=None)
    trajectory = [
        (
            Action(tool="process_refund", args={"order_id": TARGET_ORDER_ID, "amount": 100.0}),
            ActionResult(ok=False, tool="process_refund", error="invalid_args:missing_required_field:method"),
        )
    ]
    result = _evaluate(expected, trajectory)
    assert result.success is False
    assert result.error_type == "invalid_tool_sequence"


def test_expected_and_actual_are_present_in_output():
    expected = Expected(
        action="reject_refund",
        amount=None,
        method=None,
        reason_code="already_refunded",
        rules_involved=["R8"],
    )
    trajectory = [_reject(reason_code="already_refunded")]
    result = _evaluate(expected, trajectory)
    assert result.expected == {
        "action": "reject_refund",
        "amount": None,
        "method": None,
        "reason_code": "already_refunded",
    }
    assert result.actual["action"] == "reject_refund"
    assert result.rules_involved == ["R8"]


# -- wrong_order (Phase 1.1) --------------------------------------------------


def test_process_refund_on_wrong_order_ends_episode_as_wrong_order_and_critical():
    expected = Expected(action="process_refund", amount=100.0, method="original_payment", reason_code=None)
    trajectory = [_process(order_id="ORD-DISTRACTOR", amount=100.0, method="original_payment")]
    result = _evaluate(expected, trajectory)
    assert result.success is False
    assert result.error_type == "wrong_order"
    assert result.critical is True  # money issued, just against the wrong order
    assert result.score == 0.0


def test_reject_refund_on_wrong_order_is_wrong_order_but_not_critical():
    expected = Expected(action="reject_refund", amount=None, method=None, reason_code="window_expired")
    trajectory = [_reject(order_id="ORD-DISTRACTOR", reason_code="window_expired")]
    result = _evaluate(expected, trajectory)
    assert result.success is False
    assert result.error_type == "wrong_order"
    assert result.critical is False  # no money moved
    assert result.score == 0.0


def test_escalate_on_wrong_order_is_wrong_order_but_not_critical():
    expected = Expected(action="escalate", amount=None, method=None, reason_code="high_value")
    trajectory = [_escalate(order_id="ORD-DISTRACTOR", reason_code="high_value")]
    result = _evaluate(expected, trajectory)
    assert result.success is False
    assert result.error_type == "wrong_order"
    assert result.critical is False
    assert result.score == 0.0


def test_wrong_order_even_when_action_and_params_would_otherwise_match():
    # Right action, right amount, right method — but the wrong order. Still
    # wholly wrong: no partial credit for "would have been correct".
    expected = Expected(action="process_refund", amount=100.0, method="original_payment", reason_code=None)
    trajectory = [_process(order_id="ORD-DISTRACTOR", amount=100.0, method="original_payment")]
    result = _evaluate(expected, trajectory)
    assert result.error_type == "wrong_order"
    assert result.score == 0.0


def test_wrong_order_ends_the_episode_in_extract_actual():
    # A wrong-order terminal call is a *successful* (ok=True) tool
    # execution in the environment now (see environment.py) — evaluate()
    # must classify it by comparing order_id, not by the tool having
    # failed.
    expected = Expected(action="reject_refund", amount=None, method=None, reason_code="window_expired")
    trajectory = [
        _reject(order_id="ORD-DISTRACTOR", reason_code="window_expired", ok=True, terminal=True),
    ]
    result = _evaluate(expected, trajectory)
    assert result.actual["order_id"] == "ORD-DISTRACTOR"
    assert result.error_type == "wrong_order"
