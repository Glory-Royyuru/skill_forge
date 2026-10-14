"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from skillforge.api.auth import dev_router as dev_auth_router
from skillforge.api.auth import router as auth_router
from skillforge.api.catalog import router as catalog_router
from skillforge.api.health import router as health_router
from skillforge.api.learner import router as learner_router
from skillforge.api.practice import router as practice_router
from skillforge.api.profile import router as profile_router
from skillforge.api.progress import router as progress_router
from skillforge.api.runs import router as runs_router
from skillforge.api.study import router as study_router
from skillforge.api.teacher import router as teacher_router
from skillforge.api.timetable import router as timetable_router
from skillforge.auth.email import EmailSender, build_email_sender
from skillforge.core.settings import get_settings
from skillforge.db.database import Database
from skillforge.teacher.seed import load_curriculum, seed_curriculum

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def create_app(database_url: str | None = None, email_sender: EmailSender | None = None) -> FastAPI:
    settings = get_settings()
    db = Database(database_url or settings.database_url)
    db.init()  # applies pending schema migrations
    seed_curriculum(db)  # idempotent upsert of the VNR curriculum
    load_curriculum(db)  # the Teacher engine reads the curriculum from the database

    app = FastAPI(title="SkillForge API")
    app.state.db = db
    app.state.settings = settings
    app.state.email_sender = email_sender or build_email_sender(settings)
    app.state.practice_sessions = {}

    allowed_origins = settings.cors_origin_list

    @app.middleware("http")
    async def reject_cross_site_writes(request: Request, call_next):
        # Session cookies are SameSite=Lax; additionally refuse state-changing
        # requests whose Origin is neither this server nor an allowed frontend.
        origin = request.headers.get("origin")
        if request.method in UNSAFE_METHODS and origin:
            own = f"{request.url.scheme}://{request.url.netloc}"
            if origin.rstrip("/") not in allowed_origins and origin.rstrip("/") != own:
                return JSONResponse(status_code=403, content={"detail": "Cross-site request refused."})
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )

    app.include_router(health_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(dev_auth_router, prefix="/api")
    app.include_router(catalog_router, prefix="/api")
    app.include_router(teacher_router, prefix="/api")
    app.include_router(timetable_router, prefix="/api")
    app.include_router(learner_router, prefix="/api")
    app.include_router(study_router, prefix="/api")
    app.include_router(profile_router, prefix="/api")
    # Original SkillForge research endpoints (e-commerce environment).
    app.include_router(runs_router, prefix="/api")
    app.include_router(practice_router, prefix="/api")
    app.include_router(progress_router, prefix="/api")

    return app


# Default app instance for `uvicorn skillforge.api.app:app`.
app = create_app()
