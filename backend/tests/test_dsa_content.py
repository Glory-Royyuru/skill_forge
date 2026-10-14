"""DSA foundations: structure and question quality, under the same rules as
the VNR banks."""

from __future__ import annotations

from collections import Counter

from skillforge.teacher.content import SUBJECTS
from skillforge.teacher.content.question_meta import COGNITIVE_TYPES
from skillforge.teacher.content.resources import ALLOWED_HOSTS, RESOURCES

DSA = next(s for s in SUBJECTS if s["id"] == "dsa")
TOPICS = [t for u in DSA["units"] for t in u["topics"]]
BANKED = [t for t in TOPICS if t["questions"]]


def test_dsa_is_a_separate_foundations_area_without_semester_branding():
    assert DSA["area"] == "foundations" and DSA["kind"] == "foundation"
    text = " ".join([DSA["name"], DSA["description"], *(u["title"] for u in DSA["units"])]).lower()
    assert "semester" not in text and "vnr" not in text
    assert [u["title"] for u in DSA["units"]] == [
        "Complexity", "Arrays & Strings", "Linked Lists", "Stacks & Queues", "Hashing",
        "Searching & Sorting", "Recursion", "Trees", "Heaps", "Graphs", "Dynamic Programming",
    ]


def test_every_banked_topic_has_a_full_lesson_and_balanced_levels():
    assert len(BANKED) == 12
    for t in BANKED:
        assert t["lesson"]["intro"] and len(t["lesson"]["body"]) >= 2 and len(t["lesson"]["key_points"]) >= 3
        assert Counter(q["difficulty"] for q in t["questions"]) == {1: 2, 2: 2, 3: 2}, t["id"]
        # Every concept is assessed and every concept has a key idea to re-teach.
        assert {q["concept"] for q in t["questions"]} == set(t["concepts"]), t["id"]
        assert all(len(c["reteach"]) > 40 for c in t["concepts"].values())


def test_every_question_carries_quality_metadata_and_a_real_explanation():
    ids, prompts = [], []
    for t in BANKED:
        for q in t["questions"]:
            ids.append(q["id"])
            prompts.append(q["prompt"])
            assert q["cognitive_type"] in COGNITIVE_TYPES
            assert q["quality"] == "reviewed" and q["active"] is True
            assert q["source"] == "SkillForge question bank, DSA foundations"
            assert 0 <= q["answer"] < len(q["options"]) == 4
            assert len(set(q["options"])) == 4, q["id"]
            assert len(q["explanation"]) > 40, q["id"]
            for k in q.get("why_wrong", {}):
                assert k != q["answer"], q["id"]  # why-wrong never targets the right answer
    assert len(ids) == len(set(ids)) == 72
    assert len(prompts) == len(set(prompts))
    # Several cognitive types are represented, not just recall.
    assert {q["cognitive_type"] for t in BANKED for q in t["questions"]} == set(COGNITIVE_TYPES)


def test_resources_are_https_on_allowlisted_hosts_and_target_real_concepts():
    by_id = {t["id"]: t for s in SUBJECTS for u in s["units"] for t in u["topics"]}
    for tid, items in RESOURCES.items():
        for r in items:
            assert r["url"].startswith("https://") and r["url"].split("/")[2] in ALLOWED_HOSTS
            assert r["title"] and r["publisher"]
            for c in r.get("concepts", []):
                assert c in by_id[tid]["concepts"]
    # Every banked DSA topic has at least one curated reference.
    assert all(by_id[t["id"]]["resources"] for t in BANKED)
