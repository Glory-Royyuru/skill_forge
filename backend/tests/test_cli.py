from __future__ import annotations

from skillforge.cli.main import main


def test_cli_health_command(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cli.db'}")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    exit_code = main(["health"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "status=ok" in captured.out
    assert "database=ok" in captured.out
