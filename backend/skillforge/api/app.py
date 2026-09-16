"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from skillforge.api.health import router as health_router
from skillforge.core.settings import get_settings
from skillforge.db.database import Database


def create_app(database_url: str | None = None) -> FastAPI:
    settings = get_settings()
    db = Database(database_url or settings.database_url)
    db.init()

    app = FastAPI(title="SkillForge API")
    app.state.db = db

    app.include_router(health_router, prefix="/api")

    return app


# Default app instance for `uvicorn skillforge.api.app:app`.
app = create_app()
