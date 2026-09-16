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


def test_random_agent_produces_mostly_wrong_order_errors():
    # Phase 1.1: a terminal action on the wrong order now executes and
    # ends the episode (see environment.py), rather than being refused and
    # retried. RandomAgent essentially never guesses the real order id, so
    # its first successful terminal call — which is likely within a few
    # of its 15 steps, since 3 of the 8 tools are terminal — ends the
    # episode as `wrong_order`. This replaces the old (Phase 1) assumption
    # that RandomAgent could never be critical: a wrong-order
    # process_refund now legitimately *is* critical (money issued against
    # the wrong order).
    tasks = generate_tasks(seed=42, n=200)
    agent = RandomAgent(seed=0)
    error_types: dict[str, int] = {}
    for task in tasks:
        env = EcommerceRefundEnvironment()
        result, _trajectory = run_episode(env, task, agent)
        if result.error_type:
            error_types[result.error_type] = error_types.get(result.error_type, 0) + 1

    assert error_types.get("wrong_order", 0) > 0
