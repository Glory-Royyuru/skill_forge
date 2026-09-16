"""Domain dataclasses for the e-commerce refund environment.

`Order.days_since_delivery` is the *system* record — the only date field
`resolve_ground_truth` ever reads (see policy.py / R9). A customer's
claimed date lives only on `RefundRequest.claimed_days_since_delivery` and
is flavor/distractor text for the request message; policy code never
touches it, so "system record wins" holds by construction, not by a
runtime check.

All enums subclass `str` so dataclass instances serialize straight to JSON
via `dataclasses.asdict()` + `json.dumps()` with no custom encoding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ItemCategory(StrEnum):
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    HOME = "home"
    BOOKS = "books"
    OTHER = "other"


class ItemCondition(StrEnum):
    NEW = "new"
    # Used uniformly for both "defective/damaged" (R2) and "damaged on
    # arrival" (R4's final-sale exception) — the spec never distinguishes
    # the two, so one flag covers both.
    DAMAGED = "damaged"


class RefundMethod(StrEnum):
    ORIGINAL_PAYMENT = "original_payment"
    STORE_CREDIT = "store_credit"


class ActionType(StrEnum):
    PROCESS_REFUND = "process_refund"
    REJECT_REFUND = "reject_refund"
    ESCALATE = "escalate"


@dataclass
class Order:
    order_id: str
    customer_id: str
    item_name: str
    item_price: float
    category: ItemCategory
    condition: ItemCondition
    is_final_sale: bool
    is_gift: bool
    is_opened: bool
    days_since_delivery: int  # SYSTEM record; the only date resolve_ground_truth reads
    already_refunded: bool


@dataclass
class Customer:
    customer_id: str
    name: str
    is_vip: bool


@dataclass
class RefundHistoryEntry:
    order_id: str
    days_ago: int
    amount: float


@dataclass
class OrderHistory:
    entries: list[RefundHistoryEntry] = field(default_factory=list)

    def count_within(self, days: int) -> int:
        return sum(1 for e in self.entries if e.days_ago <= days)


@dataclass
class RefundRequest:
    order_id: str
    message: str
    # The customer's claim, which may legitimately disagree with
    # `Order.days_since_delivery` (R9 distractor). Never read by policy.
    claimed_days_since_delivery: int | None = None
