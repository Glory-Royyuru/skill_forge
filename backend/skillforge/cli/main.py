"""`python -m skillforge <command>` entry point.

Only the `health` command exists in Phase 0; later phases add subcommands
here (e.g. `train`, `evaluate`) without changing this dispatch shape.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import text

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skillforge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    health_parser = subparsers.add_parser("health", help="Check settings and DB connectivity.")
    health_parser.set_defaults(func=cmd_health)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
