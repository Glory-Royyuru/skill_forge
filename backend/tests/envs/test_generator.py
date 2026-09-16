"""Tests for the seeded task generator: determinism, split coverage, and
that boundary/interaction scenarios and distractors actually show up.
"""

from __future__ import annotations

import dataclasses

import pytest

from skillforge.envs.ecommerce.generator import RECIPES, SPLIT_ORDER, generate_tasks

ALL_RULES = [f"R{i}" for i in range(1, 11)]


def test_same_seed_generates_identical_tasks():
    first = generate_tasks(seed=42, n=300)
    second = generate_tasks(seed=42, n=300)
    assert [dataclasses.asdict(t) for t in first] == [dataclasses.asdict(t) for t in second]


def test_different_seed_generates_different_tasks():
    a = generate_tasks(seed=42, n=300)
    b = generate_tasks(seed=43, n=300)
    assert [dataclasses.asdict(t) for t in a] != [dataclasses.asdict(t) for t in b]


def test_requested_count_is_respected():
    tasks = generate_tasks(seed=1, n=100)
    assert len(tasks) == 100


def test_rejects_n_too_small_for_guaranteed_coverage():
    min_n = len(RECIPES) * len(SPLIT_ORDER)
    with pytest.raises(ValueError):
        generate_tasks(seed=1, n=min_n - 1)


def test_every_rule_appears_in_every_split_at_default_n():
    tasks = generate_tasks(seed=42, n=300)
    by_split: dict[str, set[str]] = {s: set() for s in SPLIT_ORDER}
    for task in tasks:
        by_split[task.split].update(task.ground_truth["rules_involved"])

    for split in SPLIT_ORDER:
        missing = [r for r in ALL_RULES if r not in by_split[split]]
        assert not missing, f"split={split} is missing rules {missing}"


def test_every_rule_appears_in_every_split_at_minimum_n():
    min_n = len(RECIPES) * len(SPLIT_ORDER)
    tasks = generate_tasks(seed=99, n=min_n)
    by_split: dict[str, set[str]] = {s: set() for s in SPLIT_ORDER}
    for task in tasks:
        by_split[task.split].update(task.ground_truth["rules_involved"])

    for split in SPLIT_ORDER:
        missing = [r for r in ALL_RULES if r not in by_split[split]]
        assert not missing, f"split={split} is missing rules {missing}"


def test_splits_are_all_present_and_roughly_proportioned():
    tasks = generate_tasks(seed=42, n=300)
    counts = {s: sum(1 for t in tasks if t.split == s) for s in SPLIT_ORDER}
    assert sum(counts.values()) == 300
    assert counts["train"] > counts["validation"]
    assert counts["train"] > counts["test"]
    for split in SPLIT_ORDER:
        assert counts[split] > 0


def test_boundary_days_are_present():
    tasks = generate_tasks(seed=42, n=300)
    days_seen = {t.initial_state["order"]["days_since_delivery"] for t in tasks}
    for boundary in (30, 31, 60, 61, 45, 46):
        assert boundary in days_seen


def test_distractor_orders_appear_in_some_tasks():
    tasks = generate_tasks(seed=42, n=300)
    assert any(t.initial_state["distractor_orders"] for t in tasks)


def test_date_conflict_distractor_appears():
    tasks = generate_tasks(seed=42, n=300)
    conflicts = [
        t
        for t in tasks
        if t.initial_state["request"]["claimed_days_since_delivery"]
        != t.initial_state["order"]["days_since_delivery"]
    ]
    assert conflicts


def test_task_ids_are_unique():
    tasks = generate_tasks(seed=42, n=300)
    ids = [t.id for t in tasks]
    assert len(ids) == len(set(ids))


def test_order_ids_are_unique_across_tasks():
    tasks = generate_tasks(seed=42, n=300)
    order_ids = [t.initial_state["order"]["order_id"] for t in tasks]
    assert len(order_ids) == len(set(order_ids))
