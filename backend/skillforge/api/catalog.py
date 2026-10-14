"""GET /api/curriculum — the public outline of every curriculum area.

Exposes only what a printed syllabus would: area, subject codes and names,
unit titles and topic titles, plus how many topics currently have a question
bank. No questions, answers, concepts or student data.
"""

from __future__ import annotations

from fastapi import APIRouter

from skillforge.teacher import curriculum
from skillforge.teacher.content._build import AREAS

router = APIRouter()


@router.get("/curriculum")
def curriculum_outline() -> dict:
    subjects = []
    for s in curriculum.subjects():
        topics = [t for u in s["units"] for t in u["topics"]]
        subjects.append(
            {
                "id": s["id"],
                "area": s.get("area", "vnr-aiml-r22"),
                "code": s["code"],
                "name": s["name"],
                "short_name": s["short_name"],
                "kind": s["kind"],
                "unit_label": s["unit_label"],
                "units": [
                    {"number": u["number"], "title": u["title"], "topics": [t["title"] for t in u["topics"]]}
                    for u in s["units"]
                ],
                "topic_count": len(topics),
                "assessable_topics": sum(1 for t in topics if curriculum.is_assessable(t)),
            }
        )
    areas = []
    for key, label in AREAS.items():
        members = [s for s in subjects if s["area"] == key]
        if members:
            areas.append(
                {
                    "id": key,
                    "label": label,
                    "subjects": len(members),
                    "topic_count": sum(s["topic_count"] for s in members),
                    "assessable_topics": sum(s["assessable_topics"] for s in members),
                }
            )
    return {
        "areas": areas,
        "subjects": subjects,
        "topic_count": sum(s["topic_count"] for s in subjects),
        "assessable_topics": sum(s["assessable_topics"] for s in subjects),
    }
