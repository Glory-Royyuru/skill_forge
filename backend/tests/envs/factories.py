"""Small factories for building policy test fixtures without repeating all
five dataclass constructors in every test.
"""

from __future__ import annotations

from skillforge.envs.ecommerce.models import (
    Customer,
    ItemCategory,
    ItemCondition,
    Order,
    OrderHistory,
    RefundHistoryEntry,
    RefundRequest,
)


def make_order(
    order_id: str = "ORD-1",
    customer_id: str = "CUST-1",
    item_name: str = "Widget",
    item_price: float = 100.0,
    category: ItemCategory = ItemCategory.HOME,
    condition: ItemCondition = ItemCondition.NEW,
    is_final_sale: bool = False,
    is_gift: bool = False,
    is_opened: bool = False,
    days_since_delivery: int = 10,
    already_refunded: bool = False,
) -> Order:
    return Order(
        order_id=order_id,
        customer_id=customer_id,
        item_name=item_name,
        item_price=item_price,
        category=category,
        condition=condition,
        is_final_sale=is_final_sale,
        is_gift=is_gift,
        is_opened=is_opened,
        days_since_delivery=days_since_delivery,
        already_refunded=already_refunded,
    )


def make_customer(customer_id: str = "CUST-1", name: str = "Test Customer", is_vip: bool = False) -> Customer:
    return Customer(customer_id=customer_id, name=name, is_vip=is_vip)


def make_history(refund_days_ago: list[int] | None = None) -> OrderHistory:
    entries = [
        RefundHistoryEntry(order_id=f"ORD-hist-{i}", days_ago=d, amount=25.0)
        for i, d in enumerate(refund_days_ago or [])
    ]
    return OrderHistory(entries=entries)


def make_request(
    order_id: str = "ORD-1",
    claimed_days_since_delivery: int | None = None,
    message: str = "I'd like a refund.",
) -> RefundRequest:
    return RefundRequest(
        order_id=order_id, message=message, claimed_days_since_delivery=claimed_days_since_delivery
    )
