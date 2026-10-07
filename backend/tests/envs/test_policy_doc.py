from __future__ import annotations

from skillforge.envs.ecommerce.tools import load_policy_document

REQUIRED_VALUES = ["30", "60", "15", "7", "85%", "$500", "90 days"]


def test_policy_document_contains_required_values():
    text = load_policy_document()
    for value in REQUIRED_VALUES:
        assert value in text, f"missing required value {value!r}"
    assert "3" in text and "refund" in text.lower()


def test_policy_document_is_not_a_numbered_rule_list():
    text = load_policy_document()
    for marker in ("R1", "R2", "R3", "R10"):
        assert marker not in text


def test_policy_document_has_no_task_specific_fields():
    text = load_policy_document().lower()
    for leaked in ("order_id", "customer_id", "ord-", "cust-"):
        assert leaked not in text
