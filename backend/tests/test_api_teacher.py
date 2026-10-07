from __future__ import annotations

from fastapi.testclient import TestClient

from skillforge.api.app import create_app
from skillforge.teacher.curriculum import get_question


def _client(tmp_path, seed_demo=False):
    return TestClient(create_app(database_url=f"sqlite:///{tmp_path / 'teacher.db'}", seed_demo=seed_demo))


def _complete(client, topic_id, pattern):
    s = client.post("/api/teacher/session/start", json={"topic_id": topic_id}).json()
    for ok in pattern:
        q = s["current_question"]
        ans = get_question(topic_id, q["id"])["answer"]
        r = client.post(
            f"/api/teacher/session/{s['id']}/answer",
            json={"question_id": q["id"], "choice": ans if ok else (ans + 1) % 4},
        )
        assert r.status_code == 200
        s = r.json()["session"]
    return s


def test_topics_lists_curriculum_without_answers(tmp_path):
    body = _client(tmp_path).get("/api/teacher/topics").json()
    assert [s["id"] for s in body["subjects"]] == ["ml", "python", "dsa"]
    assert "answer" not in str(body)


def test_start_session_returns_lesson_and_question_without_answer_key(tmp_path):
    r = _client(tmp_path).post("/api/teacher/session/start", json={"topic_id": "decision-trees"})
    assert r.status_code == 200
    s = r.json()
    assert s["lesson"]["intro"]
    assert s["current_question"]["options"]
    assert "answer" not in s["current_question"]
    assert "explanation" not in s["current_question"]


def test_start_unknown_topic_404(tmp_path):
    r = _client(tmp_path).post("/api/teacher/session/start", json={"topic_id": "nope"})
    assert r.status_code == 404


def test_answer_returns_feedback_and_persists(tmp_path):
    client = _client(tmp_path)
    s = client.post("/api/teacher/session/start", json={"topic_id": "lists"}).json()
    q = s["current_question"]
    ans = get_question("lists", q["id"])["answer"]
    r = client.post(f"/api/teacher/session/{s['id']}/answer", json={"question_id": q["id"], "choice": ans})
    body = r.json()
    assert body["feedback"]["verdict"] == "correct"
    assert body["feedback"]["message"]
    again = client.get(f"/api/teacher/session/{s['id']}").json()
    assert again["answered"] == 1
    assert again["current_question"]["id"] == body["session"]["current_question"]["id"]


def test_answer_wrong_question_409_and_unknown_session_404(tmp_path):
    client = _client(tmp_path)
    s = client.post("/api/teacher/session/start", json={"topic_id": "lists"}).json()
    r = client.post(f"/api/teacher/session/{s['id']}/answer", json={"question_id": "ls-6", "choice": 0})
    assert r.status_code == 409
    r = client.get("/api/teacher/session/9999")
    assert r.status_code == 404


def test_report_only_after_completion(tmp_path):
    client = _client(tmp_path)
    s = client.post("/api/teacher/session/start", json={"topic_id": "stacks"}).json()
    assert client.get(f"/api/teacher/session/{s['id']}/report").status_code == 409
    s = _complete(client, "stacks", [True, True, False, True, True])
    assert s["status"] == "completed"
    report = client.get(f"/api/teacher/session/{s['id']}/report").json()
    assert report["correct"] == 4 and report["attempted"] == 5
    assert report["recommendation"]["next_topic_title"]


def test_progress_reflects_completed_sessions(tmp_path):
    client = _client(tmp_path)
    empty = client.get("/api/teacher/progress").json()
    assert empty["sessions_completed"] == 0
    assert empty["overall_mastery"] is None
    assert empty["recommended"]["topic_id"] == "decision-trees"

    _complete(client, "decision-trees", [True] * 5)
    p = client.get("/api/teacher/progress").json()
    assert p["sessions_completed"] == 1
    assert p["overall_mastery"] == 1.0
    assert p["topics_mastered"] == 1
    assert p["recommended"]["topic_id"] == "overfitting"
    assert p["recent_sessions"][0]["topic_title"] == "Decision Trees"


def test_active_session_is_resumable_and_replaced_by_new_start(tmp_path):
    client = _client(tmp_path)
    first = client.post("/api/teacher/session/start", json={"topic_id": "lists"}).json()
    assert client.get("/api/teacher/progress").json()["active_session"]["id"] == first["id"]
    second = client.post("/api/teacher/session/start", json={"topic_id": "oop"}).json()
    assert client.get("/api/teacher/progress").json()["active_session"]["id"] == second["id"]


def test_second_session_uses_prior_mastery_to_diagnose(tmp_path):
    client = _client(tmp_path)
    _complete(client, "arrays", [True] * 5)
    s = client.post("/api/teacher/session/start", json={"topic_id": "arrays"}).json()
    assert s["level"] == 2
    assert "Previous mastery" in s["log"][0]["text"]


def test_demo_seed_populates_history_once(tmp_path):
    client = _client(tmp_path, seed_demo=True)
    p = client.get("/api/teacher/progress").json()
    assert p["sessions_completed"] == 3
    assert p["strengths"] and p["areas_to_improve"]
    # Re-creating the app on the same DB doesn't seed again.
    client2 = _client(tmp_path, seed_demo=True)
    assert client2.get("/api/teacher/progress").json()["sessions_completed"] == 3
