"""The VNR curriculum: required subjects, structure, seeding and DB round-trip."""

from __future__ import annotations

import copy

from sqlalchemy import func, select

from skillforge.db.migrations import MIGRATIONS, current_version, upgrade
from skillforge.db.models import Concept, Question, Subject, Topic
from skillforge.teacher.content import SUBJECTS
from skillforge.teacher.seed import read_curriculum, seed_curriculum

V_SEMESTER = [
    ("22PC1IN202", "Computer Networks"),
    ("22PC1AM301", "Artificial Intelligence"),
    ("22PC1IT202", "Operating Systems"),
    ("22PC1AM302", "Machine Learning"),
    ("22PE1AM302", "Explainable AI"),
    ("22PC2AM322", "Computer Networks and Operating Systems Laboratory"),
    ("22PC2AM302", "Machine Learning Laboratory"),
    ("22MN6HS302", "Gender Sensitization"),
]


VNR = [s for s in SUBJECTS if s["area"] == "vnr-aiml-r22"]


def test_exactly_the_eight_v_semester_subjects():
    # The VNR syllabus area keeps exactly its eight courses; other areas
    # (DSA foundations) are separate and never mixed into it.
    assert [(s["code"], s["name"]) for s in VNR] == V_SEMESTER
    assert [(s["id"], s["area"], s["kind"]) for s in SUBJECTS if s not in VNR] == [
        ("dsa", "foundations", "foundation")
    ]
    names = {s["name"] for s in VNR}
    for excluded in (
        "Data Mining",
        "Web Programming",
        "Software Testing Methodologies",
        "Mobile Application Development",
    ):
        assert excluded not in names


def test_every_subject_has_units_topics_and_a_question_bank():
    for s in SUBJECTS:
        topics = [t for u in s["units"] for t in u["topics"]]
        assert len(topics) >= 3, s["id"]
        assert any(t["questions"] for t in topics), s["id"]
        if s["kind"] == "theory":
            assert len(s["units"]) == 5, s["id"]


def test_syllabus_units_follow_the_pdf():
    ml = next(s for s in SUBJECTS if s["id"] == "machine-learning")
    assert [u["title"] for u in ml["units"]] == [
        "Introduction to Machine Learning and Pre-requisites",
        "Supervised Learning – I",
        "Supervised Learning – II",
        "Unsupervised Learning",
        "Ensemble Learning",
    ]
    lab = next(s for s in SUBJECTS if s["id"] == "cn-os-lab")
    assert [u["title"] for u in lab["units"]] == ["Computer Networks Programs", "Operating Systems Programs"]
    gs = next(s for s in SUBJECTS if s["id"] == "gender-sensitization")
    assert gs["unit_label"] == "Module" and len(gs["units"]) == 5


def test_seed_is_idempotent_and_relational(db):
    first = seed_curriculum(db)
    second = seed_curriculum(db)
    assert first == second and first["subjects"] == len(SUBJECTS) == 9
    with db.session() as s:
        assert s.scalar(select(func.count(Subject.id))) == 9
        assert s.scalar(select(func.count(Subject.id)).where(Subject.area == "vnr-aiml-r22")) == 8
        assert s.scalar(select(func.count(Topic.id))) == first["topics"]
        # Every question belongs to a concept of its own topic.
        for q in s.scalars(select(Question)):
            concept = s.get(Concept, q.concept_id)
            assert concept is not None and concept.topic_id == q.topic_id
            assert 0 <= q.answer_index < len(q.options_json)


def test_database_round_trip_matches_seed_content(db):
    seed_curriculum(db)
    from_db = read_curriculum(db)
    expected = copy.deepcopy(SUBJECTS)
    assert from_db == expected


def test_migrations_are_versioned_and_idempotent(db):
    assert current_version(db.engine) == MIGRATIONS[-1][0] == 3
    assert upgrade(db.engine) == []


def test_v3_migration_adds_areas_and_resources_and_is_rerunnable(db):
    """A database migrated to v2 gains the curriculum-area and resources
    columns; existing subjects default to the VNR area."""
    from sqlalchemy import inspect, text

    from skillforge.db.models import SchemaMigration

    seed_curriculum(db)
    with db.engine.begin() as conn:
        conn.execute(SchemaMigration.__table__.delete().where(SchemaMigration.version == 3))
    assert upgrade(db.engine) == [3]
    cols = {c["name"] for c in inspect(db.engine).get_columns("subjects")}
    assert "area" in cols
    assert "resources_json" in {c["name"] for c in inspect(db.engine).get_columns("topics")}
    with db.engine.connect() as conn:
        areas = dict(conn.execute(text("SELECT id, area FROM subjects")).all())
    assert areas["machine-learning"] == "vnr-aiml-r22" and areas["dsa"] == "foundations"


def test_resources_round_trip_and_are_curated(db):
    seed_curriculum(db)
    topics = {t["id"]: t for s in read_curriculum(db) for u in s["units"] for t in u["topics"]}
    assert topics["decision-trees"]["resources"][0]["url"].startswith("https://scikit-learn.org/")
    assert topics["gs-definition"]["resources"] == []  # no trustworthy match: none invented


def test_v2_migration_backfills_evidence_and_is_rerunnable(db):
    """Simulate a database last migrated at v1 that already has session
    answers: re-running v2 must not fail on existing columns and must copy
    the answers into the evidence log."""
    from sqlalchemy import text

    from skillforge.db.models import SchemaMigration

    seed_curriculum(db)
    with db.engine.begin() as conn:
        conn.execute(
            text("INSERT INTO users (id, email, name, password_hash) VALUES (1, 'a@x.io', 'A', 'h')")
        )
        conn.execute(
            text(
                "INSERT INTO learning_sessions (id, user_id, topic_id, status, state_json, mastery, "
                "answered_count, correct_count) VALUES (1, 1, 'decision-trees', 'active', '{}', 0, 1, 1)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO answers (session_id, user_id, question_id, concept_id, number, choice, correct, "
                "verdict, difficulty, mastery_after) VALUES (1, 1, 'dt-1', "
                "'decision-trees/splitting-criteria', 1, 1, 1, 'correct', 1, 0.15)"
            )
        )
        conn.execute(SchemaMigration.__table__.delete().where(SchemaMigration.version == 2))
    assert upgrade(db.engine) == [2]
    with db.engine.connect() as conn:
        rows = conn.execute(text("SELECT source, ref_id, correct, weight FROM evidence_events")).all()
    assert rows == [("session", 1, 1, 1.0)]
