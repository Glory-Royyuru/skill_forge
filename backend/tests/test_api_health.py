from __future__ import annotations

from fastapi.testclient import TestClient

from skillforge.api.app import create_app


def test_health_endpoint_ok(tmp_path):
    app = create_app(database_url=f"sqlite:///{tmp_path / 'health.db'}")
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
