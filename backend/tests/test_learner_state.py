"""Learner state: BKT persistence, evidence aggregation and status rules."""

from __future__ import annotations

from sqlalchemy import select

from skillforge.db.models import LearnerConcept
from skillforge.learner import state as learner_state
from skillforge.learner.state import classify
from tests.learner_helpers import answer, seeded

SPLIT = "decision-trees/splitting-criteria"


def _state(db, uid):
    with db.session() as s:
        return learner_state.build(s, uid)


def test_fresh_student_has_no_evidence_and_no_mastery(db):
    uid = seeded(db)
    st = _state(db, uid)
    assert not st.has_evidence()
    overall = st.overall()
    assert overall["estimate"] is None and overall["assessed"] == 0 and overall["mastered"] == 0
    assert all(c.status == "not_started" for c in st.concepts.values())


def test_evidence_updates_persistent_bkt(db):
    uid = seeded(db)
    answer(db, uid, "dt-1", True)
    with db.session() as s:
        lc = s.scalar(select(LearnerConcept).where(LearnerConcept.concept_id == SPLIT))
    assert lc.p_known > 0.3 and lc.attempts == 1 and lc.correct == 1


def test_one_correct_answer_is_not_mastery(db):
    uid = seeded(db)
    answer(db, uid, "dt-6", True)  # Advanced, correct
    c = _state(db, uid).concepts[SPLIT]
    assert c.status == "learning" and c.confidence == "low"


def test_mastery_needs_several_answers_including_harder_ones(db):
    uid = seeded(db)
    for qid in ("dt-1", "dt-3", "dt-6"):
        answer(db, uid, qid, True)
    c = _state(db, uid).concepts[SPLIT]
    assert c.p_known >= 0.85 and c.status == "mastered"
    assert c.by_difficulty[1] == [1, 1] and c.by_difficulty[3] == [1, 1]


def test_one_wrong_answer_is_not_needs_review(db):
    uid = seeded(db)
    answer(db, uid, "dt-1", True)
    answer(db, uid, "dt-3", False)
    assert _state(db, uid).concepts[SPLIT].status == "learning"


def test_repeated_mistakes_flag_needs_review(db):
    uid = seeded(db)
    answer(db, uid, "dt-1", True)
    answer(db, uid, "dt-3", False)
    answer(db, uid, "dt-6", False)
    c = _state(db, uid).concepts[SPLIT]
    assert c.consecutive_incorrect == 2 and c.recent == [True, False, False]
    assert c.status == "needs_review"
    assert any("2 incorrect answers in a row" in line for line in c.evidence_lines())


def test_recent_accuracy_window_and_cognitive_breakdown(db):
    uid = seeded(db)
    for qid, ok in [
        ("dt-1", False),
        ("dt-3", False),
        ("dt-6", True),
        ("dt-1", True),
        ("dt-3", True),
        ("dt-6", True),
        ("dt-1", True),
    ]:
        answer(db, uid, qid, ok)
    c = _state(db, uid).concepts[SPLIT]
    assert len(c.recent) == learner_state.RECENT_WINDOW
    assert c.recent_accuracy == 5 / 6
    assert c.by_cognitive["recall"] == [3, 2]  # dt-1 is a recall question


def test_recency_is_tracked(db):
    uid = seeded(db)
    answer(db, uid, "dt-1", True, days_ago=9)
    c = _state(db, uid).concepts[SPLIT]
    assert c.days_since == 9
    assert any("Last practised 9 days ago" in line for line in c.evidence_lines())


def test_response_time_is_secondary(db):
    """Slow-but-correct and fast-but-correct produce the same estimate."""
    uid = seeded(db)
    answer(db, uid, "dt-1", True, response_ms=40_000)
    slow = _state(db, uid).concepts[SPLIT]
    uid2 = _second_user(db)
    answer(db, uid2, "dt-1", True, response_ms=2_000)
    fast = _state(db, uid2).concepts[SPLIT]
    assert slow.p_known == fast.p_known and slow.status == fast.status
    assert slow.median_response_ms == 40_000


def _second_user(db) -> int:
    from skillforge.db.models import User
    from skillforge.learner.evidence import utcnow

    with db.session() as s:
        u = User(email="u2@example.com", name="Other", password_hash="x", email_verified_at=utcnow())
        s.add(u)
        s.commit()
        return u.id


def test_rapid_round_evidence_counts_less(db):
    uid = seeded(db)
    answer(db, uid, "dt-1", True, source="session")
    uid2 = _second_user(db)
    answer(db, uid2, "dt-1", True, source="rapid_round")
    session_p = _state(db, uid).concepts[SPLIT].p_known
    rapid_p = _state(db, uid2).concepts[SPLIT].p_known
    assert 0.3 < rapid_p < session_p
    assert _state(db, uid2).concepts[SPLIT].weight == 0.5


def test_draft_questions_do_not_count_in_analytics(db):
    from sqlalchemy import update

    from skillforge.db.models import Question

    uid = seeded(db)
    with db.session() as s:
        s.execute(update(Question).where(Question.id == "dt-1").values(quality="draft"))
        s.commit()
    answer(db, uid, "dt-1", True)
    assert _state(db, uid).concepts[SPLIT].attempts == 0


def test_topic_aggregate_reports_coverage(db):
    uid = seeded(db)
    for qid in ("dt-1", "dt-3", "dt-6"):
        answer(db, uid, qid, True)
    summary = _state(db, uid).topic_summary("decision-trees")
    assert summary["assessed"] == 1 and summary["total"] == 3
    assert abs(summary["coverage"] - 1 / 3) < 1e-9
    assert summary["status"] == "in_progress"  # one mastered concept is not a mastered topic


def test_classify_is_pure_rules():
    c = learner_state.ConceptState(
        id="x/y",
        key="y",
        name="Y",
        topic_id="x",
        topic_title="X",
        subject_id="s",
        subject_name="S",
        unit_number=1,
        unit_title="U",
    )
    assert classify(c) == "not_started"
