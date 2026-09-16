"""Deterministic, pure-Python evaluator. No LLM involved anywhere here —
the Teacher is never the source of truth for pass/fail.

`evaluate_attempt` takes the hidden `Expected` answer, the trajectory of
(Action, ActionResult) pairs recorded during an episode, and the task's
target `order_id`, and produces an `EvaluationResult` per the Phase 1 spec's
output shape. `error_type` is one of: `wrong_decision`, `wrong_amount`,
`wrong_method`, `wrong_reason_code`, `wrong_order`, `missed_escalation`,
`invalid_tool_sequence`, `no_final_action` (see Phase 1.1 in PROGRESS.md's
Decisions log for `wrong_order`/`wrong_reason_code`, added after Phase 1's
gate).
"""

from __future__ import annotations

from skillforge.envs.base import Action, ActionResult, EvaluationResult
from skillforge.envs.ecommerce.policy import Expected

TERMINAL_TOOLS = {"process_refund", "reject_refund", "escalate"}
AMOUNT_TOLERANCE = 0.01


def _extract_actual(trajectory: list[tuple[Action, ActionResult]]) -> dict:
    terminal_attempts = [(a, r) for a, r in trajectory if a.tool in TERMINAL_TOOLS]
    successful = [(a, r) for a, r in terminal_attempts if r.ok]

    if successful:
        action, _result = successful[-1]
        if action.tool == "process_refund":
            return {
                "action": "process_refund",
                "order_id": action.args.get("order_id"),
                "amount": action.args.get("amount"),
                "method": action.args.get("method"),
                "reason_code": None,
            }
        return {
            "action": action.tool,
            "order_id": action.args.get("order_id"),
            "amount": None,
            "method": None,
            "reason_code": action.args.get("reason_code"),
        }

    if terminal_attempts:
        # At least one terminal tool was attempted, but every attempt was
        # invalid (schema violation — missing/malformed args). Distinct
        # from never trying at all. Note: targeting the wrong order_id is
        # NOT a reason to land here anymore — the environment executes
        # such calls (see environment.py); that's `wrong_order` below.
        return {
            "action": None,
            "order_id": None,
            "amount": None,
            "method": None,
            "reason_code": None,
            "attempted_tool": terminal_attempts[-1][0].tool,
        }

    return {"action": None, "order_id": None, "amount": None, "method": None, "reason_code": None}


def evaluate_attempt(
    expected: Expected,
    trajectory: list[tuple[Action, ActionResult]],
    target_order_id: str,
) -> EvaluationResult:
    actual = _extract_actual(trajectory)
    expected_dict = {
        "action": expected.action,
        "amount": expected.amount,
        "method": expected.method,
        "reason_code": expected.reason_code,
    }

    if actual["action"] is None:
        error_type = "invalid_tool_sequence" if "attempted_tool" in actual else "no_final_action"
        return EvaluationResult(
            success=False,
            score=0.0,
            critical=False,
            error_type=error_type,
            expected=expected_dict,
            actual=actual,
            rules_involved=expected.rules_involved,
        )

    # wrong_order: a terminal action was taken on an order other than the
    # request's target. This is checked before — and takes priority over —
    # action/parameter correctness: whatever was decided, it wasn't decided
    # about this task's order, so no partial credit for happening to match.
    if actual["order_id"] != target_order_id:
        return EvaluationResult(
            success=False,
            score=0.0,
            critical=actual["action"] == "process_refund",
            error_type="wrong_order",
            expected=expected_dict,
            actual=actual,
            rules_involved=expected.rules_involved,
        )

    action_correct = actual["action"] == expected.action

    params_correct = False
    amount_ok = False
    if action_correct:
        if expected.action == "process_refund":
            amount_ok = (
                actual["amount"] is not None
                and expected.amount is not None
                and abs(actual["amount"] - expected.amount) <= AMOUNT_TOLERANCE
            )
            params_correct = amount_ok and actual["method"] == expected.method
        else:
            params_correct = actual["reason_code"] == expected.reason_code

    score = (0.5 if action_correct else 0.0) + (0.5 if params_correct else 0.0)
    success = action_correct and params_correct

    critical = False
    if actual["action"] == "process_refund" and expected.action != "process_refund":
        # Money issued when it should not have been at all (includes the
        # "should have escalated" case).
        critical = True
    elif actual["action"] == "process_refund" and expected.action == "process_refund" and not params_correct:
        # Money issued, but the wrong amount or method.
        critical = True

    if success:
        error_type = None
    elif not action_correct:
        if expected.action == "escalate":
            error_type = "missed_escalation"
        else:
            error_type = "wrong_decision"
    else:
        # Action matches; parameters differ.
        if expected.action == "process_refund":
            error_type = "wrong_amount" if not amount_ok else "wrong_method"
        else:
            # Same terminal action (reject/escalate), but a different
            # reason_code. Not critical: no money moved either way.
            error_type = "wrong_reason_code"

    return EvaluationResult(
        success=success,
        score=score,
        critical=critical,
        error_type=error_type,
        expected=expected_dict,
        actual=actual,
        rules_involved=expected.rules_involved,
    )
