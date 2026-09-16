"""GET /api/health — liveness plus a real DB round trip."""

from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter()


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
    }
