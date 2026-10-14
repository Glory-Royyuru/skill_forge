"""Seed the curriculum into the database and load it back.

`seed_curriculum` upserts every subject, unit, topic, concept and question
from `skillforge.teacher.content` (primary keys are stable slugs, so running
it repeatedly is safe). It never deletes: retiring content that students
have answered must be done deliberately in a migration.

`load_curriculum` reads the database back into the registry the Teacher
engine uses, so at runtime the database is the source of truth.
"""

from __future__ import annotations

from sqlalchemy import select

from skillforge.db.database import Database
from skillforge.db.models import Concept, Question, Subject, Topic, Unit
from skillforge.teacher import curriculum
from skillforge.teacher.content import SUBJECTS


def seed_curriculum(db: Database, subjects: list[dict] | None = None) -> dict[str, int]:
    subjects = subjects if subjects is not None else SUBJECTS
    counts = {"subjects": 0, "units": 0, "topics": 0, "concepts": 0, "questions": 0}
    with db.session() as session:
        for s_pos, s in enumerate(subjects):
            session.merge(Subject(
                id=s["id"], code=s["code"], name=s["name"], short_name=s["short_name"], kind=s["kind"],
                description=s["description"], unit_label=s["unit_label"], position=s_pos,
                area=s.get("area", "vnr-aiml-r22"),
            ))
            counts["subjects"] += 1
            t_pos = 0
            for u in s["units"]:
                unit_id = f"{s['id']}:{u['number']}"
                session.merge(Unit(id=unit_id, subject_id=s["id"], number=u["number"], title=u["title"]))
                counts["units"] += 1
                for t in u["topics"]:
                    session.merge(Topic(
                        id=t["id"], subject_id=s["id"], unit_id=unit_id, title=t["title"],
                        summary=t["summary"], level=t["level"], position=t_pos, lesson_json=t["lesson"],
                        resources_json=t.get("resources") or None,
                    ))
                    t_pos += 1
                    counts["topics"] += 1
                    for c_pos, (key, c) in enumerate(t["concepts"].items()):
                        session.merge(Concept(
                            id=curriculum.concept_id(t["id"], key), topic_id=t["id"], key=key,
                            name=c["name"], reteach=c["reteach"], position=c_pos,
                        ))
                        counts["concepts"] += 1
                    for q_pos, q in enumerate(t["questions"]):
                        session.merge(Question(
                            id=q["id"], topic_id=t["id"],
                            concept_id=curriculum.concept_id(t["id"], q["concept"]),
                            difficulty=q["difficulty"], prompt=q["prompt"], options_json=list(q["options"]),
                            answer_index=q["answer"], explanation=q["explanation"],
                            why_wrong_json={str(k): v for k, v in q.get("why_wrong", {}).items()} or None,
                            position=q_pos, cognitive_type=q.get("cognitive_type"),
                            quality=q.get("quality", "reviewed"), active=q.get("active", True),
                            source=q.get("source"),
                        ))
                        counts["questions"] += 1
        session.commit()
    return counts


def read_curriculum(db: Database) -> list[dict]:
    """The curriculum as stored in the database, in the engine's dict shape."""
    with db.session() as session:
        subjects = session.scalars(select(Subject).order_by(Subject.position)).all()
        units = session.scalars(select(Unit).order_by(Unit.subject_id, Unit.number)).all()
        topics = session.scalars(select(Topic).order_by(Topic.position)).all()
        concepts = session.scalars(select(Concept).order_by(Concept.position)).all()
        questions = session.scalars(select(Question).order_by(Question.position)).all()

        concepts_by_topic: dict[str, dict] = {}
        for c in concepts:
            concepts_by_topic.setdefault(c.topic_id, {})[c.key] = {"name": c.name, "reteach": c.reteach}
        key_of = {c.id: c.key for c in concepts}
        questions_by_topic: dict[str, list] = {}
        for q in questions:
            item = {
                "id": q.id, "difficulty": q.difficulty, "concept": key_of[q.concept_id], "prompt": q.prompt,
                "options": list(q.options_json), "answer": q.answer_index, "explanation": q.explanation,
                "cognitive_type": q.cognitive_type, "quality": q.quality, "active": q.active,
                "source": q.source,
            }
            if q.why_wrong_json:
                item["why_wrong"] = {int(k): v for k, v in q.why_wrong_json.items()}
            questions_by_topic.setdefault(q.topic_id, []).append(item)

        topics_by_unit: dict[str, list] = {}
        for t in topics:
            topics_by_unit.setdefault(t.unit_id, []).append({
                "id": t.id, "title": t.title, "summary": t.summary, "level": t.level,
                "lesson": t.lesson_json, "concepts": concepts_by_topic.get(t.id, {}),
                "resources": list(t.resources_json or []),
                "questions": questions_by_topic.get(t.id, []),
            })
        units_by_subject: dict[str, list] = {}
        for u in units:
            units_by_subject.setdefault(u.subject_id, []).append(
                {"number": u.number, "title": u.title, "topics": topics_by_unit.get(u.id, [])}
            )
        return [
            {
                "id": s.id, "code": s.code, "name": s.name, "short_name": s.short_name, "kind": s.kind,
                "description": s.description, "unit_label": s.unit_label, "area": s.area,
                "units": units_by_subject.get(s.id, []),
            }
            for s in subjects
        ]


def load_curriculum(db: Database) -> None:
    curriculum.set_subjects(read_curriculum(db))
