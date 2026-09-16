from __future__ import annotations

from skillforge.cli.main import main
from skillforge.core.settings import get_settings
from skillforge.db.database import Database
from skillforge.envs.ecommerce.persistence import count_tasks_by_split, get_or_create_environment


def _fresh_db_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cli_envs.db'}")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_envs_generate_then_stats(tmp_path, monkeypatch, capsys):
    # Uses the default n (1400): the Phase 1.1 targets (decision
    # distribution, interaction share, R1-only cap, per-rule minimums) are
    # only guaranteed at that size — see generator.py's module docstring.
    _fresh_db_env(tmp_path, monkeypatch)

    exit_code = main(["envs", "generate", "--env", "ecommerce", "--seed", "42"])
    assert exit_code == 0
    generate_out = capsys.readouterr().out
    assert "generated 1400 tasks" in generate_out

    exit_code = main(["envs", "stats"])
    stats_out = capsys.readouterr().out
    assert exit_code == 0, stats_out
    assert "FAILED" not in stats_out
    for i in range(1, 11):
        assert f"R{i}" in stats_out


def test_envs_generate_is_idempotent_per_seed(tmp_path, monkeypatch, capsys):
    _fresh_db_env(tmp_path, monkeypatch)

    main(["envs", "generate", "--env", "ecommerce", "--seed", "42"])
    capsys.readouterr()
    main(["envs", "generate", "--env", "ecommerce", "--seed", "42"])
    capsys.readouterr()

    # total across all three splits should still be exactly 1400, not 2800
    db = Database(get_settings().database_url)
    with db.session() as session:
        env_row = get_or_create_environment(session)
        counts = count_tasks_by_split(session, env_row.id)
    assert sum(counts.values()) == 1400


def test_envs_run_agent_oracle_is_perfect(tmp_path, monkeypatch, capsys):
    _fresh_db_env(tmp_path, monkeypatch)
    main(["envs", "generate", "--env", "ecommerce", "--seed", "42", "--n", "300"])
    capsys.readouterr()

    exit_code = main(["envs", "run-agent", "--agent", "oracle", "--split", "validation", "--n", "50"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "success_rate=1.000" in out


def test_envs_run_agent_random_is_low(tmp_path, monkeypatch, capsys):
    _fresh_db_env(tmp_path, monkeypatch)
    main(["envs", "generate", "--env", "ecommerce", "--seed", "42", "--n", "300"])
    capsys.readouterr()

    exit_code = main(["envs", "run-agent", "--agent", "random", "--split", "validation", "--n", "50"])
    assert exit_code == 0
    out = capsys.readouterr().out
    line = next(line for line in out.splitlines() if "success_rate" in line)
    rate = float(line.split("success_rate=")[1].split(" ")[0])
    assert rate < 0.2


def test_envs_stats_without_data_errors_cleanly(tmp_path, monkeypatch, capsys):
    _fresh_db_env(tmp_path, monkeypatch)
    exit_code = main(["envs", "stats"])
    assert exit_code == 1
