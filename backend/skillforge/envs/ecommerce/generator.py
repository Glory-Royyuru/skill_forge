"""Seeded, deterministic, stratified task generator for the e-commerce
refund env.

Three layers, all driven off one `random.Random(seed)` so the whole
sequence — and therefore the output — is reproducible for a given
`(seed, n)`:

1. **Recipes**: one scenario per rule/boundary/interaction the Phase 1
   gate requires (R1-R10, every boundary day, every named interaction).
   Each recipe is instantiated once per split, so every rule and every
   boundary day is *guaranteed* present in every split regardless of `n`
   or RNG luck.
2. **Stratified cells**: a weighted menu of scenario generators, each
   tagged with the exact (decision bucket, interaction flag, R1-only flag)
   it produces. For each split, the *remaining* budget after recipes is
   allocated across buckets to hit the target decision distribution
   (process_full ~25%, process_adjusted ~20%, reject ~30%, escalate ~25%),
   then across each bucket's cells by weight — a direct, exact
   construction rather than rejection sampling, so the ±5% target and the
   interaction/R1-only shares are hit by the arithmetic itself, not by
   chance. Every generated bundle is self-checked against its cell's
   declared classification (see `classify_expected`) so a future change to
   `policy.py` that silently breaks a cell's assumptions fails loudly here
   instead of quietly skewing the stats.
3. **Cross-cutting overlay**: independent of bucket/cell, every generated
   bundle gets a random claimed-date conflict (R9) and 0-3 distractor
   orders, exactly as before.

A single globally-incrementing index (never reset per split or per cell)
drives every `order_id`/`customer_id`, which makes every task's
`(request, initial_state)` unique by construction — see
`test_generator.py::test_no_duplicate_request_and_state_across_all_tasks`.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import asdict, dataclass
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
from skillforge.envs.ecommerce.policy import Expected, resolve_ground_truth

DEFAULT_N = 1400
# Chosen so the default validation/test splits land exactly on 220 tasks
# each (the size the Phase 1.1 per-rule minimums are anchored to) and train
# on 960. For any other `n`, split sizes scale proportionally (see
# `_split_target_counts`).
DEFAULT_SPLIT_COUNTS = {"train": 960, "validation": 220, "test": 220}
SPLIT_ORDER = ["train", "validation", "test"]

# Per-rule minimum task counts, anchored to DEFAULT_SPLIT_COUNTS and scaled
# proportionally for other `n` (see `min_per_rule_at_default`).
MIN_PER_RULE_AT_DEFAULT = {"train": 60, "validation": 20, "test": 20}

# Decision-bucket target shares of each split's total task count. "adjusted"
# means the process_refund involved R5 (85% cut) and/or R6 (store credit) —
# exactly the definition the Phase 1.1 spec gives.
BUCKET_TARGET_PCT = {
    "process_full": 0.25,
    "process_adjusted": 0.20,
    "reject": 0.30,
    "escalate": 0.25,
}
BUCKET_NAMES = list(BUCKET_TARGET_PCT)

# A task counts as an "interaction" task when 2+ rules other than R1/R9 are
# involved (R1 and R9 don't count, per the Phase 1.1 spec).
INTERACTION_MIN_SHARE = 0.40
R1_ONLY_MAX_SHARE = 0.20

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
NON_ELECTRONICS_CATEGORIES = [c for c in ItemCategory if c != ItemCategory.ELECTRONICS]

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


def _apply_crosscutting(rng: random.Random, kwargs: dict, allow_r9: bool = True) -> dict:
    """R9 date-conflict and distractor orders: independent of which cell
    produced `kwargs`, and never able to change the decision (see
    policy.py — the claimed date is never read for eligibility).

    `allow_r9=False` for cells declared `r1_only=True`: R9 would still
    never change their decision, but it WOULD add "R9" to rules_involved,
    breaking the promise that rules_involved is exactly ["R1"].
    """
    claimed_delta = 0
    if allow_r9 and rng.random() < 0.35:
        claimed_delta = rng.choice([-20, -15, -10, -5, 5, 10, 15, 20])
    n_distractors = rng.choices([0, 1, 2, 3], weights=[40, 30, 20, 10])[0]
    return {**kwargs, "claimed_days_delta": claimed_delta, "n_distractor_orders": n_distractors}


def classify_expected(expected: Expected) -> tuple[str, bool, bool]:
    """(bucket, is_interaction, is_r1_only) for a resolved Expected.

    `interaction` = 2+ rules other than R1/R9. `r1_only` = rules_involved is
    exactly ["R1"]. `bucket` maps process_refund to "process_full" or
    "process_adjusted" (R5 and/or R6 present) per the Phase 1.1 spec's
    literal definition ("85% or store credit").
    """
    rules = expected.rules_involved
    substantive = set(rules) - {"R1", "R9"}
    interaction = len(substantive) >= 2
    r1_only = rules == ["R1"]

    if expected.action == "reject_refund":
        bucket = "reject"
    elif expected.action == "escalate":
        bucket = "escalate"
    else:
        bucket = "process_adjusted" if ("R5" in rules or "R6" in rules) else "process_full"
    return bucket, interaction, r1_only


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


# -- Stratified cells: weighted menu, each tagged with its own outcome -----


@dataclass(frozen=True)
class Cell:
    name: str
    bucket: str
    interaction: bool
    r1_only: bool
    weight: float
    build: Callable[[random.Random], dict]


def _cat(rng: random.Random) -> ItemCategory:
    return rng.choice(NON_ELECTRONICS_CATEGORIES)


CELLS: list[Cell] = [
    # -- process_full ------------------------------------------------------
    Cell(
        "full_plain", "process_full", interaction=False, r1_only=True, weight=1,
        build=lambda rng: {
            "category": _cat(rng), "days_since_delivery": rng.randint(1, 29),
            "refund_count_90d": rng.randint(0, 1),
        },
    ),
    Cell(
        "full_damaged", "process_full", interaction=False, r1_only=False, weight=2,
        build=lambda rng: {
            "category": _cat(rng), "condition": ItemCondition.DAMAGED,
            "days_since_delivery": rng.randint(1, 59), "refund_count_90d": rng.randint(0, 1),
        },
    ),
    Cell(
        "full_vip", "process_full", interaction=False, r1_only=False, weight=2,
        build=lambda rng: {
            "category": _cat(rng), "is_vip": True,
            "days_since_delivery": rng.randint(1, 44), "refund_count_90d": rng.randint(0, 1),
        },
    ),
    Cell(
        "full_final_sale_exception", "process_full", interaction=False, r1_only=False, weight=4,
        build=lambda rng: {
            "category": ItemCategory.CLOTHING, "condition": ItemCondition.DAMAGED,
            "is_final_sale": True, "days_since_delivery": rng.randint(0, 7),
        },
    ),
    Cell(
        "full_damaged_vip", "process_full", interaction=True, r1_only=False, weight=5,
        build=lambda rng: {
            "category": _cat(rng), "condition": ItemCondition.DAMAGED, "is_vip": True,
            "days_since_delivery": rng.randint(1, 74), "refund_count_90d": rng.randint(0, 1),
        },
    ),
    # -- process_adjusted ---------------------------------------------------
    Cell(
        "adj_electronics", "process_adjusted", interaction=False, r1_only=False, weight=3,
        build=lambda rng: {
            "category": ItemCategory.ELECTRONICS, "is_opened": True,
            "days_since_delivery": rng.randint(1, 29),
        },
    ),
    Cell(
        "adj_gift", "process_adjusted", interaction=False, r1_only=False, weight=3,
        build=lambda rng: {"category": _cat(rng), "is_gift": True, "days_since_delivery": rng.randint(1, 29)},
    ),
    Cell(
        "adj_electronics_gift", "process_adjusted", interaction=True, r1_only=False, weight=3,
        build=lambda rng: {
            "category": ItemCategory.ELECTRONICS, "is_opened": True, "is_gift": True,
            "days_since_delivery": rng.randint(1, 29),
        },
    ),
    Cell(
        "adj_damaged_gift", "process_adjusted", interaction=True, r1_only=False, weight=2,
        build=lambda rng: {
            "category": _cat(rng), "condition": ItemCondition.DAMAGED, "is_gift": True,
            "days_since_delivery": rng.randint(1, 59),
        },
    ),
    Cell(
        "adj_vip_electronics", "process_adjusted", interaction=True, r1_only=False, weight=2,
        build=lambda rng: {
            "category": ItemCategory.ELECTRONICS, "is_opened": True, "is_vip": True,
            "days_since_delivery": rng.randint(1, 44),
        },
    ),
    Cell(
        "adj_vip_gift", "process_adjusted", interaction=True, r1_only=False, weight=2,
        build=lambda rng: {
            "category": _cat(rng), "is_gift": True, "is_vip": True, "days_since_delivery": rng.randint(1, 44)
        },
    ),
    Cell(
        "adj_vip_electronics_gift", "process_adjusted", interaction=True, r1_only=False, weight=2,
        build=lambda rng: {
            "category": ItemCategory.ELECTRONICS, "is_opened": True, "is_gift": True, "is_vip": True,
            "days_since_delivery": rng.randint(1, 44),
        },
    ),
    # -- reject ---------------------------------------------------------
    Cell(
        "rej_plain", "reject", interaction=False, r1_only=True, weight=1,
        build=lambda rng: {"category": _cat(rng), "days_since_delivery": rng.randint(31, 90)},
    ),
    Cell(
        "rej_damaged", "reject", interaction=False, r1_only=False, weight=2,
        build=lambda rng: {
            "category": _cat(rng), "condition": ItemCondition.DAMAGED,
            "days_since_delivery": rng.randint(61, 100),
        },
    ),
    Cell(
        "rej_vip", "reject", interaction=False, r1_only=False, weight=2,
        build=lambda rng: {
            "category": _cat(rng), "is_vip": True, "days_since_delivery": rng.randint(46, 100)
        },
    ),
    Cell(
        "rej_damaged_vip", "reject", interaction=True, r1_only=False, weight=5,
        build=lambda rng: {
            "category": _cat(rng), "condition": ItemCondition.DAMAGED, "is_vip": True,
            "days_since_delivery": rng.randint(76, 110),
        },
    ),
    Cell(
        "rej_final_sale_plain", "reject", interaction=False, r1_only=False, weight=3,
        build=lambda rng: {
            "category": ItemCategory.CLOTHING, "is_final_sale": True,
            "days_since_delivery": rng.randint(1, 90),
        },
    ),
    Cell(
        "rej_final_sale_damaged_late", "reject", interaction=False, r1_only=False, weight=3,
        build=lambda rng: {
            "category": ItemCategory.CLOTHING, "condition": ItemCondition.DAMAGED, "is_final_sale": True,
            "days_since_delivery": rng.randint(8, 90),
        },
    ),
    Cell(
        "rej_already_refunded", "reject", interaction=False, r1_only=False, weight=11,
        build=lambda rng: {
            "category": _cat(rng), "already_refunded": True, "days_since_delivery": rng.randint(1, 90)
        },
    ),
    # -- escalate ---------------------------------------------------------
    Cell(
        "esc_high_value", "escalate", interaction=False, r1_only=False, weight=2,
        build=lambda rng: {
            "category": _cat(rng), "price": round(rng.uniform(510, 900), 2),
            "days_since_delivery": rng.randint(1, 29),
        },
    ),
    Cell(
        "esc_frequent", "escalate", interaction=False, r1_only=False, weight=2,
        build=lambda rng: {
            "category": _cat(rng), "refund_count_90d": rng.randint(3, 5),
            "days_since_delivery": rng.randint(1, 29),
        },
    ),
    Cell(
        "esc_high_value_frequent", "escalate", interaction=True, r1_only=False, weight=3,
        build=lambda rng: {
            "category": _cat(rng), "price": round(rng.uniform(510, 900), 2),
            "refund_count_90d": rng.randint(3, 5), "days_since_delivery": rng.randint(1, 29),
        },
    ),
    Cell(
        "esc_electronics_high_value", "escalate", interaction=True, r1_only=False, weight=2,
        build=lambda rng: {
            "category": ItemCategory.ELECTRONICS, "is_opened": True, "price": round(rng.uniform(650, 900), 2),
            "days_since_delivery": rng.randint(1, 29),
        },
    ),
    Cell(
        "esc_gift_high_value", "escalate", interaction=True, r1_only=False, weight=2,
        build=lambda rng: {
            "category": _cat(rng), "is_gift": True, "price": round(rng.uniform(510, 900), 2),
            "days_since_delivery": rng.randint(1, 29),
        },
    ),
    Cell(
        "esc_damaged_high_value", "escalate", interaction=True, r1_only=False, weight=2,
        build=lambda rng: {
            "category": _cat(rng), "condition": ItemCondition.DAMAGED,
            "price": round(rng.uniform(510, 900), 2), "days_since_delivery": rng.randint(1, 59),
        },
    ),
    Cell(
        "esc_vip_high_value", "escalate", interaction=True, r1_only=False, weight=2,
        build=lambda rng: {
            "category": _cat(rng), "is_vip": True, "price": round(rng.uniform(510, 900), 2),
            "days_since_delivery": rng.randint(1, 44),
        },
    ),
    Cell(
        "esc_electronics_frequent", "escalate", interaction=True, r1_only=False, weight=2,
        build=lambda rng: {
            "category": ItemCategory.ELECTRONICS, "is_opened": True, "refund_count_90d": rng.randint(3, 5),
            "days_since_delivery": rng.randint(1, 29),
        },
    ),
    Cell(
        "esc_gift_frequent", "escalate", interaction=True, r1_only=False, weight=2,
        build=lambda rng: {
            "category": _cat(rng), "is_gift": True, "refund_count_90d": rng.randint(3, 5),
            "days_since_delivery": rng.randint(1, 29),
        },
    ),
]

CELLS_BY_BUCKET: dict[str, list[Cell]] = {b: [c for c in CELLS if c.bucket == b] for b in BUCKET_NAMES}


def _allocate(total: int, weights: list[float]) -> list[int]:
    """Split `total` (a non-negative int) across `weights` proportionally,
    rounding by largest remainder so the parts sum to exactly `total`.
    """
    if total <= 0 or not weights:
        return [0] * len(weights)
    weight_sum = sum(weights)
    raw = [total * w / weight_sum for w in weights]
    floors = [int(x) for x in raw]
    remainder = total - sum(floors)
    order = sorted(range(len(weights)), key=lambda i: raw[i] - floors[i], reverse=True)
    for i in order[:remainder]:
        floors[i] += 1
    return floors


def _split_target_counts(n: int) -> dict[str, int]:
    counts = _allocate(n, [DEFAULT_SPLIT_COUNTS[s] for s in SPLIT_ORDER])
    return dict(zip(SPLIT_ORDER, counts, strict=True))


def min_per_rule_at_default(split: str, target_count: int) -> int:
    default_total = DEFAULT_SPLIT_COUNTS[split]
    return max(1, round(MIN_PER_RULE_AT_DEFAULT[split] * target_count / default_total))


def _bucket_targets(total: int) -> dict[str, int]:
    counts = _allocate(total, [BUCKET_TARGET_PCT[b] for b in BUCKET_NAMES])
    return dict(zip(BUCKET_NAMES, counts, strict=True))


def generate_tasks(
    seed: int,
    n: int = DEFAULT_N,
    split_ratios: dict[str, float] | None = None,
) -> list[Task]:
    """Deterministic for a given `(seed, n)`. `split_ratios` is accepted
    for backward compatibility but ignored — split sizing is now derived
    from `DEFAULT_SPLIT_COUNTS`, scaled to `n` (see `_split_target_counts`),
    since the decision-bucket/interaction/R1-only targets are all defined
    as shares of each split's own size, not of `n` as a whole.
    """
    del split_ratios
    rng = random.Random(seed)
    split_targets = _split_target_counts(n)

    index = 0
    tasks: list[Task] = []

    for split in SPLIT_ORDER:
        target_count = split_targets[split]

        # -- Recipes: fixed, one per (recipe, split). ------------------------
        recipe_bundles: list[Bundle] = []
        recipe_bucket_counts = dict.fromkeys(BUCKET_NAMES, 0)
        for _name, builder in RECIPES:
            bundle = builder(rng, index, seed)
            index += 1
            order, customer, history, request, _distractors = bundle
            expected = resolve_ground_truth(order, customer, history, request)
            bucket, _interaction, _r1_only = classify_expected(expected)
            recipe_bucket_counts[bucket] += 1
            recipe_bundles.append(bundle)

        if len(RECIPES) > target_count:
            raise ValueError(
                f"n={n} is too small: split={split} would need to hold at least "
                f"{len(RECIPES)} recipe tasks alone (got a target of {target_count})."
            )

        # -- Stratified cells: fill the remaining budget per bucket. ---------
        bucket_targets = _bucket_targets(target_count)
        stratified_bucket_targets: dict[str, int] = {}
        for bucket in BUCKET_NAMES:
            remaining = bucket_targets[bucket] - recipe_bucket_counts[bucket]
            if remaining < 0:
                raise ValueError(
                    f"n={n} is too small: split={split} bucket={bucket} target "
                    f"({bucket_targets[bucket]}) is already exceeded by recipes alone "
                    f"({recipe_bucket_counts[bucket]}). Increase n."
                )
            stratified_bucket_targets[bucket] = remaining

        stratified_bundles: list[Bundle] = []
        for bucket in BUCKET_NAMES:
            cells = CELLS_BY_BUCKET[bucket]
            counts = _allocate(stratified_bucket_targets[bucket], [c.weight for c in cells])
            for cell, count in zip(cells, counts, strict=True):
                for _ in range(count):
                    kwargs = _apply_crosscutting(rng, cell.build(rng), allow_r9=not cell.r1_only)
                    bundle = _build_order_bundle(rng, index, seed, **kwargs)
                    index += 1
                    order, customer, history, request, _distractors = bundle
                    expected = resolve_ground_truth(order, customer, history, request)
                    actual_bucket, actual_interaction, actual_r1_only = classify_expected(expected)
                    if (actual_bucket, actual_interaction, actual_r1_only) != (
                        cell.bucket, cell.interaction, cell.r1_only,
                    ):
                        raise AssertionError(
                            f"generator cell {cell.name!r} produced "
                            f"(bucket={actual_bucket}, interaction={actual_interaction}, "
                            f"r1_only={actual_r1_only}) but declared "
                            f"(bucket={cell.bucket}, interaction={cell.interaction}, "
                            f"r1_only={cell.r1_only}) — rules_involved={expected.rules_involved}."
                        )
                    stratified_bundles.append(bundle)

        for order, customer, history, request, distractors in recipe_bundles + stratified_bundles:
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
                    id=f"ecommerce-{seed}-{len(tasks):05d}",
                    seed=seed,
                    split=split,
                    request=request.message,
                    initial_state=initial_state,
                    ground_truth=asdict(expected),
                )
            )

        _validate_split_rule_minimums(split, target_count, n, tasks)

    return tasks


def _validate_split_rule_minimums(split: str, target_count: int, n: int, tasks_so_far: list[Task]) -> None:
    """The Phase 1.1 spec's per-rule minimums (60 train / 20 val+test) are
    anchored explicitly to "the default size (220)" — i.e. `n ==
    DEFAULT_N`. That exact case is hard-enforced here (an integer
    allocation-rounding bug should fail loudly, not silently skew stats).

    For any other `n`, proportional scaling of an already-integer-rounded
    allocation can create small, harmless shortfalls with no real
    guarantee attached to them (there is no spec'd minimum at arbitrary
    `n`) — so only a much weaker sanity check applies there: every rule
    must appear at least once, which still catches a genuinely broken
    generator without rejecting reasonable custom `n` choices.
    """
    rule_counts = dict.fromkeys((f"R{i}" for i in range(1, 11)), 0)
    for task in tasks_so_far:
        if task.split != split:
            continue
        for rule in task.ground_truth["rules_involved"]:
            rule_counts[rule] += 1

    min_required = min_per_rule_at_default(split, target_count) if n == DEFAULT_N else 1
    short = {r: c for r, c in rule_counts.items() if c < min_required}
    if short:
        raise ValueError(
            f"split={split} failed its per-rule minimum ({min_required} at target_count="
            f"{target_count}, n={n}): {short}. This indicates a generator weighting bug, "
            f"not an `n` that's merely small — please adjust CELLS weights."
        )
