"""Tests for the seeded, stratified task generator: determinism, split
coverage, decision-distribution/interaction/R1-only targets (Phase 1.1),
and that boundary/interaction scenarios and distractors actually show up.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from skillforge.envs.ecommerce.generator import DEFAULT_N, RECIPES, SPLIT_ORDER, generate_tasks

ALL_RULES = [f"R{i}" for i in range(1, 11)]
BUCKET_TARGET_PCT = {"process_full": 0.25, "process_adjusted": 0.20, "reject": 0.30, "escalate": 0.25}
TOLERANCE = 0.05
MIN_PER_RULE_AT_DEFAULT = {"train": 60, "validation": 20, "test": 20}


def _bucket(task) -> str:
    gt = task.ground_truth
    if gt["action"] == "reject_refund":
        return "reject"
    if gt["action"] == "escalate":
        return "escalate"
    rules = gt["rules_involved"]
    return "process_adjusted" if ("R5" in rules or "R6" in rules) else "process_full"


def _is_interaction(task) -> bool:
    substantive = set(task.ground_truth["rules_involved"]) - {"R1", "R9"}
    return len(substantive) >= 2


def _is_r1_only(task) -> bool:
    return task.ground_truth["rules_involved"] == ["R1"]


@pytest.fixture(scope="module")
def default_tasks():
    """Generated once per test module — several tests below all analyze
    the same default-size (n=1400) generation from different angles.
    """
    return generate_tasks(seed=42, n=DEFAULT_N)


def test_same_seed_generates_identical_tasks():
    first = generate_tasks(seed=42, n=300)
    second = generate_tasks(seed=42, n=300)
    assert [dataclasses.asdict(t) for t in first] == [dataclasses.asdict(t) for t in second]


def test_different_seed_generates_different_tasks():
    a = generate_tasks(seed=42, n=300)
    b = generate_tasks(seed=43, n=300)
    assert [dataclasses.asdict(t) for t in a] != [dataclasses.asdict(t) for t in b]


def test_requested_count_is_respected():
    tasks = generate_tasks(seed=1, n=200)
    assert len(tasks) == 200


def test_rejects_n_too_small_for_recipes_to_fit():
    with pytest.raises(ValueError):
        generate_tasks(seed=1, n=100)


def test_smallest_valid_n_still_covers_every_rule_at_least_once():
    # No per-rule *minimum count* is guaranteed below DEFAULT_N (see
    # generator.py's _validate_split_rule_minimums docstring) — only that
    # every rule appears at all.
    tasks = generate_tasks(seed=99, n=150)
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


def test_no_duplicate_request_and_state_across_all_tasks(default_tasks):
    """No task's (request, initial_state) pair may repeat anywhere in the
    generated set — a stronger guarantee than just "not across splits",
    proven here across all three splits together. Holds by construction:
    every task's order_id (embedded in both fields) comes from a single
    globally-incrementing index that's never reset.
    """
    seen = set()
    for task in default_tasks:
        key = (task.request, json.dumps(task.initial_state, sort_keys=True, default=str))
        assert key not in seen, f"duplicate (request, initial_state) for task {task.id}"
        seen.add(key)


# -- Phase 1.1: per-rule minimums at the default size ------------------------


def test_per_rule_minimums_at_default_size(default_tasks):
    by_split: dict[str, dict[str, int]] = {s: dict.fromkeys(ALL_RULES, 0) for s in SPLIT_ORDER}
    for task in default_tasks:
        for rule in task.ground_truth["rules_involved"]:
            by_split[task.split][rule] += 1

    for split, min_required in MIN_PER_RULE_AT_DEFAULT.items():
        short = {r: c for r, c in by_split[split].items() if c < min_required}
        assert not short, f"split={split} below the minimum of {min_required}: {short}"


# -- Phase 1.1: decision-bucket distribution, interaction share, R1-only ----


def test_decision_bucket_distribution_within_tolerance(default_tasks):
    for split in SPLIT_ORDER:
        tasks = [t for t in default_tasks if t.split == split]
        n = len(tasks)
        counts = {b: 0 for b in BUCKET_TARGET_PCT}
        for t in tasks:
            counts[_bucket(t)] += 1
        for bucket, target_pct in BUCKET_TARGET_PCT.items():
            actual_pct = counts[bucket] / n
            assert abs(actual_pct - target_pct) <= TOLERANCE, (
                f"split={split} bucket={bucket}: {actual_pct:.1%} vs target {target_pct:.0%} "
                f"(±{TOLERANCE:.0%})"
            )


def test_interaction_share_is_at_least_40_percent(default_tasks):
    for split in SPLIT_ORDER:
        tasks = [t for t in default_tasks if t.split == split]
        share = sum(1 for t in tasks if _is_interaction(t)) / len(tasks)
        assert share >= 0.40, f"split={split} interaction share {share:.1%} < 40%"


def test_r1_only_share_is_at_most_20_percent(default_tasks):
    for split in SPLIT_ORDER:
        tasks = [t for t in default_tasks if t.split == split]
        share = sum(1 for t in tasks if _is_r1_only(t)) / len(tasks)
        assert share <= 0.20, f"split={split} R1-only share {share:.1%} > 20%"


def test_r1_only_tasks_have_exactly_rules_r1():
    # Sanity check on the classifier helper itself, independent of the
    # generator's actual output.
    tasks = generate_tasks(seed=5, n=300)
    r1_only_tasks = [t for t in tasks if _is_r1_only(t)]
    assert r1_only_tasks
    for t in r1_only_tasks:
        assert t.ground_truth["rules_involved"] == ["R1"]


def test_interaction_tasks_have_at_least_two_non_r1_r9_rules():
    tasks = generate_tasks(seed=5, n=300)
    interaction_tasks = [t for t in tasks if _is_interaction(t)]
    assert interaction_tasks
    for t in interaction_tasks:
        substantive = set(t.ground_truth["rules_involved"]) - {"R1", "R9"}
        assert len(substantive) >= 2


def test_recipes_constant_has_the_expected_size():
    # Guards the "18 recipes x 3 splits" assumption other tests/docs rely on.
    assert len(RECIPES) == 18
