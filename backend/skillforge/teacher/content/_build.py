"""Small constructors that keep the curriculum content files readable.

Every curriculum module builds plain dicts with these helpers; the shape is
exactly what `skillforge.teacher.engine` consumes (topic → lesson, concepts,
questions) plus the syllabus hierarchy (subject → units → topics).
"""

from __future__ import annotations

from typing import Any


def question(
    qid: str,
    difficulty: int,
    concept: str,
    prompt: str,
    options: list[str],
    answer: int,
    explanation: str,
    why_wrong: dict[int, str] | None = None,
) -> dict[str, Any]:
    assert difficulty in (1, 2, 3), qid
    assert 0 <= answer < len(options), qid
    q: dict[str, Any] = {
        "id": qid,
        "difficulty": difficulty,
        "concept": concept,
        "prompt": prompt,
        "options": options,
        "answer": answer,
        "explanation": explanation,
    }
    if why_wrong:
        q["why_wrong"] = why_wrong
    return q


def topic(
    tid: str,
    title: str,
    summary: str,
    level: str = "Intermediate",
    lesson: dict | None = None,
    concepts: dict[str, dict] | None = None,
    questions: list[dict] | None = None,
) -> dict[str, Any]:
    """A syllabus topic. Topics without `questions` are listed in the
    curriculum but cannot start a teaching session yet."""
    t: dict[str, Any] = {
        "id": tid,
        "title": title,
        "summary": summary,
        "level": level,
        "lesson": lesson,
        "concepts": concepts or {},
        "questions": questions or [],
    }
    for q in t["questions"]:
        assert q["concept"] in t["concepts"], (tid, q["id"])
    return t


def lesson(intro: str, body: list[str], key_points: list[str]) -> dict[str, Any]:
    return {"intro": intro, "body": body, "key_points": key_points}


def concept(name: str, reteach: str) -> dict[str, str]:
    return {"name": name, "reteach": reteach}


def unit(number: int, title: str, topics: list[dict]) -> dict[str, Any]:
    return {"number": number, "title": title, "topics": topics}


def subject(
    sid: str,
    code: str,
    name: str,
    short_name: str,
    kind: str,
    description: str,
    units: list[dict],
    unit_label: str = "Unit",
    area: str = "vnr-aiml-r22",
) -> dict[str, Any]:
    """`area` groups subjects into curricula: the VNR R22 AIML syllabus, or
    general foundations such as DSA, which belong to no institution."""
    assert kind in ("theory", "laboratory", "mandatory", "foundation"), sid
    assert area in AREAS, sid
    return {
        "id": sid,
        "code": code,
        "name": name,
        "short_name": short_name,
        "kind": kind,
        "description": description,
        "unit_label": unit_label,
        "area": area,
        "units": units,
    }


# Curriculum areas available in SkillForge.
AREAS = {
    "vnr-aiml-r22": "VNR VJIET · B.Tech. CSE (AI & ML) · R22",
    "foundations": "Foundations",
}
