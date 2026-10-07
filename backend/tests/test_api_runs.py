from __future__ import annotations

from fastapi.testclient import TestClient

from skillforge.api.app import create_app
from skillforge.envs.ecommerce.generator import generate_tasks
from skillforge.envs.ecommerce.persistence import get_or_create_environment, save_tasks


def _seeded_app(tmp_path):
    app = create_app(database_url=f"sqlite:///{tmp_path / 'api.db'}")
    with app.state.db.session() as s:
        env = get_or_create_environment(s)
        save_tasks(s, env.id, seed=1, tasks=generate_tasks(seed=1, n=200))
    return app


def test_policy_endpoint(tmp_path):
    client = TestClient(_seeded_app(tmp_path))
    r = client.get("/api/policy")
    assert r.status_code == 200
    assert "30" in r.json()["text"]


def test_run_dry_run_endpoint_forces_dry_run_without_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = TestClient(_seeded_app(tmp_path))
    r = client.post("/api/run", json={"condition": "A", "split": "validation", "n": 2, "dry_run": False})
    assert r.status_code == 200
    body = r.json()
    assert body["n"] == 2
    assert "success_rate" in body


def test_get_run_after_run(tmp_path):
    client = TestClient(_seeded_app(tmp_path))
    r = client.post("/api/run", json={"condition": "B", "split": "validation", "n": 2, "dry_run": True})
    session_id = r.json()["session_id"]
    r2 = client.get(f"/api/runs/{session_id}")
    assert r2.status_code == 200
    assert r2.json()["condition"] == "B"


def test_get_run_missing_404(tmp_path):
    client = TestClient(_seeded_app(tmp_path))
    assert client.get("/api/runs/9999").status_code == 404


def test_get_attempt(tmp_path):
    client = TestClient(_seeded_app(tmp_path))
    r = client.post("/api/run", json={"condition": "A", "n": 1, "dry_run": True})
    attempt_id = r.json()["last_attempt_id"]
    r2 = client.get(f"/api/attempts/{attempt_id}")
    assert r2.status_code == 200
    assert "trajectory" in r2.json()


def test_run_no_tasks_returns_400(tmp_path):
    app = create_app(database_url=f"sqlite:///{tmp_path / 'empty.db'}")
    client = TestClient(app)
    r = client.post("/api/run", json={"condition": "A", "n": 1, "dry_run": True})
    assert r.status_code == 400
