"""Application settings, loaded from the environment (and an optional .env
file) via pydantic-settings.

No field here has a secret default. Provider API keys default to ``None``
so the whole test suite can run with zero environment configuration by
relying on ``MockProvider`` instead of a real LLM.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database -----------------------------------------------------
    database_url: str = Field(
        default="sqlite:///./skillforge.db",
        description="SQLAlchemy database URL.",
    )

    # --- Provider credentials (optional; tests never need these) ------
    openai_api_key: str | None = Field(default=None)
    anthropic_api_key: str | None = Field(default=None)

    # --- Default agent providers/models --------------------------------
    # "mock" is the default so the app is runnable out of the box with no
    # API keys configured.
    teacher_provider: str = Field(default="mock")
    teacher_model: str = Field(default="mock-teacher")
    learner_provider: str = Field(default="mock")
    learner_model: str = Field(default="mock-learner")

    # --- Per-session budgets --------------------------------------------
    session_token_budget: int = Field(default=200_000)
    session_cost_budget_usd: float = Field(default=5.0)

    # --- LLM response cache ---------------------------------------------
    llm_cache_enabled: bool = Field(default=True)

    # --- Teacher Agent ----------------------------------------------------
    # Offline learner model used as a supporting signal by the Teacher:
    # "bkt" (Bayesian Knowledge Tracing) or "none" to disable it.
    teacher_learner_model: str = Field(default="bkt")

    # --- Application / web ------------------------------------------------
    # "development" enables developer conveniences (see dev_email_outbox);
    # use "production" for any deployment.
    app_env: str = Field(default="development")
    # Base URL of the frontend; used to build links in emails.
    frontend_base_url: str = Field(default="http://localhost:5173")
    # Browser origins allowed to call the API with credentials (comma-separated).
    cors_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173")

    # --- Authentication -----------------------------------------------------
    session_cookie_name: str = Field(default="sf_session")
    session_ttl_hours: int = Field(default=24 * 7)
    # Set true whenever the site is served over HTTPS.
    session_cookie_secure: bool = Field(default=False)
    verification_token_ttl_hours: int = Field(default=24)
    reset_token_ttl_minutes: int = Field(default=60)

    # --- Email --------------------------------------------------------------
    # "console": do not send; write the message (with its link) to the server
    # log. "smtp": deliver through the SMTP server below.
    email_backend: str = Field(default="console")
    smtp_host: str | None = Field(default=None)
    smtp_port: int = Field(default=587)
    smtp_username: str | None = Field(default=None)
    smtp_password: str | None = Field(default=None)
    smtp_from: str = Field(default="SkillForge <no-reply@localhost>")
    smtp_starttls: bool = Field(default=True)
    smtp_ssl: bool = Field(default=False)
    smtp_timeout_seconds: int = Field(default=10)
    # Development only: expose unsent console-backend emails at
    # GET /api/dev/outbox (localhost requests only). Ignored unless
    # app_env == "development" and email_backend == "console".
    dev_email_outbox: bool = Field(default=True)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    @property
    def dev_outbox_enabled(self) -> bool:
        return self.dev_email_outbox and self.app_env == "development" and self.email_backend == "console"


def get_settings() -> Settings:
    """Return a freshly-loaded Settings instance.

    Deliberately uncached: settings are cheap to construct and tests
    frequently need to change environment variables between calls (e.g.
    via monkeypatch). Add caching back later if profiling shows it matters.
    """
    return Settings()
