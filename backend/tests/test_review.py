"""Wrong-answer teaching feedback and the Student Performance Review (PTM)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.learner_helpers import choice_for

TZ = {"tz_offset": -330}


def _answer(client, session, ok):
    q = session["current_question"]
    r = client.post(
        f"/api/teacher/session/{session['id']}/answer",
        json={"question_id": q["id"], "choice": choice_for(q["id"], ok), "response_ms": 5000},
    ).json()
    return r["feedback"], r["session"]


# --- Wrong-answer experience ----------------------------------------------------------


def test_wrong_answer_teaches_with_explanation_takeaway_link_and_resources(make_student):
    client = make_student()
    s = client.post("/api/teacher/session/start", json={"topic_id": "decision-trees"}).json()
    fb, s = _answer(client, s, ok=False)
    r = fb["review"]
    assert r["your_answer"]["letter"] != r["correct_answer"]["letter"]
    assert r["correct_answer"]["letter"] == "ABCD"[fb["correct_choice"]]
    assert len(r["why"]) > 30 and len(r["remember"]) > 30
    assert r["related"]["topic_id"] == "decision-trees" and r["related"]["concept"] == fb["concept"]
    assert r["related"]["subject_name"] == "Machine Learning"
    assert 1 <= len(r["resources"]) <= 3
    assert all(x["url"].startswith("https://") for x in r["resources"])


def test_correct_answer_has_no_review_block_and_dsa_sessions_work(make_student):
    client = make_student()
    s = client.post("/api/teacher/session/start", json={"topic_id": "dsa-asymptotic"}).json()
    assert s["subject_id"] == "dsa"
    fb, s = _answer(client, s, ok=True)
    assert fb["correct"] is True and fb["review"] is None
    fb, s = _answer(client, s, ok=False)
    assert fb["review"]["related"]["subject_id"] == "dsa"


def test_topic_without_curated_resources_gets_none_invented(make_student):
    client = make_student()
    s = client.post("/api/teacher/session/start", json={"topic_id": "gs-definition"}).json()
    fb, _ = _answer(client, s, ok=False)
    assert fb["review"]["resources"] == []
    assert fb["review"]["why"]  # the explanation still teaches


# --- Performance review -----------------------------------------------------------------


def test_review_for_new_student_is_genuinely_empty(make_student):
    r = make_student().get("/api/learner/review", params=TZ).json()
    o = r["overview"]
    assert o["has_evidence"] is False and o["key"] == "insufficient"
    assert o["estimate"] is None and o["questions_attempted"] == 0 and o["sessions_completed"] == 0
    assert r["strengths"] == [] and r["improvement_areas"] == []
    assert all(s["status"] in ("too_early", "no_bank") for s in r["subjects"])
    assert r["difficulty"]["highest_demonstrated"] is None and r["cognitive"]["summary"] is None
    assert r["behaviour"]["enough"] is False and r["behaviour"]["longest_gap_days"] is None
    assert "no graded answers yet" in r["teacher_summary"][0]["text"]


def test_review_numbers_match_learner_state_and_sessions(make_student):
    client = make_student()
    s = client.post("/api/teacher/session/start", json={"topic_id": "decision-trees"}).json()
    for ok in [True, False, False, True, True]:
        _, s = _answer(client, s, ok)
    review = client.get("/api/learner/review", params=TZ).json()
    state = client.get("/api/learner/state").json()["overall"]
    o = review["overview"]
    assert o["questions_attempted"] == state["attempts"] == 5
    assert o["correct"] == state["correct"] == 3
    assert o["estimate"] == state["estimate"] and o["assessed"] == state["assessed"]
    assert o["sessions_completed"] == 1 == review["assessment"]["sessions_completed"]
    assert review["assessment"]["sessions"][0]["score"] == 3 / 5
    ml = next(x for x in review["subjects"] if x["id"] == "machine-learning")
    assert ml["attempts"] == 5 and ml["status"] != "too_early"
    dt = next(t for u in ml["units"] for t in u["topics"] if t["id"] == "decision-trees")
    concepts = {c["key"]: c for c in dt["concepts"]}
    assert sum(c["attempts"] for c in concepts.values()) == 5
    for c in concepts.values():
        assert c["action"]["topic_id"] == "decision-trees" and c["action"]["text"]
    # Five answers are not enough for any subject trend, and no level is
    # "demonstrated" from fewer than three answers at it.
    assert ml["trend"] is None
    for row in review["difficulty"]["rows"]:
        assert not row["demonstrated"] or row["attempts"] >= 3
    assert len(review["action_plan"]) >= 1
    assert review["teacher_summary"][0]["heading"] == "Overall assessment"


def test_one_correct_answer_is_never_a_strength(make_student):
    client = make_student()
    s = client.post("/api/teacher/session/start", json={"topic_id": "os-cpu-scheduling"}).json()
    _answer(client, s, ok=True)
    r = client.get("/api/learner/review", params=TZ).json()
    assert r["strengths"] == []
    assert r["overview"]["key"] == "early"


def test_review_is_private_to_each_student(make_student, app):
    a = make_student("asha@example.com")
    s = a.post("/api/teacher/session/start", json={"topic_id": "decision-trees"}).json()
    _answer(a, s, ok=False)
    b = make_student("ravi@example.com")
    rb = b.get("/api/learner/review", params=TZ).json()
    assert rb["overview"]["questions_attempted"] == 0
    assert rb["student"]["email"] == "ravi@example.com"
    assert TestClient(app).get("/api/learner/review").status_code == 401
