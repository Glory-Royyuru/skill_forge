from __future__ import annotations

from skillforge.cli.main import main


def _fresh_db_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cli_envs.db'}")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_envs_generate_then_stats(tmp_path, monkeypatch, capsys):
    _fresh_db_env(tmp_path, monkeypatch)

    exit_code = main(["envs", "generate", "--env", "ecommerce", "--seed", "42", "--n", "300"])
    assert exit_code == 0
    generate_out = capsys.readouterr().out
    assert "generated 300 tasks" in generate_out

    exit_code = main(["envs", "stats"])
    assert exit_code == 0
    stats_out = capsys.readouterr().out
    assert "MISSING" not in stats_out
    for i in range(1, 11):
        assert f"R{i}" in stats_out


def test_envs_generate_is_idempotent_per_seed(tmp_path, monkeypatch, capsys):
    _fresh_db_env(tmp_path, monkeypatch)

    main(["envs", "generate", "--env", "ecommerce", "--seed", "42", "--n", "300"])
    capsys.readouterr()
    main(["envs", "generate", "--env", "ecommerce", "--seed", "42", "--n", "300"])
    capsys.readouterr()

    main(["envs", "stats"])
    stats_out = capsys.readouterr().out
    # total across all three splits should still be exactly 300, not 600
    split_names = ("train", "validation", "test")
    lines = [line for line in stats_out.splitlines() if line.split() and line.split()[0] in split_names]
    total = sum(int(line.split()[1]) for line in lines)
    assert total == 300


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
