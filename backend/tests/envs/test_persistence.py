from __future__ import annotations

from skillforge.envs.ecommerce.generator import generate_tasks
from skillforge.envs.ecommerce.persistence import (
    count_by_split_and_rule,
    count_tasks_by_split,
    get_or_create_environment,
    load_tasks,
    save_tasks,
)


def test_get_or_create_environment_is_idempotent(db):
    with db.session() as session:
        first = get_or_create_environment(session)
        second = get_or_create_environment(session)
        assert first.id == second.id


def test_save_and_load_round_trip(db):
    tasks = generate_tasks(seed=42, n=200)
    with db.session() as session:
        env_row = get_or_create_environment(session)
        count = save_tasks(session, env_row.id, seed=42, tasks=tasks)
        assert count == len(tasks)

        loaded = load_tasks(session, env_row.id)
        assert len(loaded) == len(tasks)
        assert {t.split for t in loaded} == {"train", "validation", "test"}


def test_save_tasks_is_idempotent_per_seed(db):
    tasks = generate_tasks(seed=42, n=200)
    with db.session() as session:
        env_row = get_or_create_environment(session)
        save_tasks(session, env_row.id, seed=42, tasks=tasks)
        save_tasks(session, env_row.id, seed=42, tasks=tasks)  # regenerate same seed

        loaded = load_tasks(session, env_row.id)
        assert len(loaded) == len(tasks)  # not doubled


def test_load_tasks_filters_by_split(db):
    tasks = generate_tasks(seed=42, n=200)
    with db.session() as session:
        env_row = get_or_create_environment(session)
        save_tasks(session, env_row.id, seed=42, tasks=tasks)

        train_only = load_tasks(session, env_row.id, split="train")
        assert train_only
        assert all(t.split == "train" for t in train_only)


def test_count_tasks_by_split(db):
    tasks = generate_tasks(seed=42, n=200)
    with db.session() as session:
        env_row = get_or_create_environment(session)
        save_tasks(session, env_row.id, seed=42, tasks=tasks)

        counts = count_tasks_by_split(session, env_row.id)
        assert sum(counts.values()) == 200
        assert set(counts) == {"train", "validation", "test"}


def test_count_by_split_and_rule_covers_every_rule(db):
    tasks = generate_tasks(seed=42, n=300)
    with db.session() as session:
        env_row = get_or_create_environment(session)
        save_tasks(session, env_row.id, seed=42, tasks=tasks)

        counts = count_by_split_and_rule(session, env_row.id)
        for split in ("train", "validation", "test"):
            for i in range(1, 11):
                assert counts[split].get(f"R{i}", 0) > 0, f"missing R{i} in {split}"
