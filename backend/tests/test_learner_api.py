"""API tests for this phase: cold start, practice modes, insights, profile,
adaptive session start, and per-student isolation of every new resource."""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy import select, update

from skillforge.db.models import EvidenceEvent, FlashcardReview, LearnerConcept, Question, RapidRound
from skillforge.learner.evidence import utcnow
from skillforge.teacher.curriculum import find_question
from tests.learner_helpers import choice_for

TZ = {"tz_offset": -330}


def _run_diagnostic(client, pattern):
    d = client.post("/api/learner/diagnostic/start").json()
    for ok in pattern:
        q = d["current_question"]
        assert "answer" not in q and "explanation" not in q
        choice = None if ok is None else choice_for(q["id"], ok)
        d = client.post(
            "/api/learner/diagnostic/answer",
            json={"question_id": q["id"], "choice": choice, "response_ms": 4000},
        ).json()
    return d


def _session(client, topic_id, pattern, **start):
    s = client.post("/api/teacher/session/start", json={"topic_id": topic_id, **start}).json()
    for ok in pattern:
        q = s["current_question"]
        s = client.post(
            f"/api/teacher/session/{s['id']}/answer",
            json={"question_id": q["id"], "choice": choice_for(q["id"], ok), "response_ms": 6000},
        ).json()["session"]
    return s


# --- Cold start ------------------------------------------------------------------------


def test_fresh_account_overview_is_empty_and_suggests_diagnostic(make_student):
    o = make_student().get("/api/learner/overview", params=TZ).json()
    assert o["has_evidence"] is False and o["diagnostic_status"] == "none"
    assert o["overall"]["estimate"] is None and o["overall"]["mastered"] == 0
    assert o["next_up"]["action"] == "take_diagnostic"
    assert o["weakest_concept"] is None and o["improved_concept"] is None and o["today"] is None
    assert o["activity_level"]["xp"] == 0


def test_diagnostic_samples_every_subject_and_initialises_state_carefully(make_student, app):
    client = make_student()
    # One question per subject with a bank: the eight VNR courses and DSA.
    d = _run_diagnostic(client, [True, False, True, None, True, False, True, True, False])
    assert d["status"] == "completed" and d["total"] == 9
    subjects = {i["subject_id"] for i in d["summary"]["items"]}
    assert len(subjects) == 9 and "dsa" in subjects
    assert d["summary"]["skipped"] == 1 and d["summary"]["answered"] == 8
    assert "starting point" in d["summary"]["note"]
    state = client.get("/api/learner/state").json()["overall"]
    assert state["assessed"] == 8  # the skipped question recorded no evidence
    assert state["mastered"] == 0  # one answer per concept can never be mastery
    with app.state.db.session() as s:
        sources = {e.source for e in s.scalars(select(EvidenceEvent))}
    assert sources == {"diagnostic"}
    # Cannot be taken twice; status visible.
    assert client.post("/api/learner/diagnostic/start").status_code == 409
    assert client.get("/api/learner/diagnostic").json()["status"] == "completed"


def test_diagnostic_can_be_skipped(make_student):
    client = make_student()
    assert client.post("/api/learner/diagnostic/skip").json()["status"] == "skipped"
    o = client.get("/api/learner/overview", params=TZ).json()
    assert o["next_up"]["action"] == "start_new_topic"


def test_diagnostic_rejects_out_of_order_answers(make_student):
    client = make_student()
    d = client.post("/api/learner/diagnostic/start").json()
    first = d["current_question"]["id"]
    other = "gs-6" if first != "gs-6" else "dt-6"
    r = client.post("/api/learner/diagnostic/answer", json={"question_id": other, "choice": 0})
    assert r.status_code == 409


# --- Adaptive session start ---------------------------------------------------------------


def test_recommendation_focus_and_difficulty_steer_session_start(make_student):
    client = make_student()
    s = client.post(
        "/api/teacher/session/start",
        json={"topic_id": "os-cpu-scheduling", "focus_concept": "evaluation", "target_difficulty": 2},
    ).json()
    _, _, q = find_question(s["current_question"]["id"])
    assert q["concept"] == "evaluation"
    # Algorithm evaluation only has Advanced questions, so the level follows
    # the question actually served, and the log says why.
    assert q["difficulty"] == 3 and s["level"] == 3
    texts = [line["text"] for line in s["log"]]
    assert any("Focusing first on Algorithm evaluation" in t for t in texts)
    assert any("closest question on Algorithm evaluation is at the Advanced level" in t for t in texts)


def test_exposure_makes_the_engine_prefer_unseen_questions():
    from skillforge.teacher import engine

    default = engine.start_session("os-deadlock", learner_model=None)["current_question_id"]
    fresh = engine.start_session("os-deadlock", learner_model=None, exposure={default: 2})
    assert fresh["current_question_id"] != default
    _, _, q = find_question(fresh["current_question_id"])
    assert q["difficulty"] == 1  # still at the right level


def test_retired_questions_are_never_served(make_student, app):
    client = make_student()
    with app.state.db.session() as s:
        s.execute(update(Question).where(Question.id.in_(["dt-1", "dt-2"])).values(quality="retired"))
        s.commit()
    from skillforge.teacher.seed import load_curriculum

    load_curriculum(app.state.db)
    try:
        s = _session(client, "decision-trees", [True, True, True, True])
        asked = s["log"]
        assert s["max_questions"] == 4
        assert all("dt-1" not in str(x) for x in asked)
    finally:
        with app.state.db.session() as s:
            s.execute(update(Question).where(Question.id.in_(["dt-1", "dt-2"])).values(quality="reviewed"))
            s.commit()
        load_curriculum(app.state.db)


def test_session_answers_record_evidence_with_response_time(make_student, app):
    client = make_student()
    _session(client, "lab-page-replacement", [True, False])
    with app.state.db.session() as s:
        rows = s.scalars(select(EvidenceEvent)).all()
    assert [r.source for r in rows] == ["session", "session"]
    assert all(r.response_ms == 6000 and r.p_after is not None for r in rows)


# --- Flashcards ----------------------------------------------------------------------------


def test_flashcards_are_personalised_and_hide_backs(make_student):
    client = make_student()
    assert client.get("/api/study/flashcards", params=TZ).json()["cards"] == []
    _session(client, "os-deadlock", [False, False, True, True, False])
    cards = client.get("/api/study/flashcards", params=TZ).json()["cards"]
    assert cards and all("back" not in c for c in cards)
    assert all(c["subject_name"] == "Operating Systems" for c in cards)
    assert any("incorrect" in " ".join(c["reasons"]).lower() for c in cards)
    back = client.post("/api/study/flashcards/reveal", json={"card_id": cards[0]["id"]}).json()["back"]
    assert back["title"] and back["text"]


def test_question_flashcards_only_for_seen_questions(make_student):
    client = make_student()
    r = client.post("/api/study/flashcards/reveal", json={"card_id": "question:os-dl-6"})
    assert r.status_code == 404
    assert client.post("/api/study/flashcards/reveal", json={"card_id": "nonsense"}).status_code == 404


def test_flashcard_rating_is_secondary_signal(make_student, app):
    client = make_student()
    _session(client, "os-deadlock", [True, True])
    before = client.get("/api/learner/state").json()["overall"]
    card = client.get("/api/study/flashcards", params=TZ).json()["cards"][0]
    assert client.post("/api/study/flashcards/review", json={"card_id": card["id"], "rating": "known"}).json()
    assert (
        client.post(
            "/api/study/flashcards/review", json={"card_id": card["id"], "rating": "bogus"}
        ).status_code
        == 400
    )
    after = client.get("/api/learner/state").json()["overall"]
    assert before["estimate"] == after["estimate"] and before["attempts"] == after["attempts"]
    with app.state.db.session() as s:
        assert s.scalar(select(FlashcardReview)).rating == "known"


# --- Rapid Round ----------------------------------------------------------------------------


def test_rapid_round_flow_and_lighter_evidence(make_student, app):
    client = make_student()
    r = client.post("/api/study/rapid/start").json()
    assert len(r["questions"]) == 10 and 59 <= r["remaining_seconds"] <= 60
    assert all("answer" not in q for q in r["questions"])
    for q in r["questions"][:3]:
        res = client.post(
            f"/api/study/rapid/{r['id']}/answer",
            json={"question_id": q["id"], "choice": choice_for(q["id"], True), "response_ms": 2500},
        )
        assert res.json()["correct"] is True
    dup = client.post(
        f"/api/study/rapid/{r['id']}/answer", json={"question_id": r["questions"][0]["id"], "choice": 0}
    )
    assert dup.status_code == 409
    results = client.post(f"/api/study/rapid/{r['id']}/finish").json()
    assert results["attempted"] == 3 and results["correct"] == 3 and results["headline"] == "Strong retrieval"
    with app.state.db.session() as s:
        assert {e.weight for e in s.scalars(select(EvidenceEvent))} == {0.5}
    # Finished rounds accept no more answers.
    q = r["questions"][5]
    late = client.post(f"/api/study/rapid/{r['id']}/answer", json={"question_id": q["id"], "choice": 0})
    assert late.status_code == 409


def test_rapid_round_deadline_is_enforced_by_server(make_student, app):
    client = make_student()
    r = client.post("/api/study/rapid/start").json()
    with app.state.db.session() as s:
        s.execute(update(RapidRound).values(deadline_at=utcnow() - dt.timedelta(seconds=30)))
        s.commit()
    q = r["questions"][0]
    res = client.post(f"/api/study/rapid/{r['id']}/answer", json={"question_id": q["id"], "choice": 0})
    assert res.status_code == 409 and "Time is up" in res.json()["detail"]


def test_rapid_round_labels_are_not_judgemental():
    from skillforge.learner.rapid import label

    assert label(1.0, 12_000, 5)[0] == "Slow but accurate"
    assert label(0.9, 3_000, 5)[0] == "Strong retrieval"
    assert label(0.6, 3_000, 5)[0] == "Mixed retrieval"
    assert label(0.2, 3_000, 5)[0] == "Needs review"
    assert label(None, None, 0)[0] == "No answers recorded"


# --- Insights: calendar, trends, PTM, level -------------------------------------------------


def test_calendar_empty_then_real_activity(make_student):
    client = make_student()
    today = dt.date.today()
    params = {"start": str(today - dt.timedelta(days=30)), "end": str(today + dt.timedelta(days=1)), **TZ}
    empty = client.get("/api/learner/activity", params=params).json()
    assert empty["days"] == [] and empty["active_days"] == 0
    _session(client, "os-deadlock", [True, True, False, True, True])
    days = client.get("/api/learner/activity", params=params).json()["days"]
    assert len(days) == 1
    d = days[0]
    assert d["sessions_completed"] == 1 and d["graded_answers"] == 5 and d["correct"] == 4
    assert d["by_source"]["session"] == 5 and d["concepts_practised"] >= 2 and d["active_minutes"] >= 1


def test_calendar_rejects_huge_ranges(make_student):
    r = make_student().get("/api/learner/activity", params={"start": "2020-01-01", "end": "2026-01-01"})
    assert r.status_code == 400


def test_trends_reflect_real_answers(make_student):
    client = make_student()
    weeks = client.get("/api/learner/trends", params=TZ).json()["weeks"]
    assert len(weeks) == 8 and all(w["graded_answers"] == 0 and w["estimate"] is None for w in weeks)
    _session(client, "os-deadlock", [True, False])
    last = client.get("/api/learner/trends", params=TZ).json()["weeks"][-1]
    assert last["graded_answers"] == 2 and last["accuracy"] == 0.5 and last["estimate"] is not None


def test_ptm_is_evidence_driven(make_student, app):
    client = make_student()
    empty = client.get("/api/learner/ptm", params=TZ).json()
    assert all(v == [] for v in empty["swot"].values())
    _session(client, "decision-trees", [True] * 5)  # Splitting criteria answered 3× correctly
    _session(client, "os-deadlock", [False, False, False, False, False])
    p = client.get("/api/learner/ptm", params=TZ).json()
    strengths = p["swot"]["strengths"]
    weaknesses = p["swot"]["weaknesses"]
    assert strengths and strengths[0]["concept"] == "Splitting criteria"
    assert "graded attempts" in strengths[0]["text"]
    assert weaknesses and all("incorrect" in w["text"] for w in weaknesses)
    assert p["student"]["name"] == "Asha Rao"
    # Neglect becomes a threat only from real dates.
    with app.state.db.session() as s:
        s.execute(
            update(EvidenceEvent)
            .where(EvidenceEvent.concept_id.like("os-deadlock/%"))
            .values(created_at=utcnow() - dt.timedelta(days=21))
        )
        s.commit()
    threats = client.get("/api/learner/ptm", params=TZ).json()["swot"]["threats"]
    assert any("21 days" in t["text"] for t in threats)


def test_activity_level_is_separate_from_mastery(make_student):
    client = make_student()
    _session(client, "os-deadlock", [False] * 5)
    o = client.get("/api/learner/overview", params=TZ).json()
    assert o["activity_level"]["xp"] == 5 * 10 + 25  # 5 answers + 1 completed session
    assert "not what you know" in o["activity_level"]["note"]
    assert o["overall"]["estimate"] < 0.3  # lots of activity, little knowledge


def test_overview_links_timetable_to_preparation(make_student):
    client = make_student()
    now = dt.datetime.now(dt.UTC).replace(tzinfo=None) + dt.timedelta(minutes=330)  # IST wall clock
    soon = now + dt.timedelta(hours=2)
    client.post(
        "/api/timetable",
        json={
            "day_of_week": soon.weekday(),
            "start_time": soon.strftime("%H:%M"),
            "end_time": (soon + dt.timedelta(minutes=50)).strftime("%H:%M"),
            "subject_id": "operating-systems",
        },
    )
    if soon.date() != now.date() or soon.strftime("%H:%M") < "00:30":
        return  # avoid a midnight edge case in the wall-clock arithmetic
    o = client.get("/api/learner/overview", params=TZ).json()
    cls = o["upcoming_classes"][0]
    assert cls["subject_id"] == "operating-systems" and cls["preparation"]["action"] == "prepare_for_class"


def test_profile_preferences(make_student):
    client = make_student()
    p = client.get("/api/profile").json()
    assert p["preferences"] == {"mode": "student", "theme": "auto", "diagnostic_skipped": False}
    assert client.put("/api/profile/preferences", json={"mode": "ptm", "theme": "diwali"}).status_code == 200
    assert client.get("/api/profile").json()["preferences"]["mode"] == "ptm"
    assert client.put("/api/profile/preferences", json={"theme": "neon"}).status_code == 400
    assert client.put("/api/profile/preferences", json={"mode": "parent"}).status_code == 400


# --- Isolation ----------------------------------------------------------------------------------


def test_new_resources_are_isolated_between_students(make_student, app):
    a = make_student("a@example.com", "Student A")
    b = make_student("b@example.com", "Student B")
    _run_diagnostic(a, [True] * 8)
    _session(a, "os-deadlock", [True, False, True])
    card = a.get("/api/study/flashcards", params=TZ).json()["cards"][0]
    a.post("/api/study/flashcards/review", json={"card_id": card["id"], "rating": "review"})
    r = a.post("/api/study/rapid/start").json()
    a.put("/api/profile/preferences", json={"mode": "ptm"})

    assert b.get(f"/api/study/rapid/{r['id']}").status_code == 404
    q = r["questions"][0]
    assert (
        b.post(f"/api/study/rapid/{r['id']}/answer", json={"question_id": q["id"], "choice": 0}).status_code
        == 404
    )
    assert b.post(f"/api/study/rapid/{r['id']}/finish").status_code == 404
    assert b.get("/api/learner/diagnostic").json()["status"] == "none"
    ob = b.get("/api/learner/overview", params=TZ).json()
    assert ob["has_evidence"] is False and ob["overall"]["assessed"] == 0
    assert b.get("/api/learner/state").json()["overall"]["assessed"] == 0
    assert all(v == [] for v in b.get("/api/learner/ptm", params=TZ).json()["swot"].values())
    assert b.get("/api/study/flashcards", params=TZ).json()["cards"] == []
    today = dt.date.today()
    cal = b.get("/api/learner/activity", params={"start": str(today), "end": str(today), **TZ}).json()
    assert cal["days"] == []
    assert b.get("/api/profile").json()["preferences"]["mode"] == "student"
    # A's seen question is not revealable as a flashcard for B.
    seen_q = next(
        c for c in a.get("/api/study/flashcards", params=TZ).json()["cards"] if c["kind"] == "question"
    )
    assert b.post("/api/study/flashcards/reveal", json={"card_id": seen_q["id"]}).status_code == 404
    with app.state.db.session() as s:
        assert {lc.user_id for lc in s.scalars(select(LearnerConcept))} == {1}


def test_new_endpoints_require_authentication(app):
    c = TestClient(app)
    for method, path in [
        ("get", "/api/learner/overview"),
        ("get", "/api/learner/state"),
        ("get", "/api/learner/recommendations"),
        ("get", "/api/learner/trends"),
        ("get", "/api/learner/ptm"),
        ("get", "/api/learner/diagnostic"),
        ("post", "/api/learner/diagnostic/start"),
        ("get", "/api/study/flashcards"),
        ("post", "/api/study/rapid/start"),
        ("get", "/api/study/rapid/1"),
        ("get", "/api/profile"),
    ]:
        assert getattr(c, method)(path).status_code == 401, path
    assert (
        c.get("/api/learner/activity", params={"start": "2026-01-01", "end": "2026-01-02"}).status_code == 401
    )
