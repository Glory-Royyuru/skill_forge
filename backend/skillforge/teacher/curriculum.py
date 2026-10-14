"""The Teacher Agent's curriculum registry.

Shape: subject → units → topics → concepts → questions (the VNR R22 AIML
V Semester syllabus; see `skillforge.teacher.content`). Each topic dict is
exactly what the engine consumes: `lesson`, `concepts` (key → name/reteach)
and `questions` (with answer keys).

At application start the registry is loaded from the database
(`skillforge.teacher.seed.load_curriculum`), which is the runtime source of
truth. Code that runs without a database (unit tests, scripts) gets the
same data built straight from the seed content.

Answers and explanations only leave the backend through `public_question`
(which strips them) or after the student has answered.
"""

from __future__ import annotations

from typing import Any

LEVEL_NAMES = {1: "Foundational", 2: "Intermediate", 3: "Advanced"}

_registry: dict[str, Any] | None = None


def concept_id(topic_id: str, key: str) -> str:
    """Global id of a topic-scoped concept (used in the database)."""
    return f"{topic_id}/{key}"


def set_subjects(subjects: list[dict]) -> None:
    """Install a curriculum (subjects → units → topics)."""
    global _registry
    topics: dict[str, tuple[dict, dict]] = {}
    questions: dict[str, tuple[dict, dict, dict]] = {}
    for s in subjects:
        for u in s["units"]:
            for t in u["topics"]:
                t["subject_id"] = s["id"]
                t["unit_number"] = u["number"]
                t["unit_title"] = u["title"]
                topics[t["id"]] = (s, t)
                for q in t["questions"]:
                    questions[q["id"]] = (s, t, q)
    _registry = {"subjects": subjects, "topics": topics, "questions": questions}


def _reg() -> dict[str, Any]:
    if _registry is None:
        import copy

        from skillforge.teacher.content import SUBJECTS

        set_subjects(copy.deepcopy(SUBJECTS))
    return _registry


def subjects() -> list[dict]:
    return _reg()["subjects"]


def is_servable(question: dict) -> bool:
    """Active and not retired. Draft questions may be served in Teacher
    sessions but are excluded from analytics and from the diagnostic/Rapid Round."""
    return question.get("active", True) and question.get("quality", "reviewed") != "retired"


def is_reviewed(question: dict) -> bool:
    return is_servable(question) and question.get("quality", "reviewed") == "reviewed"


def is_assessable(topic: dict) -> bool:
    return any(is_servable(q) for q in topic["questions"])


def find_question(question_id: str) -> tuple[dict, dict, dict] | None:
    """(subject, topic, question) for a question id, or None."""
    return _reg()["questions"].get(question_id)


def get_topic(topic_id: str) -> tuple[dict, dict] | None:
    """Return (subject, topic) for a topic id, or None."""
    return _reg()["topics"].get(topic_id)


def get_question(topic_id: str, question_id: str) -> dict | None:
    found = get_topic(topic_id)
    if found is None:
        return None
    return next((q for q in found[1]["questions"] if q["id"] == question_id), None)


def topic_ids(assessable_only: bool = True) -> list[str]:
    """Topic ids in curriculum order (by default only topics that have a
    question bank, i.e. that can start a teaching session)."""
    return [
        tid for tid, (_, t) in _reg()["topics"].items() if not assessable_only or is_assessable(t)
    ]


def assessable_in_subject(subject_id: str) -> list[str]:
    return [tid for tid, (s, t) in _reg()["topics"].items() if s["id"] == subject_id and is_assessable(t)]


def concept_name(topic_id: str, concept: str) -> str:
    found = get_topic(topic_id)
    if found is None:
        return concept
    return found[1]["concepts"].get(concept, {}).get("name", concept)


def public_question(topic: dict, question: dict) -> dict:
    """A question as the student sees it: no answer key, no explanation."""
    return {
        "id": question["id"],
        "prompt": question["prompt"],
        "options": list(question["options"]),
        "difficulty": question["difficulty"],
        "difficulty_label": LEVEL_NAMES[question["difficulty"]],
        "concept": question["concept"],
        "concept_name": topic["concepts"][question["concept"]]["name"],
        "cognitive_type": question.get("cognitive_type"),
    }


def public_topic(subject: dict, topic: dict) -> dict:
    return {
        "id": topic["id"],
        "title": topic["title"],
        "summary": topic["summary"],
        "level": topic["level"],
        "subject_id": subject["id"],
        "subject_name": subject["name"],
        "unit_number": topic["unit_number"],
        "unit_title": topic["unit_title"],
        "assessable": is_assessable(topic),
        "question_count": len(topic["questions"]),
        "concepts": [c["name"] for c in topic["concepts"].values()],
        "resources": resources_for(topic),
    }


def resources_for(topic: dict, concept: str | None = None) -> list[dict]:
    """Curated further reading: links aimed at `concept` first, then the
    topic-wide ones. Never invented; empty when none were curated."""
    items = topic.get("resources") or []
    specific = [r for r in items if concept and concept in r.get("concepts", [])]
    general = [r for r in items if not r.get("concepts")]
    chosen = (specific + general) if concept else items
    return [{k: r[k] for k in ("title", "url", "publisher")} for r in chosen]


def public_curriculum() -> list[dict]:
    """The curriculum for browsing: units, topics and concept names; no questions."""
    return [
        {
            "id": s["id"],
            "code": s["code"],
            "name": s["name"],
            "short_name": s["short_name"],
            "kind": s["kind"],
            "area": s.get("area", "vnr-aiml-r22"),
            "description": s["description"],
            "unit_label": s["unit_label"],
            "units": [
                {
                    "number": u["number"],
                    "title": u["title"],
                    "topics": [public_topic(s, t) for t in u["topics"]],
                }
                for u in s["units"]
            ],
        }
        for s in subjects()
    ]
