"""Data isolation: every student-owned resource is enforced by the backend."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from skillforge.db.models import Answer, LearnerConcept, LearningSession
from skillforge.teacher.curriculum import get_question

PROTECTED = [
    ("get", "/api/teacher/topics", None),
    ("get", "/api/teacher/progress", None),
    ("post", "/api/teacher/session/start", {"topic_id": "decision-trees"}),
    ("get", "/api/teacher/session/1", None),
    ("post", "/api/teacher/session/1/answer", {"question_id": "dt-1", "choice": 0}),
    ("get", "/api/teacher/session/1/report", None),
    ("get", "/api/timetable", None),
    (
        "post",
        "/api/timetable",
        {"day_of_week": 0, "start_time": "09:00", "end_time": "10:00", "subject_id": "machine-learning"},
    ),
    (
        "put",
        "/api/timetable/1",
        {"day_of_week": 0, "start_time": "09:00", "end_time": "10:00", "subject_id": "machine-learning"},
    ),
    ("delete", "/api/timetable/1", None),
]


@pytest.mark.parametrize("method,path,body", PROTECTED)
def test_unauthenticated_requests_rejected(app, method, path, body):
    client = TestClient(app)
    r = getattr(client, method)(path, json=body) if body is not None else getattr(client, method)(path)
    assert r.status_code == 401


def test_health_stays_public(app):
    assert TestClient(app).get("/api/health").status_code == 200


def test_me_reports_signed_out_without_error(app):
    r = TestClient(app).get("/api/auth/me")
    assert r.status_code == 200 and r.json() == {"user": None}


def test_student_cannot_read_or_answer_another_students_session(make_student, app):
    a = make_student("a@example.com", "Student A")
    b = make_student("b@example.com", "Student B")
    s = a.post("/api/teacher/session/start", json={"topic_id": "decision-trees"}).json()
    q = s["current_question"]

    assert b.get(f"/api/teacher/session/{s['id']}").status_code == 404
    assert b.get(f"/api/teacher/session/{s['id']}/report").status_code == 404
    ans = get_question("decision-trees", q["id"])["answer"]
    r = b.post(f"/api/teacher/session/{s['id']}/answer", json={"question_id": q["id"], "choice": ans})
    assert r.status_code == 404
    # Nothing was written for A's session by B's attempt.
    with app.state.db.session() as db:
        assert db.scalar(select(Answer)) is None
        assert db.get(LearningSession, s["id"]).answered_count == 0
    # A still owns and can use it.
    assert a.get(f"/api/teacher/session/{s['id']}").status_code == 200


def test_progress_and_mastery_are_per_student(make_student):
    a = make_student("a@example.com", "Student A")
    b = make_student("b@example.com", "Student B")
    s = a.post("/api/teacher/session/start", json={"topic_id": "os-deadlock"}).json()
    for _ in range(5):
        q = s["current_question"]
        ans = get_question("os-deadlock", q["id"])["answer"]
        s = a.post(
            f"/api/teacher/session/{s['id']}/answer", json={"question_id": q["id"], "choice": ans}
        ).json()["session"]
    pa = a.get("/api/teacher/progress").json()
    pb = b.get("/api/teacher/progress").json()
    assert pa["sessions_completed"] == 1 and pa["learner_model"]["tracked"] > 0
    assert pb["sessions_completed"] == 0 and pb["questions_answered"] == 0
    assert pb["learner_model"]["tracked"] == 0 and pb["active_session"] is None


def test_separate_students_have_independent_learner_states(make_student, app):
    a = make_student("a@example.com", "Student A")
    b = make_student("b@example.com", "Student B")
    for client, ok in ((a, True), (b, False)):
        s = client.post("/api/teacher/session/start", json={"topic_id": "decision-trees"}).json()
        for _ in range(5):
            q = s["current_question"]
            ans = get_question("decision-trees", q["id"])["answer"]
            s = client.post(
                f"/api/teacher/session/{s['id']}/answer",
                json={"question_id": q["id"], "choice": ans if ok else (ans + 1) % 4},
            ).json()["session"]
    with app.state.db.session() as db:
        rows = db.execute(
            select(LearnerConcept.user_id, LearnerConcept.concept_id, LearnerConcept.p_known)
        ).all()
    by_user: dict[int, dict] = {}
    for uid, cid, p in rows:
        by_user.setdefault(uid, {})[cid] = p
    assert set(by_user) == {1, 2}
    shared = set(by_user[1]) & set(by_user[2])
    assert shared
    for cid in shared:
        assert by_user[1][cid] > 0.5 > by_user[2][cid]

    # Each student's next session starts from their own estimates.
    est_a = {
        c["id"]: c["estimate"]
        for c in a.post("/api/teacher/session/start", json={"topic_id": "decision-trees"}).json()["concepts"]
    }
    est_b = {
        c["id"]: c["estimate"]
        for c in b.post("/api/teacher/session/start", json={"topic_id": "decision-trees"}).json()["concepts"]
    }
    for key in est_a:
        assert est_a[key] != est_b[key]


def test_student_cannot_touch_another_students_timetable(make_student):
    a = make_student("a@example.com", "Student A")
    b = make_student("b@example.com", "Student B")
    entry = a.post(
        "/api/timetable",
        json={
            "day_of_week": 1,
            "start_time": "09:00",
            "end_time": "09:50",
            "subject_id": "computer-networks",
            "room": "A-204",
        },
    ).json()
    body = {"day_of_week": 2, "start_time": "10:00", "end_time": "11:00", "subject_id": "machine-learning"}
    assert b.put(f"/api/timetable/{entry['id']}", json=body).status_code == 404
    assert b.delete(f"/api/timetable/{entry['id']}").status_code == 404
    assert b.get("/api/timetable").json()["entries"] == []
    assert a.get("/api/timetable").json()["entries"][0]["room"] == "A-204"
