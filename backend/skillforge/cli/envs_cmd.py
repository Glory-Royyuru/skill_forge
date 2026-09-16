"""`python -m skillforge envs ...` subcommands: generate, stats, run-agent."""

from __future__ import annotations

import argparse
import sys
from collections import Counter

from sqlalchemy import select

from skillforge.core.settings import get_settings
from skillforge.db.database import Database
from skillforge.db.models import Environment as DBEnvironment
from skillforge.envs.agents import RandomAgent, run_episode
from skillforge.envs.ecommerce.environment import EcommerceRefundEnvironment
from skillforge.envs.ecommerce.generator import DEFAULT_N, generate_tasks
from skillforge.envs.ecommerce.oracle import OracleAgent
from skillforge.envs.ecommerce.persistence import (
    count_by_split_and_rule,
    count_tasks_by_split,
    get_or_create_environment,
    load_tasks,
    save_tasks,
)

ALL_RULES = [f"R{i}" for i in range(1, 11)]
SPLITS = ["train", "validation", "test"]


def cmd_envs_generate(args: argparse.Namespace) -> int:
    if args.env != "ecommerce":
        print(f"unknown environment: {args.env}", file=sys.stderr)
        return 1

    settings = get_settings()
    db = Database(settings.database_url)
    db.init()

    tasks = generate_tasks(seed=args.seed, n=args.n)
    with db.session() as session:
        env_row = get_or_create_environment(session)
        environment_id = env_row.id
        count = save_tasks(session, environment_id, args.seed, tasks)

    by_split = Counter(t.split for t in tasks)
    print(f"generated {count} tasks for env={args.env} seed={args.seed} (environment_id={environment_id})")
    print("  " + ", ".join(f"{split}={by_split.get(split, 0)}" for split in SPLITS))
    return 0


def cmd_envs_stats(args: argparse.Namespace) -> int:
    del args
    settings = get_settings()
    db = Database(settings.database_url)
    db.init()

    with db.session() as session:
        env_row = session.scalar(
            select(DBEnvironment).where(DBEnvironment.name == EcommerceRefundEnvironment.name)
        )
        if env_row is None:
            print("no ecommerce_refunds tasks found; run `envs generate` first.", file=sys.stderr)
            return 1
        totals = count_tasks_by_split(session, env_row.id)
        rule_counts = count_by_split_and_rule(session, env_row.id)

    header = "split".ljust(12) + "total".rjust(7) + "".join(r.rjust(6) for r in ALL_RULES)
    print(header)
    missing: list[tuple[str, str]] = []
    for split in SPLITS:
        total = totals.get(split, 0)
        counts = rule_counts.get(split, {})
        row = split.ljust(12) + str(total).rjust(7)
        for rule in ALL_RULES:
            c = counts.get(rule, 0)
            row += str(c).rjust(6)
            if total > 0 and c == 0:
                missing.append((split, rule))
        print(row)

    if missing:
        print("MISSING rule coverage: " + ", ".join(f"{split}/{rule}" for split, rule in missing))
        return 1
    return 0


def cmd_envs_run_agent(args: argparse.Namespace) -> int:
    if args.env != "ecommerce":
        print(f"unknown environment: {args.env}", file=sys.stderr)
        return 1
    if args.agent not in ("oracle", "random"):
        print(f"unknown agent: {args.agent}", file=sys.stderr)
        return 1

    settings = get_settings()
    db = Database(settings.database_url)
    db.init()

    with db.session() as session:
        env_row = session.scalar(
            select(DBEnvironment).where(DBEnvironment.name == EcommerceRefundEnvironment.name)
        )
        if env_row is None:
            print("no ecommerce_refunds tasks found; run `envs generate` first.", file=sys.stderr)
            return 1
        tasks = load_tasks(session, env_row.id, split=args.split, limit=args.n)

    if not tasks:
        print(f"no tasks found for split={args.split}", file=sys.stderr)
        return 1

    random_agent = RandomAgent(seed=args.agent_seed) if args.agent == "random" else None

    successes = 0
    criticals = 0
    total_score = 0.0
    error_counter: Counter[str] = Counter()

    for task in tasks:
        env = EcommerceRefundEnvironment()
        agent = OracleAgent(task) if args.agent == "oracle" else random_agent
        result, _trajectory = run_episode(env, task, agent)
        if result.success:
            successes += 1
        if result.critical:
            criticals += 1
        total_score += result.score
        if result.error_type:
            error_counter[result.error_type] += 1

    n = len(tasks)
    print(f"agent={args.agent} split={args.split} n={n}")
    print(f"  success_rate={successes / n:.3f} ({successes}/{n})")
    print(f"  mean_score={total_score / n:.3f}")
    print(f"  critical_rate={criticals / n:.3f} ({criticals}/{n})")
    if error_counter:
        breakdown = ", ".join(f"{k}={v}" for k, v in sorted(error_counter.items()))
        print(f"  error_types: {breakdown}")
    return 0


def add_envs_subcommands(subparsers: argparse._SubParsersAction) -> None:
    envs_parser = subparsers.add_parser("envs", help="Environment task generation, stats, and agent runs.")
    envs_sub = envs_parser.add_subparsers(dest="envs_command", required=True)

    generate_parser = envs_sub.add_parser("generate", help="Generate and persist tasks for an environment.")
    generate_parser.add_argument("--env", default="ecommerce")
    generate_parser.add_argument("--seed", type=int, required=True)
    generate_parser.add_argument("--n", type=int, default=DEFAULT_N)
    generate_parser.set_defaults(func=cmd_envs_generate)

    stats_parser = envs_sub.add_parser("stats", help="Report task counts and rule coverage per split.")
    stats_parser.set_defaults(func=cmd_envs_stats)

    run_agent_parser = envs_sub.add_parser("run-agent", help="Run an agent over a split and report scores.")
    run_agent_parser.add_argument("--env", default="ecommerce")
    run_agent_parser.add_argument("--agent", required=True, choices=["oracle", "random"])
    run_agent_parser.add_argument("--split", default="validation", choices=SPLITS)
    run_agent_parser.add_argument("--n", type=int, default=50)
    run_agent_parser.add_argument("--agent-seed", type=int, default=0)
    run_agent_parser.set_defaults(func=cmd_envs_run_agent)
