"""`python -m skillforge <command>` entry point.

Commands: `health`, `db upgrade`, `curriculum seed`, plus the research
`envs` and `run` groups.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import text

from skillforge.cli.envs_cmd import add_envs_subcommands
from skillforge.cli.run_cmd import add_run_subcommands
from skillforge.core.settings import get_settings
from skillforge.db.database import Database


def cmd_health(_args: argparse.Namespace) -> int:
    settings = get_settings()
    db = Database(settings.database_url)
    db.init()

    db_ok = True
    try:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - defensive
        db_ok = False
        print(f"database error: {exc}", file=sys.stderr)

    status = "ok" if db_ok else "degraded"
    print(
        f"status={status} database={'ok' if db_ok else 'error'} "
        f"database_url={settings.database_url}"
    )
    return 0 if db_ok else 1


def cmd_db_upgrade(_args: argparse.Namespace) -> int:
    from skillforge.db.migrations import current_version, upgrade

    db = Database(get_settings().database_url)
    applied = upgrade(db.engine)
    print(f"applied={applied or 'none'} schema_version={current_version(db.engine)}")
    return 0


def cmd_curriculum_seed(_args: argparse.Namespace) -> int:
    from skillforge.teacher.seed import seed_curriculum

    db = Database(get_settings().database_url)
    db.init()
    counts = seed_curriculum(db)
    print(" ".join(f"{k}={v}" for k, v in counts.items()))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skillforge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    health_parser = subparsers.add_parser("health", help="Check settings and DB connectivity.")
    health_parser.set_defaults(func=cmd_health)

    db_parser = subparsers.add_parser("db", help="Database schema management.")
    db_sub = db_parser.add_subparsers(dest="db_command", required=True)
    db_sub.add_parser("upgrade", help="Apply pending schema migrations.").set_defaults(func=cmd_db_upgrade)

    cur_parser = subparsers.add_parser("curriculum", help="Curriculum content.")
    cur_sub = cur_parser.add_subparsers(dest="curriculum_command", required=True)
    cur_sub.add_parser("seed", help="Upsert the VNR curriculum into the database.").set_defaults(
        func=cmd_curriculum_seed
    )

    add_envs_subcommands(subparsers)
    add_run_subcommands(subparsers)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
