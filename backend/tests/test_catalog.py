"""Public endpoints used by the signed-out landing page."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from skillforge.api.health import API_VERSION
from skillforge.teacher import curriculum


def test_curriculum_outline_is_public_and_matches_content(app):
    r = TestClient(app).get("/api/curriculum")
    assert r.status_code == 200
    body = r.json()
    assert [s["id"] for s in body["subjects"]] == [s["id"] for s in curriculum.subjects()]
    areas = {a["id"]: a for a in body["areas"]}
    # The VNR syllabus keeps its eight courses; DSA is a separate area.
    assert areas["vnr-aiml-r22"]["subjects"] == 8
    assert areas["foundations"]["subjects"] == 1
    assert {s["area"] for s in body["subjects"] if s["id"] == "dsa"} == {"foundations"}
    assert body["topic_count"] == sum(s["topic_count"] for s in body["subjects"])
    assert body["topic_count"] == len(curriculum.topic_ids(assessable_only=False))
    assert body["assessable_topics"] == len(curriculum.topic_ids())
    ml = next(s for s in body["subjects"] if s["id"] == "machine-learning")
    assert ml["units"][0]["number"] == 1
    assert all(isinstance(t, str) for u in ml["units"] for t in u["topics"])


def test_curriculum_outline_has_no_semester_branding_or_answers(app):
    raw = json.dumps(TestClient(app).get("/api/curriculum").json())
    assert "semester" not in raw.lower()
    for leaked in ('"questions"', '"options"', '"answer"', '"explanation"', '"concepts"', '"prompt"'):
        assert leaked not in raw
    for tid in curriculum.topic_ids():
        _, topic = curriculum.get_topic(tid)
        for q in topic["questions"][:3]:
            assert q["prompt"] not in raw


def test_health_names_api_generation_and_features(app):
    body = TestClient(app).get("/api/health").json()
    assert body["api_version"] == API_VERSION
    assert {"accounts", "curriculum", "learner", "review"} <= set(body["features"])
