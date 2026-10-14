from __future__ import annotations

from fastapi.testclient import TestClient

from skillforge.teacher.curriculum import get_question


def _answer(client, session, topic_id, ok):
    q = session["current_question"]
    ans = get_question(topic_id, q["id"])["answer"]
    r = client.post(
        f"/api/teacher/session/{session['id']}/answer",
        json={"question_id": q["id"], "choice": ans if ok else (ans + 1) % 4},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _complete(client, topic_id, pattern):
    s = client.post("/api/teacher/session/start", json={"topic_id": topic_id}).json()
    for ok in pattern:
        s = _answer(client, s, topic_id, ok)["session"]
    return s


def test_topics_lists_vnr_curriculum_with_units_and_no_answers(make_student):
    body = make_student().get("/api/teacher/topics").json()
    assert [s["code"] for s in body["subjects"]][:2] == ["22PC1IN202", "22PC1AM301"]
    ml = next(s for s in body["subjects"] if s["id"] == "machine-learning")
    assert [u["title"] for u in ml["units"]][1] == "Supervised Learning – I"
    topics = [t for s in body["subjects"] for u in s["units"] for t in u["topics"]]
    assert all(t["progress"] is None or t["progress"]["status"] == "not_started" for t in topics)
    assert '"answer"' not in str(body).replace("'", '"')


def test_start_session_returns_lesson_and_question_without_answer_key(make_student):
    r = make_student().post("/api/teacher/session/start", json={"topic_id": "decision-trees"})
    assert r.status_code == 200
    s = r.json()
    assert s["lesson"]["intro"]
    assert s["unit_title"] == "Supervised Learning – I"
    assert "answer" not in s["current_question"] and "explanation" not in s["current_question"]


def test_start_unknown_topic_404_and_topic_without_bank_409(make_student):
    client = make_student()
    assert client.post("/api/teacher/session/start", json={"topic_id": "nope"}).status_code == 404
    assert client.post("/api/teacher/session/start", json={"topic_id": "cn-dns"}).status_code == 409


def test_answer_returns_feedback_and_persists(make_student, app):
    client = make_student()
    s = client.post("/api/teacher/session/start", json={"topic_id": "os-deadlock"}).json()
    body = _answer(client, s, "os-deadlock", True)
    assert body["feedback"]["verdict"] == "correct" and body["feedback"]["message"]
    again = client.get(f"/api/teacher/session/{s['id']}").json()
    assert again["answered"] == 1
    assert again["current_question"]["id"] == body["session"]["current_question"]["id"]


def test_answer_wrong_question_409_and_unknown_session_404(make_student):
    client = make_student()
    s = client.post("/api/teacher/session/start", json={"topic_id": "os-deadlock"}).json()
    r = client.post(f"/api/teacher/session/{s['id']}/answer", json={"question_id": "os-dl-6", "choice": 0})
    assert r.status_code == 409
    assert client.get("/api/teacher/session/9999").status_code == 404


def test_report_only_after_completion(make_student):
    client = make_student()
    s = client.post("/api/teacher/session/start", json={"topic_id": "lab-page-replacement"}).json()
    assert client.get(f"/api/teacher/session/{s['id']}/report").status_code == 409
    s = _complete(client, "lab-page-replacement", [True, True, False, True, True])
    assert s["status"] == "completed"
    report = client.get(f"/api/teacher/session/{s['id']}/report").json()
    assert report["correct"] == 4 and report["attempted"] == 5
    assert report["recommendation"]["next_topic_title"]


def test_fresh_account_has_no_fake_progress(make_student):
    p = make_student().get("/api/teacher/progress").json()
    assert p["sessions_completed"] == 0
    assert p["questions_answered"] == 0
    assert p["overall_mastery"] is None
    assert p["recent_sessions"] == [] and p["strengths"] == [] and p["areas_to_improve"] == []
    assert p["learner_model"]["tracked"] == 0
    assert p["recommended"]["from_session_id"] is None


def test_progress_reflects_completed_sessions(make_student):
    client = make_student()
    _complete(client, "decision-trees", [True] * 5)
    p = client.get("/api/teacher/progress").json()
    assert p["sessions_completed"] == 1
    assert p["questions_answered"] == 5 and p["correct_answers"] == 5
    # Mastery is concept-level evidence, not the session score. The session
    # asks Splitting criteria three times (correct at Foundational, Advanced and
    # Intermediate), which meets the mastery rule; the other two concepts got
    # one answer each, so the topic as a whole is not mastered yet.
    assert 0.5 < p["overall_mastery"] < 1.0
    assert p["concepts_assessed"] == 3 and p["concepts_total"] >= 3
    assert p["concepts_mastered"] == 1 and p["topics_mastered"] == 0
    assert [s["concept"] for s in p["strengths"]] == ["Splitting criteria"]
    assert p["subjects_studied"] == 1
    assert p["recent_sessions"][0]["mastery"] == 1.0  # the session report score is unchanged
    assert p["recommended"]["topic_id"] == "bias-variance"
    assert p["recent_sessions"][0]["topic_title"] == "Decision Trees – ID3 and CART"
    assert p["learner_model"]["tracked"] >= 2


def test_needs_review_status_comes_from_weak_concepts(make_student):
    client = make_student()
    _complete(client, "os-cpu-scheduling", [False] * 5)
    topics = client.get("/api/teacher/topics").json()["subjects"]
    t = next(t for s in topics for u in s["units"] for t in u["topics"] if t["id"] == "os-cpu-scheduling")
    assert t["progress"]["status"] == "needs_review"
    assert t["progress"]["needs_review"]


def test_active_session_is_resumable_and_replaced_by_new_start(make_student):
    client = make_student()
    first = client.post("/api/teacher/session/start", json={"topic_id": "os-deadlock"}).json()
    assert client.get("/api/teacher/progress").json()["active_session"]["id"] == first["id"]
    second = client.post("/api/teacher/session/start", json={"topic_id": "ai-search-strategies"}).json()
    assert client.get("/api/teacher/progress").json()["active_session"]["id"] == second["id"]
    shelved = client.get(f"/api/teacher/session/{first['id']}").json()
    assert shelved["status"] == "abandoned"
    q = shelved["current_question"]
    r = client.post(f"/api/teacher/session/{first['id']}/answer", json={"question_id": q["id"], "choice": 0})
    assert r.status_code == 409


def test_second_session_uses_prior_mastery_to_diagnose(make_student):
    client = make_student()
    _complete(client, "mllab-model-training", [True] * 5)
    s = client.post("/api/teacher/session/start", json={"topic_id": "mllab-model-training"}).json()
    assert s["level"] == 2
    assert "Previous mastery" in s["log"][0]["text"]


def test_history_survives_logout_login_and_app_restart(make_student, app, tmp_path):
    client = make_student()
    done = _complete(client, "gs-definition", [True, False, True, True, True])
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/teacher/progress").status_code == 401

    # A brand-new application process on the same database file.
    from skillforge.api.app import create_app
    from skillforge.auth.email import ConsoleEmailSender

    restarted = create_app(database_url=f"sqlite:///{tmp_path / 'api.db'}", email_sender=ConsoleEmailSender())
    c2 = TestClient(restarted)
    assert (
        c2.post("/api/auth/login", json={"email": "asha@example.com", "password": "forge2024x"}).status_code
        == 200
    )
    p = c2.get("/api/teacher/progress").json()
    assert p["sessions_completed"] == 1 and p["questions_answered"] == 5
    report = c2.get(f"/api/teacher/session/{done['id']}/report").json()
    assert report["correct"] == 4
    restarted.state.db.engine.dispose()
