"""Unit tests for `resolve_ground_truth`: one or more per rule (R1-R10),
plus every interaction/boundary case the Phase 1 gate lists explicitly.
"""

from __future__ import annotations

from skillforge.envs.ecommerce.models import ItemCategory, ItemCondition
from skillforge.envs.ecommerce.policy import resolve_ground_truth
from tests.envs.factories import make_customer, make_history, make_order, make_request

# -- R1: standard 30-day window ---------------------------------------------


def test_r1_within_window_processes():
    order = make_order(days_since_delivery=15)
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.action == "process_refund"
    assert result.amount == 100.0
    assert result.method == "original_payment"
    assert "R1" in result.rules_involved


def test_r1_day_30_is_inclusive_and_eligible():
    order = make_order(days_since_delivery=30)
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.action == "process_refund"


def test_r1_day_31_is_expired():
    order = make_order(days_since_delivery=31)
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.action == "reject_refund"
    assert result.reason_code == "window_expired"


# -- R2: damaged items get a 60-day window -----------------------------------


def test_r2_damaged_extends_window_to_60():
    order = make_order(condition=ItemCondition.DAMAGED, days_since_delivery=50)
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.action == "process_refund"
    assert "R2" in result.rules_involved


def test_r2_damaged_day_60_is_inclusive_and_eligible():
    order = make_order(condition=ItemCondition.DAMAGED, days_since_delivery=60)
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.action == "process_refund"


def test_r2_damaged_day_61_is_expired():
    order = make_order(condition=ItemCondition.DAMAGED, days_since_delivery=61)
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.action == "reject_refund"
    assert result.reason_code == "window_expired"


# -- R3: VIP customers get +15 days on any window ----------------------------


def test_r3_vip_extends_standard_window():
    order = make_order(days_since_delivery=40)
    customer = make_customer(is_vip=True)
    result = resolve_ground_truth(order, customer, make_history(), make_request())
    assert result.action == "process_refund"
    assert "R3" in result.rules_involved


def test_r3_vip_day_45_is_inclusive_and_eligible():
    order = make_order(days_since_delivery=45)
    result = resolve_ground_truth(order, make_customer(is_vip=True), make_history(), make_request())
    assert result.action == "process_refund"


def test_r3_vip_day_46_is_expired():
    order = make_order(days_since_delivery=46)
    result = resolve_ground_truth(order, make_customer(is_vip=True), make_history(), make_request())
    assert result.action == "reject_refund"
    assert result.reason_code == "window_expired"


# -- R4: final sale is never refundable, except damaged-on-arrival <=7 days --


def test_r4_final_sale_plain_is_never_refundable():
    order = make_order(is_final_sale=True, days_since_delivery=2)
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.action == "reject_refund"
    assert result.reason_code == "final_sale_non_refundable"
    assert "R4" in result.rules_involved


def test_r4_final_sale_damaged_within_7_days_is_refundable():
    order = make_order(is_final_sale=True, condition=ItemCondition.DAMAGED, days_since_delivery=7)
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.action == "process_refund"


def test_r4_final_sale_damaged_after_7_days_is_not_refundable():
    order = make_order(is_final_sale=True, condition=ItemCondition.DAMAGED, days_since_delivery=8)
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.action == "reject_refund"
    assert result.reason_code == "final_sale_non_refundable"


def test_r4_vip_does_not_extend_the_7_day_exception():
    # Documented conservative choice: R3's "any window" bonus does not
    # stretch R4's fixed 7-day damaged-on-arrival exception.
    order = make_order(is_final_sale=True, condition=ItemCondition.DAMAGED, days_since_delivery=8)
    result = resolve_ground_truth(order, make_customer(is_vip=True), make_history(), make_request())
    assert result.action == "reject_refund"
    assert result.reason_code == "final_sale_non_refundable"


# -- R5: opened, non-damaged electronics refund at 85% -----------------------


def test_r5_opened_electronics_refunds_85_percent():
    order = make_order(
        category=ItemCategory.ELECTRONICS, is_opened=True, item_price=200.0, days_since_delivery=5
    )
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.action == "process_refund"
    assert result.amount == 170.0
    assert "R5" in result.rules_involved


def test_r5_does_not_apply_when_damaged():
    order = make_order(
        category=ItemCategory.ELECTRONICS,
        is_opened=True,
        condition=ItemCondition.DAMAGED,
        item_price=200.0,
        days_since_delivery=5,
    )
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.amount == 200.0
    assert "R5" not in result.rules_involved


def test_r5_does_not_apply_when_unopened():
    order = make_order(
        category=ItemCategory.ELECTRONICS, is_opened=False, item_price=200.0, days_since_delivery=5
    )
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.amount == 200.0


# -- R6: gift orders refund as store credit only -----------------------------


def test_r6_gift_refunds_as_store_credit():
    order = make_order(is_gift=True, days_since_delivery=5)
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.action == "process_refund"
    assert result.method == "store_credit"
    assert "R6" in result.rules_involved


# -- R7: refunds over $500 (after adjustments) must escalate -----------------


def test_r7_high_value_escalates():
    order = make_order(item_price=600.0, days_since_delivery=5)
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.action == "escalate"
    assert result.reason_code == "high_value"
    assert "R7" in result.rules_involved


def test_r7_exactly_500_does_not_escalate():
    order = make_order(item_price=500.0, days_since_delivery=5)
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.action == "process_refund"


def test_r7_over_500_after_85_percent_electronics_adjustment_escalates():
    # $700 opened electronics -> $595 after R5's 85% adjustment -> still
    # over $500, so R7 fires on the *adjusted* amount.
    order = make_order(
        category=ItemCategory.ELECTRONICS, is_opened=True, item_price=700.0, days_since_delivery=5
    )
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.action == "escalate"
    assert result.reason_code == "high_value"
    assert "R5" in result.rules_involved
    assert "R7" in result.rules_involved


def test_r7_under_500_after_85_percent_adjustment_does_not_escalate():
    # $550 opened electronics -> $467.50 after adjustment -> under $500.
    order = make_order(
        category=ItemCategory.ELECTRONICS, is_opened=True, item_price=550.0, days_since_delivery=5
    )
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.action == "process_refund"
    assert result.amount == 467.50


# -- R8: already-refunded orders reject with already_refunded ----------------


def test_r8_already_refunded_rejects():
    order = make_order(already_refunded=True, days_since_delivery=5)
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.action == "reject_refund"
    assert result.reason_code == "already_refunded"
    assert result.rules_involved == ["R8"]


def test_r8_takes_precedence_over_everything_else():
    # Even a scenario that would otherwise process cleanly must reject.
    order = make_order(already_refunded=True, days_since_delivery=5, is_gift=True)
    result = resolve_ground_truth(order, make_customer(is_vip=True), make_history([1, 2, 3]), make_request())
    assert result.action == "reject_refund"
    assert result.reason_code == "already_refunded"


# -- R9: system record wins over the customer's claimed date -----------------


def test_r9_system_record_wins_when_claim_says_eligible_but_system_says_expired():
    order = make_order(days_since_delivery=35)  # system: expired
    request = make_request(claimed_days_since_delivery=10)  # customer claims: eligible
    result = resolve_ground_truth(order, make_customer(), make_history(), request)
    assert result.action == "reject_refund"
    assert result.reason_code == "window_expired"
    assert "R9" in result.rules_involved


def test_r9_system_record_wins_when_claim_says_expired_but_system_says_eligible():
    order = make_order(days_since_delivery=10)  # system: eligible
    request = make_request(claimed_days_since_delivery=90)  # customer claims: expired
    result = resolve_ground_truth(order, make_customer(), make_history(), request)
    assert result.action == "process_refund"
    assert "R9" in result.rules_involved


def test_r9_not_tagged_when_claim_matches_system():
    order = make_order(days_since_delivery=10)
    request = make_request(claimed_days_since_delivery=10)
    result = resolve_ground_truth(order, make_customer(), make_history(), request)
    assert "R9" not in result.rules_involved


# -- R10: 3+ refunds in the last 90 days escalates ---------------------------


def test_r10_frequent_refunder_escalates():
    order = make_order(days_since_delivery=5)
    history = make_history([10, 20, 30])
    result = resolve_ground_truth(order, make_customer(), history, make_request())
    assert result.action == "escalate"
    assert result.reason_code == "frequent_refunds"
    assert "R10" in result.rules_involved


def test_r10_two_recent_refunds_does_not_escalate():
    order = make_order(days_since_delivery=5)
    history = make_history([10, 20])
    result = resolve_ground_truth(order, make_customer(), history, make_request())
    assert result.action == "process_refund"


def test_r10_refunds_older_than_90_days_do_not_count():
    order = make_order(days_since_delivery=5)
    history = make_history([91, 92, 93])
    result = resolve_ground_truth(order, make_customer(), history, make_request())
    assert result.action == "process_refund"


def test_r10_does_not_override_a_reject():
    # Documented choice: R10 only converts a would-be process into an
    # escalate; a request that would already reject (window expired) stays
    # a reject even for a frequent refunder.
    order = make_order(days_since_delivery=90)
    history = make_history([10, 20, 30])
    result = resolve_ground_truth(order, make_customer(), history, make_request())
    assert result.action == "reject_refund"
    assert result.reason_code == "window_expired"


# -- Interactions explicitly listed in the Phase 1 gate ----------------------


def test_interaction_vip_plus_damaged():
    # 60 (damaged) + 15 (VIP) = 75-day window.
    order = make_order(condition=ItemCondition.DAMAGED, days_since_delivery=70)
    result = resolve_ground_truth(order, make_customer(is_vip=True), make_history(), make_request())
    assert result.action == "process_refund"
    assert {"R2", "R3"} <= set(result.rules_involved)


def test_interaction_vip_plus_damaged_boundary_75_and_76():
    within = make_order(condition=ItemCondition.DAMAGED, days_since_delivery=75)
    outside = make_order(condition=ItemCondition.DAMAGED, days_since_delivery=76)
    vip = make_customer(is_vip=True)
    assert resolve_ground_truth(within, vip, make_history(), make_request()).action == "process_refund"
    assert resolve_ground_truth(outside, vip, make_history(), make_request()).action == "reject_refund"


def test_interaction_opened_electronics_as_a_gift():
    order = make_order(
        category=ItemCategory.ELECTRONICS,
        is_opened=True,
        is_gift=True,
        item_price=200.0,
        days_since_delivery=5,
    )
    result = resolve_ground_truth(order, make_customer(), make_history(), make_request())
    assert result.action == "process_refund"
    assert result.amount == 170.0
    assert result.method == "store_credit"
    assert {"R5", "R6"} <= set(result.rules_involved)


def test_interaction_vip_gift_opened_electronics_extends_window_too():
    # VIP + gift + opened (non-damaged) electronics: window = 30+15=45,
    # amount = 85%, method = store_credit — all three rules stack.
    order = make_order(
        category=ItemCategory.ELECTRONICS,
        is_opened=True,
        is_gift=True,
        item_price=200.0,
        days_since_delivery=45,
    )
    result = resolve_ground_truth(order, make_customer(is_vip=True), make_history(), make_request())
    assert result.action == "process_refund"
    assert result.amount == 170.0
    assert result.method == "store_credit"
    assert {"R3", "R5", "R6"} <= set(result.rules_involved)
