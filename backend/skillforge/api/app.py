"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from skillforge.api.health import router as health_router
from skillforge.api.practice import router as practice_router
from skillforge.api.progress import router as progress_router
from skillforge.api.runs import router as runs_router
from skillforge.api.teacher import router as teacher_router
from skillforge.core.settings import get_settings
from skillforge.db.database import Database
from skillforge.teacher.store import seed_demo_history

# Local Vite dev server default ports only — this API has no other
# frontend/deployment target yet.
DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def create_app(database_url: str | None = None, seed_demo: bool | None = None) -> FastAPI:
    settings = get_settings()
    db = Database(database_url or settings.database_url)
    db.init()
    if settings.teacher_seed_demo if seed_demo is None else seed_demo:
        seed_demo_history(db)

    app = FastAPI(title="SkillForge API")
    app.state.db = db
    app.state.settings = settings
    app.state.practice_sessions = {}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api")
    app.include_router(runs_router, prefix="/api")
    app.include_router(practice_router, prefix="/api")
    app.include_router(progress_router, prefix="/api")
    app.include_router(teacher_router, prefix="/api")

    return app


# Default app instance for `uvicorn skillforge.api.app:app`.
app = create_app()
