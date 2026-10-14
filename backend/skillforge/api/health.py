"""GET /api/health — liveness plus a real DB round trip.

The response also names the API generation and its feature areas, so a
frontend can tell an out-of-date backend process (e.g. one started before
accounts existed and never restarted) from a genuinely missing feature.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter()

# Bump when a frontend-visible feature area is added or changed incompatibly.
API_VERSION = 4
FEATURES = ["accounts", "curriculum", "teacher", "learner", "study", "profile", "timetable", "review"]


@router.get("/health")
def health(request: Request) -> dict:
    db = request.app.state.db
    db_ok = True
    try:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "api_version": API_VERSION,
        "features": FEATURES,
    }
