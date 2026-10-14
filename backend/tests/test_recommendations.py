"""Recommendation engine: rules, explanations, timetable linkage, no-data behaviour."""

from __future__ import annotations

from datetime import datetime, timedelta

from skillforge.learner import recommend
from skillforge.learner import state as learner_state
from tests.learner_helpers import answer, seeded

NOW = datetime(2026, 10, 7, 10, 0)  # a Wednesday


def _recs(db, uid, **ctx):
    with db.session() as s:
        st = learner_state.build(s, uid)
    return recommend.recommend(st, recommend.Context(local_now=NOW, **ctx), limit=10)


def test_new_student_is_offered_the_diagnostic_and_nothing_fabricated(db):
    uid = seeded(db)
    recs = _recs(db, uid)
    assert [r.action for r in recs] == ["take_diagnostic"]


def test_after_skipping_diagnostic_a_first_topic_is_suggested(db):
    uid = seeded(db)
    recs = _recs(db, uid, diagnostic_status="skipped")
    assert recs[0].action == "start_new_topic" and recs[0].topic_id


def test_repeated_mistakes_trigger_remediation_with_evidence(db):
    uid = seeded(db)
    for qid, ok in [("dt-1", True), ("dt-3", False), ("dt-6", False)]:
        answer(db, uid, qid, ok)
    recs = _recs(db, uid, diagnostic_status="completed")
    top = recs[0]
    assert top.action == "remediate_misconception"
    assert top.concept_name == "Splitting criteria" and top.topic_id == "decision-trees"
    assert any("incorrect answers in a row" in e for e in top.evidence)
    assert top.target_difficulty == 1  # step below the easiest missed level (Intermediate)
    assert top.cta == {
        "kind": "session",
        "topic_id": "decision-trees",
        "concept_key": "splitting-criteria",
        "target_difficulty": 1,
    }


def test_neglected_concept_is_revisited(db):
    uid = seeded(db)
    answer(db, uid, "os-cs-2", True, days_ago=10)
    answer(db, uid, "os-cs-4", True, days_ago=10)
    recs = _recs(db, uid, diagnostic_status="completed")
    revisit = [r for r in recs if r.action == "revisit_neglected"]
    assert revisit and "10 days" in revisit[0].reason


def test_timetable_class_tomorrow_produces_preparation(db):
    uid = seeded(db)
    answer(db, uid, "os-cs-2", False)
    timetable = [
        {"id": 1, "day_of_week": 3, "start_time": "09:00", "subject_id": "operating-systems", "room": "B-204"}
    ]
    recs = _recs(db, uid, diagnostic_status="completed", timetable=timetable)
    prep = [r for r in recs if r.action == "prepare_for_class"]
    assert prep and prep[0].subject_id == "operating-systems"
    assert "tomorrow at 09:00" in prep[0].reason
    assert prep[0].evidence[0].startswith("Operating Systems class tomorrow at 09:00 in B-204")


def test_class_in_subject_without_question_bank_is_not_invented(db):
    """Only subjects with a question bank can be prepared for; a class beyond
    the horizon or without a bank yields no preparation recommendation."""
    uid = seeded(db)
    far = [
        {"id": 2, "day_of_week": 1, "start_time": "09:00", "subject_id": "operating-systems"}
    ]  # Tue: 6 days
    assert not [
        r
        for r in _recs(db, uid, diagnostic_status="completed", timetable=far)
        if r.action == "prepare_for_class"
    ]
    from skillforge.teacher import curriculum

    original = curriculum.assessable_in_subject
    curriculum.assessable_in_subject = lambda sid: [] if sid == "gender-sensitization" else original(sid)
    try:
        cls = recommend.upcoming_classes(
            [{"day_of_week": 3, "start_time": "09:00", "subject_id": "gender-sensitization"}], NOW
        )[0]
        with db.session() as s:
            assert recommend.prepare_for_class(learner_state.build(s, uid), cls) is None
    finally:
        curriculum.assessable_in_subject = original


def test_upcoming_classes_next_occurrence():
    tt = [
        {"day_of_week": 2, "start_time": "09:00", "subject_id": "x"},  # Wed 09:00 already passed
        {"day_of_week": 2, "start_time": "14:00", "subject_id": "y"},
    ]  # later today
    up = recommend.upcoming_classes(tt, NOW)
    assert [c["subject_id"] for c in up] == ["y"]
    assert up[0]["when"] == "today at 14:00" and up[0]["hours_until"] == 4.0


def test_active_session_is_continued_first(db):
    uid = seeded(db)
    active = {
        "id": 7,
        "topic_id": "os-deadlock",
        "topic_title": "Deadlock",
        "subject_name": "OS",
        "question_number": 3,
        "max_questions": 5,
    }
    recs = _recs(db, uid, diagnostic_status="completed", active_session=active)
    assert recs[0].action == "continue_session" and recs[0].cta == {"kind": "resume", "session_id": 7}


def test_every_recommendation_is_explained(db):
    uid = seeded(db)
    for qid, ok in [
        ("dt-1", True),
        ("dt-3", False),
        ("dt-6", False),
        ("os-cs-2", True),
        ("lr-1", True),
        ("lr-2", True),
        ("xai-ph-1", True),
    ]:
        answer(db, uid, qid, ok, days_ago=1)
    for r in _recs(db, uid, diagnostic_status="completed"):
        d = r.to_dict()
        assert d["reason"] and d["action"] and 0 < d["priority"] <= 1 and d["estimated_minutes"] > 0
        assert d["cta"]["kind"] in ("session", "resume", "diagnostic", "flashcards", "rapid_round")


def test_no_duplicate_topic_recommendations(db):
    uid = seeded(db)
    for qid, ok in [("dt-1", False), ("dt-2", False), ("dt-3", False), ("dt-4", False)]:
        answer(db, uid, qid, ok)
    topics = [r.topic_id for r in _recs(db, uid, diagnostic_status="completed") if r.concept_id]
    assert len(topics) == len(set(topics))


def test_upcoming_horizon_is_48_hours():
    tt = [{"day_of_week": (NOW.weekday() + 3) % 7, "start_time": "09:00", "subject_id": "x"}]
    assert recommend.upcoming_classes(tt, NOW) == []
    assert recommend.upcoming_classes(tt, NOW, horizon_hours=24 * 7)[0]["subject_id"] == "x"
    assert timedelta(hours=48) == timedelta(hours=recommend.CLASS_HORIZON_HOURS)
