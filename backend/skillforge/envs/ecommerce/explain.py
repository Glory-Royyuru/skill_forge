"""Post-case explanations for the Practice learner experience.

Separate from `policy.py` (the pure decision function): this module
translates an already-resolved `Expected` + a learner's trajectory into
natural-language feedback. Everything here is invoked only *after* a case
is decided — never exposed mid-case, so it never leaks ground truth into
an in-progress attempt.
"""

from __future__ import annotations

RULE_TAGS: dict[str, str] = {
    "R1": "Standard Window",
    "R2": "Damaged Item",
    "R3": "VIP Customer",
    "R4": "Final Sale",
    "R5": "Opened Electronics",
    "R6": "Gift Order",
    "R7": "High Value",
    "R8": "Already Refunded",
    "R9": "Date Discrepancy",
    "R10": "Frequent Refunds",
}

RULE_EXPLANATIONS: dict[str, str] = {
    "R1": "the order was within the standard 30-day return window",
    "R2": "the item was damaged, which extends the return window to 60 days",
    "R3": "the customer is a VIP, which adds 15 days to the applicable window",
    "R4": "the item was final sale, which is not refundable except for damage reported within 7 days",
    "R5": "the item was opened electronics in good condition, which refunds at 85% of the price",
    "R6": "the order was a gift, so any refund must be issued as store credit",
    "R7": "the refund amount exceeded $500 and required manager review",
    "R8": "the order had already been refunded",
    "R9": "the customer's stated delivery date did not match the system record; the system record wins",
    "R10": "the customer has had 3 or more refunds in the last 90 days and required manager review",
}

# Which tool call matters when a given rule is in play, and why — used to
# build "missed opportunity" feedback without revealing what that lookup
# would have shown.
_RULE_RELEVANT_TOOL: dict[str, tuple[str, str]] = {
    "R2": ("view_order", "the item's condition"),
    "R3": ("view_customer", "the customer's VIP status"),
    "R4": ("view_order", "whether the item was final sale"),
    "R5": ("view_order", "the item's condition and category"),
    "R6": ("view_order", "whether the order was a gift"),
    "R7": ("view_policy", "the high-value refund policy"),
    "R8": ("view_order", "whether the order was already refunded"),
    "R10": ("view_order_history", "the customer's recent refund history"),
}


def explain_decision(rules_involved: list[str]) -> str:
    reasons = [RULE_EXPLANATIONS[r] for r in rules_involved if r in RULE_EXPLANATIONS]
    if not reasons:
        return "This case followed the standard return policy with no special conditions."
    if len(reasons) == 1:
        return f"This case turned on {reasons[0]}."
    return "This case turned on multiple factors: " + "; ".join(reasons) + "."


def missed_checks(rules_involved: list[str], tools_called: set[str]) -> list[str]:
    missed: list[str] = []
    seen_reasons = set()
    for rule in rules_involved:
        info = _RULE_RELEVANT_TOOL.get(rule)
        if not info:
            continue
        tool, reason = info
        if tool not in tools_called and reason not in seen_reasons:
            missed.append(f"You did not check {reason} before deciding.")
            seen_reasons.add(reason)
    return missed


def rule_tags(rules_involved: list[str]) -> list[str]:
    return [RULE_TAGS[r] for r in rules_involved if r in RULE_TAGS]


def difficulty_for_rules(rules_involved: list[str]) -> str:
    if rules_involved == ["R1"]:
        return "beginner"
    substantive = set(rules_involved) - {"R1", "R9"}
    if len(substantive) >= 2:
        return "advanced"
    return "intermediate"
