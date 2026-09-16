from __future__ import annotations

from skillforge.core.settings import Settings


def test_settings_load_without_api_keys(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    # _env_file=None so a stray local .env can't leak into this assertion.
    settings = Settings(_env_file=None)

    assert settings.openai_api_key is None
    assert settings.anthropic_api_key is None
    assert settings.database_url
    assert settings.teacher_provider == "mock"
    assert settings.learner_provider == "mock"
    assert settings.session_token_budget > 0
    assert settings.session_cost_budget_usd > 0
    assert settings.llm_cache_enabled is True


def test_settings_read_env_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'custom.db'}")
    monkeypatch.setenv("SESSION_TOKEN_BUDGET", "12345")

    settings = Settings(_env_file=None)

    assert settings.database_url.endswith("custom.db")
    assert settings.session_token_budget == 12345
