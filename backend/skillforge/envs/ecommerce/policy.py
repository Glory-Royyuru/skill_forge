"""The hidden refund policy, as a single pure function.

`resolve_ground_truth` is the only place R1-R10 are encoded. It is
imported by the generator (to label tasks) and by the evaluator (via the
environment, indirectly) and by OracleAgent (directly, on the same world
facts the environment itself uses) — but it must never be imported by
anything that stands in for a learner or teacher.

Every place the spec was silent about rule interaction, the conservative
choice — the one least likely to let money go out when it shouldn't — is
taken and documented inline. Summary (see comments below for the "why"):

1. Already-refunded (R8) is checked first and short-circuits everything.
2. Final-sale (R4) is checked before the standard/damaged/VIP window
   logic, as its own gate with its own fixed 7-day exception.
3. The VIP +15 day bonus (R3) applies to the standard/damaged window, but
   NOT to R4's 7-day damaged-on-arrival exception.
4. R7 (>$500) and R10 (>=3 refunds/90d) only ever convert a would-be
   `process_refund` into `escalate` — they never turn an already-decided
   reject into an escalate, since no money is at risk in a reject either
   way.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from skillforge.envs.ecommerce.models import (
    Customer,
    ItemCategory,
    ItemCondition,
    Order,
    OrderHistory,
    RefundRequest,
)

STANDARD_WINDOW_DAYS = 30
DAMAGED_WINDOW_DAYS = 60
VIP_BONUS_DAYS = 15
FINAL_SALE_DAMAGED_EXCEPTION_DAYS = 7
HIGH_VALUE_THRESHOLD = 500.0
FREQUENT_REFUND_COUNT = 3
FREQUENT_REFUND_WINDOW_DAYS = 90
OPENED_ELECTRONICS_REFUND_FRACTION = 0.85


@dataclass
class Expected:
    action: str  # process_refund | reject_refund | escalate
    amount: float | None
    method: str | None
    reason_code: str | None
    rules_involved: list[str] = field(default_factory=list)


def resolve_ground_truth(
    order: Order,
    customer: Customer,
    history: OrderHistory,
    request: RefundRequest,
) -> Expected:
    """Pure function: same inputs always produce the same Expected.

    `request.claimed_days_since_delivery` (the customer's possibly-wrong
    claim) is read in exactly one place below: to tag R9 into
    `rules_involved` when it actually disagrees with the system record.
    It is never read to decide eligibility — every day-window comparison
    below uses `order.days_since_delivery` only — so "system record wins"
    holds by construction regardless of that tag.
    """
    rules: list[str] = []
    date_conflict = (
        request.claimed_days_since_delivery is not None
        and request.claimed_days_since_delivery != order.days_since_delivery
    )

    # R8 — already refunded. Checked first: unambiguous, and rejecting
    # can't wrongly issue money, so there's no reason to defer it behind
    # any other check.
    if order.already_refunded:
        return Expected(
            action="reject_refund",
            amount=None,
            method=None,
            reason_code="already_refunded",
            rules_involved=["R8"],
        )

    # R4 — final sale items are never refundable, except damaged-on-arrival
    # reported within 7 days.
    if order.is_final_sale:
        rules.append("R4")
        if date_conflict:
            rules.append("R9")
        damaged_on_arrival_within_window = (
            order.condition == ItemCondition.DAMAGED
            and order.days_since_delivery <= FINAL_SALE_DAMAGED_EXCEPTION_DAYS
        )
        if not damaged_on_arrival_within_window:
            return Expected(
                action="reject_refund",
                amount=None,
                method=None,
                reason_code="final_sale_non_refundable",
                rules_involved=rules,
            )
        # Falls through: the item is eligible via the exception. Note R3's
        # VIP bonus is deliberately NOT applied to this fixed 7-day window
        # (see module docstring) — R1/R2's window formula below is skipped
        # entirely for this branch.
    else:
        window = STANDARD_WINDOW_DAYS
        rules.append("R1")
        if order.condition == ItemCondition.DAMAGED:
            window = DAMAGED_WINDOW_DAYS
            rules.append("R2")
        if customer.is_vip:
            window += VIP_BONUS_DAYS
            rules.append("R3")
        if date_conflict:
            rules.append("R9")
        if order.days_since_delivery > window:
            return Expected(
                action="reject_refund",
                amount=None,
                method=None,
                reason_code="window_expired",
                rules_involved=rules,
            )

    # Eligible. Compute amount and method.
    amount = order.item_price
    if (
        order.category == ItemCategory.ELECTRONICS
        and order.is_opened
        and order.condition != ItemCondition.DAMAGED
    ):
        amount = round(amount * OPENED_ELECTRONICS_REFUND_FRACTION, 2)
        rules.append("R5")

    method = "original_payment"
    if order.is_gift:
        method = "store_credit"
        rules.append("R6")

    # R7 / R10 — guardrails that only ever convert a would-be process into
    # an escalate (see module docstring for why rejects are unaffected).
    is_frequent_refunder = history.count_within(FREQUENT_REFUND_WINDOW_DAYS) >= FREQUENT_REFUND_COUNT
    is_high_value = amount > HIGH_VALUE_THRESHOLD

    if is_frequent_refunder or is_high_value:
        if is_frequent_refunder:
            rules.append("R10")
        if is_high_value:
            rules.append("R7")
        # Deterministic tie-break when both fire: frequency is reported as
        # the reason_code (both rule ids still appear in rules_involved).
        reason_code = "frequent_refunds" if is_frequent_refunder else "high_value"
        return Expected(
            action="escalate",
            amount=None,
            method=None,
            reason_code=reason_code,
            rules_involved=rules,
        )

    return Expected(
        action="process_refund",
        amount=amount,
        method=method,
        reason_code=None,
        rules_involved=rules,
    )
