"""OracleAgent must score 100% on generated tasks (the Phase 1 gate).
RandomAgent is a low-bar sanity check — it should score far below that.
"""

from __future__ import annotations

from skillforge.envs.agents import RandomAgent, run_episode
from skillforge.envs.ecommerce.environment import EcommerceRefundEnvironment
from skillforge.envs.ecommerce.generator import generate_tasks
from skillforge.envs.ecommerce.oracle import OracleAgent


def test_oracle_scores_100_percent_on_200_tasks():
    tasks = generate_tasks(seed=42, n=200)
    failures = []
    for task in tasks:
        env = EcommerceRefundEnvironment()
        agent = OracleAgent(task)
        result, _trajectory = run_episode(env, task, agent)
        if not result.success:
            failures.append((task.id, result))

    assert not failures, f"oracle failed on {len(failures)}/{len(tasks)} tasks: {failures[:5]}"


def test_oracle_never_produces_a_critical_error():
    tasks = generate_tasks(seed=11, n=150)
    for task in tasks:
        env = EcommerceRefundEnvironment()
        agent = OracleAgent(task)
        result, _trajectory = run_episode(env, task, agent)
        assert result.critical is False


def test_random_agent_scores_far_below_oracle():
    tasks = generate_tasks(seed=42, n=200)

    total_score = 0.0
    successes = 0
    agent = RandomAgent(seed=0)
    for task in tasks:
        env = EcommerceRefundEnvironment()
        result, _trajectory = run_episode(env, task, agent)
        total_score += result.score
        if result.success:
            successes += 1

    mean_score = total_score / len(tasks)
    # Not a tight bound — just proving it is nowhere near oracle's 1.0.
    assert mean_score < 0.2
    assert successes < len(tasks) * 0.1


def test_random_agent_never_produces_a_critical_error_by_accident_at_this_seed():
    # RandomAgent can never target the right order id at all (see
    # environment's order_id_mismatch guard), so it should not be able to
    # accidentally issue money. This locks in that structural guarantee.
    tasks = generate_tasks(seed=42, n=200)
    agent = RandomAgent(seed=0)
    for task in tasks:
        env = EcommerceRefundEnvironment()
        result, _trajectory = run_episode(env, task, agent)
        assert result.critical is False
