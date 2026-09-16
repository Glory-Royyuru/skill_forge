"""Tool schemas, argument validation, and the in-universe policy handbook
text for `view_policy`.

`view_policy` is a real tool the learner is meant to use, so its text
reads like an actual customer-service handbook (natural language,
no "R1"/"R2" rule ids). "Not shown verbatim to the learner" (per the
spec) is interpreted as: the evaluator's internal rule-id bookkeeping and
`resolve_ground_truth`'s exact branching logic are never exposed — not
that the tool itself should be crippled or removed.
"""

from __future__ import annotations

from typing import Any

from skillforge.llm.types import ToolSpec

TERMINAL_TOOLS = {"process_refund", "reject_refund", "escalate"}

ECOMMERCE_TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="search_orders",
        description="Search orders by free-text query (order id, item name, or customer name).",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    ),
    ToolSpec(
        name="view_order",
        description="View full details of one order by id.",
        parameters={
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    ),
    ToolSpec(
        name="view_customer",
        description="View a customer's profile.",
        parameters={
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
        },
    ),
    ToolSpec(
        name="view_policy",
        description="View a section of the refund policy handbook.",
        parameters={
            "type": "object",
            "properties": {"section": {"type": "string"}},
            "required": ["section"],
        },
    ),
    ToolSpec(
        name="view_order_history",
        description="View a customer's past refund history.",
        parameters={
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
        },
    ),
    ToolSpec(
        name="process_refund",
        description="Issue a refund for an order. Terminal action.",
        parameters={
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "amount": {"type": "number"},
                "method": {"type": "string", "enum": ["original_payment", "store_credit"]},
            },
            "required": ["order_id", "amount", "method"],
        },
    ),
    ToolSpec(
        name="reject_refund",
        description="Reject a refund request. Terminal action.",
        parameters={
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "reason_code": {"type": "string"},
            },
            "required": ["order_id", "reason_code"],
        },
    ),
    ToolSpec(
        name="escalate",
        description="Escalate an order for human review. Terminal action.",
        parameters={
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "reason_code": {"type": "string"},
            },
            "required": ["order_id", "reason_code"],
        },
    ),
]

TOOLS_BY_NAME: dict[str, ToolSpec] = {t.name: t for t in ECOMMERCE_TOOLS}

POLICY_SECTIONS: dict[str, str] = {
    "refund_window": "Standard items may be refunded within 30 days of delivery.",
    "damaged_items": "Damaged or defective items may be refunded within 60 days of delivery.",
    "vip": "VIP customers receive a 15-day extension on any applicable refund window.",
    "final_sale": (
        "Final sale items are not refundable, except items that arrived damaged and "
        "are reported within 7 days of delivery."
    ),
    "electronics": "Opened electronics that are not damaged are refunded at 85% of the item price.",
    "gifts": "Gift orders are refunded as store credit only.",
    "high_value": "Refunds exceeding $500 after adjustments must be escalated for manual review.",
    "frequent_refunds": (
        "Customers with 3 or more refunds in the last 90 days must be escalated for manual review."
    ),
}


def validate_args(args: dict, schema: dict) -> tuple[bool, str | None]:
    """Minimal JSON-schema-shaped validator: required fields, known
    fields only, primitive type checks, and enum membership.
    """
    if not isinstance(args, dict):
        return False, "args_must_be_object"

    for name in schema.get("required", []):
        if name not in args:
            return False, f"missing_required_field:{name}"

    properties: dict[str, Any] = schema.get("properties", {})
    for key, value in args.items():
        if key not in properties:
            return False, f"unexpected_field:{key}"
        prop_schema = properties[key]
        expected_type = prop_schema.get("type")
        if expected_type and not _type_matches(value, expected_type):
            return False, f"wrong_type:{key}"
        enum_values = prop_schema.get("enum")
        if enum_values is not None and value not in enum_values:
            return False, f"invalid_enum_value:{key}"

    return True, None


def _type_matches(value: Any, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "object":
        return isinstance(value, dict)
    return True
