from __future__ import annotations

import re

from fastapi.testclient import TestClient

from skillforge.api.app import create_app


def _app(tmp_path):
    return create_app(database_url=f"sqlite:///{tmp_path / 'practice.db'}")


def _start_and_get_order_id(client, mode="practice"):
    r = client.post("/api/practice/start", json={"mode": mode})
    assert r.status_code == 200
    data = r.json()
    m = re.search(r"order (ORD-\S+)\)", data["request"])
    return data["case_id"], m.group(1), data


def test_start_auto_generates_tasks_and_hides_ground_truth(tmp_path):
    client = TestClient(_app(tmp_path))
    case_id, order_id, data = _start_and_get_order_id(client)
    assert data["difficulty"] in ("beginner", "intermediate", "advanced")
    blob = str(data)
    assert "rules_involved" not in blob and "already_refunded" not in blob


def test_start_rejects_unknown_mode(tmp_path):
    client = TestClient(_app(tmp_path))
    r = client.post("/api/practice/start", json={"mode": "bogus"})
    assert r.status_code == 400


def test_tool_call_returns_evidence_no_ground_truth(tmp_path):
    client = TestClient(_app(tmp_path))
    case_id, order_id, _ = _start_and_get_order_id(client)
    body = {"case_id": case_id, "tool": "view_order", "args": {"order_id": order_id}}
    r = client.post("/api/practice/tool", json=body)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "rules_involved" not in str(body)


def test_tool_call_unknown_case_404(tmp_path):
    client = TestClient(_app(tmp_path))
    r = client.post("/api/practice/tool", json={"case_id": "nope", "tool": "view_order", "args": {}})
    assert r.status_code == 404


def test_decision_returns_feedback_and_persists_attempt(tmp_path):
    client = TestClient(_app(tmp_path))
    case_id, order_id, _ = _start_and_get_order_id(client)
    r = client.post(
        "/api/practice/decision",
        json={"case_id": case_id, "action": "escalate", "args": {"order_id": order_id, "reason_code": "x"}},
    )
    assert r.status_code == 200
    body = r.json()
    for key in ("success", "score", "explanation", "did_well", "missed", "attempt_id", "rule_tags"):
        assert key in body


def test_decision_case_only_resolvable_once(tmp_path):
    client = TestClient(_app(tmp_path))
    case_id, order_id, _ = _start_and_get_order_id(client)
    args = {"case_id": case_id, "action": "escalate", "args": {"order_id": order_id, "reason_code": "x"}}
    assert client.post("/api/practice/decision", json=args).status_code == 200
    assert client.post("/api/practice/decision", json=args).status_code == 404


def test_hints_reduce_score(tmp_path):
    client = TestClient(_app(tmp_path))
    case_id, order_id, _ = _start_and_get_order_id(client)
    r = client.post(
        "/api/practice/decision",
        json={
            "case_id": case_id,
            "action": "escalate",
            "args": {"order_id": order_id, "reason_code": "x"},
            "hints_used": 2,
        },
    )
    body = r.json()
    assert body["score"] <= body["raw_score"]


def test_result_endpoint_matches_decision(tmp_path):
    client = TestClient(_app(tmp_path))
    case_id, order_id, _ = _start_and_get_order_id(client)
    decision = {
        "case_id": case_id,
        "action": "reject_refund",
        "args": {"order_id": order_id, "reason_code": "x"},
    }
    r = client.post("/api/practice/decision", json=decision)
    attempt_id = r.json()["attempt_id"]
    r2 = client.get(f"/api/practice/result/{attempt_id}")
    assert r2.status_code == 200
    assert r2.json()["explanation"] == r.json()["explanation"]


def test_result_missing_404(tmp_path):
    client = TestClient(_app(tmp_path))
    assert client.get("/api/practice/result/9999").status_code == 404


def test_progress_empty_before_any_attempts(tmp_path):
    client = TestClient(_app(tmp_path))
    r = client.get("/api/progress")
    assert r.status_code == 200
    assert r.json()["cases_completed"] == 0


def test_progress_reflects_completed_case(tmp_path):
    client = TestClient(_app(tmp_path))
    case_id, order_id, _ = _start_and_get_order_id(client)
    client.post(
        "/api/practice/decision",
        json={"case_id": case_id, "action": "escalate", "args": {"order_id": order_id, "reason_code": "x"}},
    )
    r = client.get("/api/progress")
    body = r.json()
    assert body["cases_completed"] == 1
    expected_skills = {"Policy Understanding", "Tool Selection", "Evidence Gathering", "Decision Accuracy"}
    assert set(body["skills"]) == expected_skills


def test_cases_endpoint_lists_without_ground_truth(tmp_path):
    client = TestClient(_app(tmp_path))
    r = client.get("/api/cases?limit=5")
    assert r.status_code == 200
    cases = r.json()
    assert len(cases) == 5
    assert all(c["status"] == "Not attempted" for c in cases)
    assert "rules_involved" not in str(cases)


def test_modes_select_different_difficulty_pools(tmp_path):
    client = TestClient(_app(tmp_path))
    _, _, guided = _start_and_get_order_id(client, mode="guided")
    _, _, challenge = _start_and_get_order_id(client, mode="challenge")
    assert guided["difficulty"] == "beginner"
    assert challenge["difficulty"] == "advanced"
