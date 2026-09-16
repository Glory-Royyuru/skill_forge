"""Seeded, deterministic task generator for the e-commerce refund env.

Two layers, both driven off one `random.Random(seed)` so the whole
sequence — and therefore the output — is reproducible for a given
`(seed, n)`:

1. **Recipes**: one scenario per rule/boundary/interaction the Phase 1
   gate requires (R1-R10, every boundary day, every listed interaction).
   Each recipe is instantiated once per split (train/validation/test), so
   every rule is *guaranteed* present in every split regardless of `n` or
   RNG luck — not left to chance the way pure random sampling would.
2. **Random filler**: the remaining `n - len(recipes)*3` tasks, fully
   randomized (category, condition, gift/final-sale/opened flags, window
   day, VIP, refund history, a possibly-wrong claimed date, and 0-3
   distractor orders), for volume and diversity. These are split by
   shuffling with the same seeded RNG and slicing by ratio.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import asdict
from functools import partial

from skillforge.envs.base import Task
from skillforge.envs.ecommerce.models import (
    Customer,
    ItemCategory,
    ItemCondition,
    Order,
    OrderHistory,
    RefundHistoryEntry,
    RefundRequest,
)
from skillforge.envs.ecommerce.policy import resolve_ground_truth

DEFAULT_N = 300
DEFAULT_SPLIT_RATIOS = {"train": 0.7, "validation": 0.15, "test": 0.15}
SPLIT_ORDER = ["train", "validation", "test"]

CUSTOMER_NAMES = [
    "Alex Kim", "Jordan Lee", "Morgan Diaz", "Taylor Chen",
    "Sam Patel", "Riley Brooks", "Casey Nguyen", "Drew Foster",
]

ITEM_CATALOG: dict[ItemCategory, list[tuple[str, float]]] = {
    ItemCategory.ELECTRONICS: [
        ("Wireless Headphones", 89.99),
        ("Bluetooth Speaker", 59.99),
        ("Smart Watch", 249.99),
        ("4K Monitor", 349.99),
    ],
    ItemCategory.CLOTHING: [
        ("Winter Jacket", 129.99),
        ("Running Shoes", 79.99),
        ("Wool Sweater", 64.99),
    ],
    ItemCategory.HOME: [
        ("Blender", 49.99),
        ("Cookware Set", 189.99),
        ("Table Lamp", 39.99),
    ],
    ItemCategory.BOOKS: [
        ("Hardcover Novel", 24.99),
        ("Cookbook", 29.99),
    ],
    ItemCategory.OTHER: [
        ("Gift Card Holder", 14.99),
        ("Board Game", 34.99),
    ],
}

Bundle = tuple[Order, Customer, OrderHistory, RefundRequest, list[Order]]


def _build_order_bundle(
    rng: random.Random,
    index: int,
    seed: int,
    *,
    category: ItemCategory = ItemCategory.HOME,
    condition: ItemCondition = ItemCondition.NEW,
    is_final_sale: bool = False,
    is_gift: bool = False,
    is_opened: bool = False,
    days_since_delivery: int = 10,
    is_vip: bool = False,
    already_refunded: bool = False,
    refund_count_90d: int = 0,
    price: float | None = None,
    claimed_days_delta: int = 0,
    n_distractor_orders: int = 0,
) -> Bundle:
    order_id = f"ORD-{seed}-{index:05d}"
    customer_id = f"CUST-{seed}-{index:05d}"
    item_name, catalog_price = rng.choice(ITEM_CATALOG[category])
    item_price = price if price is not None else catalog_price

    order = Order(
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
    customer = Customer(customer_id=customer_id, name=rng.choice(CUSTOMER_NAMES), is_vip=is_vip)
    history = OrderHistory(
        entries=[
            RefundHistoryEntry(
                order_id=f"{order_id}-hist{i}",
                days_ago=rng.randint(1, 85),
                amount=round(rng.uniform(10, 200), 2),
            )
            for i in range(refund_count_90d)
        ]
    )
    distractor_orders = [
        _make_distractor(rng, seed, index, j, customer_id) for j in range(n_distractor_orders)
    ]

    claimed_days = max(0, days_since_delivery + claimed_days_delta)
    message = _build_message(rng, order, claimed_days, distractor_orders)
    request = RefundRequest(order_id=order_id, message=message, claimed_days_since_delivery=claimed_days)

    return order, customer, history, request, distractor_orders


def _make_distractor(rng: random.Random, seed: int, index: int, j: int, customer_id: str) -> Order:
    category = rng.choice(list(ItemCategory))
    item_name, price = rng.choice(ITEM_CATALOG[category])
    return Order(
        order_id=f"ORD-{seed}-{index:05d}-d{j}",
        customer_id=customer_id,
        item_name=item_name,
        item_price=price,
        category=category,
        condition=ItemCondition.NEW,
        is_final_sale=False,
        is_gift=False,
        is_opened=False,
        days_since_delivery=rng.randint(1, 90),
        already_refunded=False,
    )


def _build_message(rng: random.Random, order: Order, claimed_days: int, distractors: list[Order]) -> str:
    parts = [f"Hi, I'd like a refund for my {order.item_name} (order {order.order_id})."]
    parts.append(f"It was delivered {claimed_days} day{'s' if claimed_days != 1 else ''} ago.")
    if order.condition == ItemCondition.DAMAGED:
        parts.append("It arrived damaged.")
    if order.is_gift:
        parts.append("This was a gift.")
    if distractors and rng.random() < 0.5:
        other = rng.choice(distractors)
        parts.append(
            f"(I also have another order, {other.order_id}, but this request is about {order.order_id}.)"
        )
    return " ".join(parts)


# -- Recipes: one guaranteed scenario per rule/boundary/interaction ---------

def _recipe(**kwargs) -> Callable[..., Bundle]:
    kwargs.setdefault("category", ItemCategory.HOME)
    kwargs.setdefault("days_since_delivery", 10)
    return partial(_build_order_bundle, **kwargs)


RECIPES: list[tuple[str, Callable[..., Bundle]]] = [
    ("R1_day30", _recipe(days_since_delivery=30)),
    ("R1_day31", _recipe(days_since_delivery=31)),
    ("R2_day60", _recipe(condition=ItemCondition.DAMAGED, days_since_delivery=60)),
    ("R2_day61", _recipe(condition=ItemCondition.DAMAGED, days_since_delivery=61)),
    ("R3_vip_day45", _recipe(is_vip=True, days_since_delivery=45)),
    ("R3_vip_day46", _recipe(is_vip=True, days_since_delivery=46)),
    ("R2_R3_vip_damaged", _recipe(condition=ItemCondition.DAMAGED, is_vip=True, days_since_delivery=70)),
    (
        "R4_final_sale_damaged_day7",
        _recipe(
            category=ItemCategory.CLOTHING,
            condition=ItemCondition.DAMAGED,
            is_final_sale=True,
            days_since_delivery=7,
        ),
    ),
    (
        "R4_final_sale_damaged_day8",
        _recipe(
            category=ItemCategory.CLOTHING,
            condition=ItemCondition.DAMAGED,
            is_final_sale=True,
            days_since_delivery=8,
        ),
    ),
    (
        "R4_final_sale_plain",
        _recipe(category=ItemCategory.CLOTHING, is_final_sale=True, days_since_delivery=5),
    ),
    ("R5_opened_electronics", _recipe(category=ItemCategory.ELECTRONICS, is_opened=True)),
    (
        "R5_R6_opened_electronics_gift",
        _recipe(category=ItemCategory.ELECTRONICS, is_opened=True, is_gift=True),
    ),
    ("R6_gift", _recipe(is_gift=True)),
    ("R7_over_500", _recipe(category=ItemCategory.ELECTRONICS, is_opened=True, price=700.0)),
    ("R8_already_refunded", _recipe(already_refunded=True)),
    ("R9_claim_in_actual_out", _recipe(days_since_delivery=35, claimed_days_delta=-10)),
    ("R9_claim_out_actual_in", _recipe(days_since_delivery=20, claimed_days_delta=20)),
    ("R10_frequent_refunds", _recipe(refund_count_90d=3)),
]

CATEGORIES = list(ItemCategory)


def _scenario_random(rng: random.Random, index: int, seed: int) -> Bundle:
    category = rng.choices(CATEGORIES, weights=[3, 2, 2, 2, 1])[0]
    condition = ItemCondition.DAMAGED if rng.random() < 0.15 else ItemCondition.NEW
    is_final_sale = rng.random() < 0.12
    is_gift = rng.random() < 0.15
    is_opened = category == ItemCategory.ELECTRONICS and rng.random() < 0.4
    days = rng.randint(0, 100)
    is_vip = rng.random() < 0.25
    already_refunded = rng.random() < 0.05
    refund_count_90d = rng.choices([0, 1, 2, 3, 4], weights=[60, 20, 10, 6, 4])[0]
    claimed_delta = 0 if rng.random() < 0.7 else rng.randint(-15, 15)
    n_distractors = rng.choices([0, 1, 2, 3], weights=[40, 30, 20, 10])[0]

    return _build_order_bundle(
        rng,
        index,
        seed,
        category=category,
        condition=condition,
        is_final_sale=is_final_sale,
        is_gift=is_gift,
        is_opened=is_opened,
        days_since_delivery=days,
        is_vip=is_vip,
        already_refunded=already_refunded,
        refund_count_90d=refund_count_90d,
        claimed_days_delta=claimed_delta,
        n_distractor_orders=n_distractors,
    )


def generate_tasks(
    seed: int,
    n: int = DEFAULT_N,
    split_ratios: dict[str, float] | None = None,
) -> list[Task]:
    min_n = len(RECIPES) * len(SPLIT_ORDER)
    if n < min_n:
        raise ValueError(
            f"n={n} is too small to guarantee rule coverage in every split; "
            f"need at least {min_n} ({len(RECIPES)} recipes x {len(SPLIT_ORDER)} splits)."
        )
    ratios = split_ratios or DEFAULT_SPLIT_RATIOS
    rng = random.Random(seed)

    bundles: list[Bundle] = []
    forced_split: list[str | None] = []

    index = 0
    for _name, builder in RECIPES:
        for split in SPLIT_ORDER:
            bundles.append(builder(rng, index, seed))
            forced_split.append(split)
            index += 1

    n_random = n - len(bundles)
    for _ in range(n_random):
        bundles.append(_scenario_random(rng, index, seed))
        forced_split.append(None)
        index += 1

    # Assign splits for filler tasks by shuffling their positions with the
    # same seeded RNG, then slicing by ratio — recipe tasks already have a
    # forced split and are untouched here.
    unforced_positions = [i for i, s in enumerate(forced_split) if s is None]
    shuffled = unforced_positions[:]
    rng.shuffle(shuffled)
    n_unforced = len(shuffled)
    n_train = round(n_unforced * ratios["train"])
    n_val = round(n_unforced * ratios["validation"])

    split_for_position: dict[int, str] = {}
    for pos in shuffled[:n_train]:
        split_for_position[pos] = "train"
    for pos in shuffled[n_train : n_train + n_val]:
        split_for_position[pos] = "validation"
    for pos in shuffled[n_train + n_val :]:
        split_for_position[pos] = "test"

    tasks: list[Task] = []
    for i, bundle in enumerate(bundles):
        split = forced_split[i] or split_for_position[i]
        order, customer, history, request, distractors = bundle
        expected = resolve_ground_truth(order, customer, history, request)
        initial_state = {
            "order": asdict(order),
            "customer": asdict(customer),
            "history": {"entries": [asdict(e) for e in history.entries]},
            "request": asdict(request),
            "distractor_orders": [asdict(o) for o in distractors],
        }
        tasks.append(
            Task(
                id=f"ecommerce-{seed}-{i:05d}",
                seed=seed,
                split=split,
                request=request.message,
                initial_state=initial_state,
                ground_truth=asdict(expected),
            )
        )
    return tasks
