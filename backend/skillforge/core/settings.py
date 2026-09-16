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


def get_settings() -> Settings:
    """Return a freshly-loaded Settings instance.

    Deliberately uncached: settings are cheap to construct and tests
    frequently need to change environment variables between calls (e.g.
    via monkeypatch). Add caching back later if profiling shows it matters.
    """
    return Settings()
