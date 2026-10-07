"""`python -m skillforge run` / `show-attempt`, and the shared `run_condition`
function the API's `/api/run` endpoint also calls — one implementation,
two front ends.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict
from typing import Any

from sqlalchemy import select

from skillforge.agents.learner import run_learner
from skillforge.agents.prompts import prompt_for_condition
from skillforge.core.settings import get_settings
from skillforge.db.database import Database
from skillforge.db.helpers import (
    create_training_session,
    db_task_id,
    get_attempt,
    get_or_create_agent,
    get_or_create_skill,
    save_attempt,
)
from skillforge.db.models import Attempt, TrainingSession
from skillforge.db.models import Environment as DBEnvironment
from skillforge.envs.ecommerce.environment import EcommerceRefundEnvironment
from skillforge.envs.ecommerce.persistence import load_tasks
from skillforge.llm.anthropic_provider import AnthropicProvider
from skillforge.llm.cache import ResponseCache
from skillforge.llm.client import LoggingLLMClient
from skillforge.llm.mock import MockProvider
from skillforge.llm.openai_provider import OpenAIProvider

ALL_RULES = [f"R{i}" for i in range(1, 11)]


class RunError(Exception):
    """No tasks / bad config — caller (CLI or API) decides how to surface it."""


def _is_interaction(rules_involved: list[str]) -> bool:
    return len(set(rules_involved) - {"R1", "R9"}) >= 2


def build_provider(provider_name: str, model: str, dry_run: bool, script: list | None = None):
    if dry_run:
        return MockProvider(script=script or [], model="mock-learner")
    settings = get_settings()
    if provider_name == "anthropic":
        if not settings.anthropic_api_key:
            raise RunError("ANTHROPIC_API_KEY is not set; use dry_run or set the key in backend/.env")
        return AnthropicProvider(api_key=settings.anthropic_api_key, default_model=model)
    if provider_name == "openai":
        if not settings.openai_api_key:
            raise RunError("OPENAI_API_KEY is not set; use dry_run or set the key in backend/.env")
        return OpenAIProvider(api_key=settings.openai_api_key, default_model=model)
    raise RunError(f"unknown provider: {provider_name}")


def _dry_run_script(tasks) -> list:
    """One immediate (terminal, order-correct) tool call per task, so a
    dry run exercises the full pipeline with zero network calls.
    """
    return [
        {
            "tool_calls": [
                {
                    "name": "escalate",
                    "arguments": {"order_id": t.initial_state["order"]["order_id"], "reason_code": "dry_run"},
                }
            ]
        }
        for t in tasks
    ]


def run_condition(
    db: Database,
    condition: str,
    split: str = "validation",
    n: int = 50,
    seed: int = 1,
    provider: str | None = None,
    model: str | None = None,
    max_cost: float | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Runs the Learner over `n` tasks of `split` under `condition`,
    persists attempts, and returns a JSON-safe summary dict. Raises
    RunError for config problems (no tasks, missing API key, ...).
    """
    settings = get_settings()
    provider_name = provider or ("mock" if dry_run else settings.learner_provider)
    model_name = model or settings.learner_model

    with db.session() as session:
        env_row = session.scalar(
            select(DBEnvironment).where(DBEnvironment.name == EcommerceRefundEnvironment.name)
        )
        if env_row is None:
            raise RunError("no ecommerce_refunds tasks found; run `envs generate` first.")
        tasks = load_tasks(session, env_row.id, split=split, limit=n)
        if not tasks:
            raise RunError(f"no tasks found for split={split}")

        skill = get_or_create_skill(session, env_row.id, name=f"ecommerce_condition_{condition}")
        agent_name = f"learner-{provider_name}-{model_name}"
        agent_row = get_or_create_agent(session, name=agent_name, provider=provider_name, model=model_name)
        training_session = create_training_session(
            session,
            skill.id,
            agent_row.id,
            condition=condition,
            config={"split": split, "n": n, "seed": seed, "dry_run": dry_run},
        )
        session_id = training_session.id

    llm_provider = build_provider(
        provider_name, model_name, dry_run, script=_dry_run_script(tasks) if dry_run else None
    )
    system_prompt = prompt_for_condition(condition)
    cache = ResponseCache() if settings.llm_cache_enabled else None

    per_task_cost_budget = (max_cost / len(tasks)) if max_cost else None
    rows = []
    total_cost = 0.0
    budget_stopped = False

    for task in tasks:
        if max_cost is not None and total_cost >= max_cost:
            budget_stopped = True
            break
        env = EcommerceRefundEnvironment()
        with db.session() as session:
            client = LoggingLLMClient(
                llm_provider, session, role="learner", session_id=session_id, cache=cache
            )
            run = run_learner(
                env,
                task,
                client,
                system_prompt,
                model=model_name,
                seed=seed,
                cost_budget=per_task_cost_budget,
            )
            evaluation = env.evaluate()
            trajectory = {
                "messages": run.messages,
                "trajectory": run.trajectory,
                "stop_reason": run.stop_reason,
                "steps_taken": run.steps_taken,
            }
            attempt = save_attempt(
                session,
                session_id,
                db_task_id(task.id),
                trajectory=trajectory,
                result=asdict(evaluation),
                tokens=run.input_tokens + run.output_tokens,
                cost=run.cost,
            )
        total_cost += run.cost
        rows.append((evaluation, run, attempt.id))

    with db.session() as session:
        ts = session.get(TrainingSession, session_id)
        ts.status = "budget_exhausted" if budget_stopped else "completed"
        session.commit()

    return build_summary(condition, split, session_id, rows, budget_stopped)


def build_summary(condition: str, split: str, session_id: int, rows, budget_stopped: bool) -> dict[str, Any]:
    n = len(rows)
    summary: dict[str, Any] = {
        "condition": condition,
        "split": split,
        "session_id": session_id,
        "n": n,
        "budget_stopped": budget_stopped,
        "last_attempt_id": rows[-1][2] if rows else None,
    }
    if n == 0:
        return summary

    def _rate(pairs):
        return (sum(1 for e, _, _ in pairs if e.success) / len(pairs)) if pairs else None

    interaction_rows = [row for row in rows if _is_interaction(row[0].rules_involved)]
    non_interaction_rows = [row for row in rows if not _is_interaction(row[0].rules_involved)]

    summary.update(
        {
            "success_rate": sum(1 for e, _, _ in rows if e.success) / n,
            "mean_score": sum(e.score for e, _, _ in rows) / n,
            "critical_rate": sum(1 for e, _, _ in rows if e.critical) / n,
            "error_types": dict(Counter(e.error_type for e, _, _ in rows if e.error_type)),
            "avg_steps": sum(r.steps_taken for _, r, _ in rows) / n,
            "tokens": sum(r.input_tokens + r.output_tokens for _, r, _ in rows),
            "cost": sum(r.cost for _, r, _ in rows),
            "per_rule_success": {
                rule: _rate([row for row in rows if rule in row[0].rules_involved])
                for rule in ALL_RULES
                if any(rule in row[0].rules_involved for row in rows)
            },
            "interaction_success": _rate(interaction_rows),
            "non_interaction_success": _rate(non_interaction_rows),
        }
    )
    return summary


def summary_from_db(db: Database, session_id: int) -> dict[str, Any] | None:
    """Rebuild a run summary from persisted Attempt rows — used by
    `GET /api/runs/{session_id}` so results survive past the request that
    started the run.
    """
    with db.session() as session:
        ts = session.get(TrainingSession, session_id)
        if ts is None:
            return None
        attempts = session.scalars(select(Attempt).where(Attempt.session_id == session_id)).all()

    class _Row:
        __slots__ = ("success", "score", "critical", "error_type", "rules_involved")

        def __init__(self, result: dict):
            self.success = result["success"]
            self.score = result["score"]
            self.critical = result["critical"]
            self.error_type = result["error_type"]
            self.rules_involved = result["rules_involved"]

    class _Run:
        __slots__ = ("steps_taken", "input_tokens", "output_tokens", "cost")

        def __init__(self, tokens: int, cost: float, steps: int):
            self.steps_taken = steps
            self.input_tokens = tokens
            self.output_tokens = 0
            self.cost = cost

    rows = []
    for a in attempts:
        steps = (a.trajectory_json or {}).get("steps_taken", 0)
        rows.append((_Row(a.result_json), _Run(a.tokens or 0, a.cost or 0.0, steps), a.id))
    budget_stopped = ts.status == "budget_exhausted"
    split = (ts.config_json or {}).get("split", "")
    return build_summary(ts.condition, split, session_id, rows, budget_stopped)


def print_summary(summary: dict[str, Any]) -> None:
    print(
        f"condition={summary['condition']} split={summary['split']} "
        f"n={summary['n']} session_id={summary['session_id']}"
    )
    if summary["n"] == 0:
        print("  no attempts completed")
        return
    if summary["budget_stopped"]:
        print("  WARNING: stopped early - cost budget exhausted")
    print(f"  success_rate={summary['success_rate']:.3f}")
    print(f"  mean_score={summary['mean_score']:.3f}")
    print(f"  critical_rate={summary['critical_rate']:.3f}")
    if summary["error_types"]:
        print("  error_types: " + ", ".join(f"{k}={v}" for k, v in sorted(summary["error_types"].items())))
    print(f"  avg_steps={summary['avg_steps']:.2f}")
    print(f"  tokens={summary['tokens']}  cost=${summary['cost']:.4f}")
    print("  per_rule_success:")
    for rule, rate in summary["per_rule_success"].items():
        print(f"    {rule}: {rate:.3f}")
    ir = summary["interaction_success"]
    nr = summary["non_interaction_success"]
    print(f"  interaction_success={ir:.3f}" if ir is not None else "  interaction_success=n/a")
    print(f"  non_interaction_success={nr:.3f}" if nr is not None else "  non_interaction_success=n/a")


def cmd_run(args: argparse.Namespace) -> int:
    settings = get_settings()
    db = Database(settings.database_url)
    db.init()
    try:
        summary = run_condition(
            db,
            args.condition,
            split=args.split,
            n=args.n,
            seed=args.seed,
            provider=args.provider,
            model=args.model,
            max_cost=args.max_cost,
            dry_run=args.dry_run,
        )
    except RunError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print_summary(summary)
    return 0


def cmd_show_attempt(args: argparse.Namespace) -> int:
    settings = get_settings()
    db = Database(settings.database_url)
    db.init()
    with db.session() as session:
        attempt = get_attempt(session, args.id)
        if attempt is None:
            print(f"no attempt with id={args.id}", file=sys.stderr)
            return 1
        print(f"attempt id={attempt.id} session_id={attempt.session_id} task_id={attempt.task_id}")
        print(f"tokens={attempt.tokens} cost=${attempt.cost:.4f}")
        print("result:")
        print(json.dumps(attempt.result_json, indent=2))
        print("trajectory:")
        print(json.dumps(attempt.trajectory_json, indent=2))
    return 0


def add_run_subcommands(subparsers: argparse._SubParsersAction) -> None:
    run_parser = subparsers.add_parser("run", help="Run the Learner agent over a split/condition.")
    run_parser.add_argument("--condition", required=True, choices=["A", "B"])
    run_parser.add_argument("--split", default="validation", choices=["train", "validation", "test"])
    run_parser.add_argument("--n", type=int, default=50)
    run_parser.add_argument("--seed", type=int, default=1)
    run_parser.add_argument("--provider", default=None, choices=["anthropic", "openai"])
    run_parser.add_argument("--model", default=None)
    run_parser.add_argument("--max-cost", type=float, default=None, dest="max_cost")
    run_parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    run_parser.set_defaults(func=cmd_run)

    show_parser = subparsers.add_parser("show-attempt", help="Print a saved attempt's trajectory/result.")
    show_parser.add_argument("--id", type=int, required=True)
    show_parser.set_defaults(func=cmd_show_attempt)
