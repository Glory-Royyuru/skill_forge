from __future__ import annotations

import pytest

from skillforge.teacher import engine
from skillforge.teacher.curriculum import get_question, get_topic, public_question, subjects, topic_ids


def _answer(state: dict, correct: bool) -> dict:
    q = get_question(state["topic_id"], state["current_question_id"])
    choice = q["answer"] if correct else (q["answer"] + 1) % len(q["options"])
    return engine.submit_answer(state, q["id"], choice)


def _run(topic_id: str, pattern: list[bool], prior: float | None = None) -> tuple[dict, list[dict]]:
    state = engine.start_session(topic_id, prior_mastery=prior)
    feedback = [_answer(state, ok) for ok in pattern]
    return state, feedback


# --- Curriculum ----------------------------------------------------------------


def test_assessable_topics_are_complete_question_banks():
    assessable = topic_ids()
    assert len(assessable) >= 8
    for tid in assessable:
        _, t = get_topic(tid)
        assert t["lesson"]["intro"] and t["lesson"]["key_points"]
        assert len(t["concepts"]) >= 2
        assert len(t["questions"]) == 6
        for level in (1, 2, 3):
            assert sum(q["difficulty"] == level for q in t["questions"]) == 2
        for q in t["questions"]:
            assert len(q["options"]) == 4
            assert len(set(q["options"])) == 4
            assert 0 <= q["answer"] < 4
            assert q["concept"] in t["concepts"]
            assert q["explanation"]
            for k in q.get("why_wrong", {}):
                assert k != q["answer"] and 0 <= k < 4


def test_question_and_topic_ids_unique():
    topics = [t for s in subjects() for u in s["units"] for t in u["topics"]]
    assert len({t["id"] for t in topics}) == len(topics)
    ids = [q["id"] for t in topics for q in t["questions"]]
    assert len(ids) == len(set(ids))


def test_public_question_hides_answer_key():
    _, topic = get_topic("decision-trees")
    pq = public_question(topic, topic["questions"][0])
    assert "answer" not in pq and "explanation" not in pq


# --- DIAGNOSE ----------------------------------------------------------------


def test_new_student_starts_foundational():
    state = engine.start_session("decision-trees")
    assert state["level"] == 1
    assert state["log"][0]["stage"] == "diagnose"
    view = engine.session_view(state)
    assert view["current_question"]["difficulty"] == 1
    assert "answer" not in view["current_question"]


def test_strong_prior_mastery_starts_intermediate():
    state = engine.start_session("decision-trees", prior_mastery=0.9)
    assert state["level"] == 2
    assert get_question("decision-trees", state["current_question_id"])["difficulty"] == 2


def test_unknown_topic_rejected():
    with pytest.raises(engine.TeacherError):
        engine.start_session("nope")


# --- ASSESS + ADAPT ----------------------------------------------------------


def test_correct_answer_raises_difficulty_and_mastery():
    state = engine.start_session("decision-trees")
    fb = _answer(state, True)
    assert fb["verdict"] == "correct"
    assert fb["adaptation"]["direction"] == "up"
    assert state["level"] == 2
    assert state["mastery"] > 0
    assert get_question("decision-trees", state["current_question_id"])["difficulty"] == 2


def test_incorrect_answer_lowers_difficulty_and_reinforces_concept():
    state = engine.start_session("decision-trees")
    _answer(state, True)
    missed = get_question("decision-trees", state["current_question_id"])
    before = state["mastery"]
    fb = _answer(state, False)
    assert fb["verdict"] == "incorrect"
    assert fb["adaptation"]["direction"] == "down"
    assert state["mastery"] < before
    nxt = get_question("decision-trees", state["current_question_id"])
    assert nxt["difficulty"] == 1
    assert nxt["concept"] == missed["concept"]


def test_repeated_miss_on_concept_is_needs_review_with_reteach():
    state = engine.start_session("decision-trees")
    _answer(state, True)
    _answer(state, False)  # miss a concept; next question reinforces it
    fb = _answer(state, False)
    assert fb["verdict"] == "needs_review"
    assert fb["reteach"]
    assert any(c["status"] == "weak" for c in engine.session_view(state)["concepts"])


def test_wrong_question_or_bad_choice_rejected():
    state = engine.start_session("os-deadlock")
    with pytest.raises(engine.TeacherError):
        engine.submit_answer(state, "os-dl-6", 0)
    with pytest.raises(engine.TeacherError):
        engine.submit_answer(state, state["current_question_id"], 9)


def test_session_completes_after_budget_and_rejects_more_answers():
    state, feedback = _run("lab-page-replacement", [True] * engine.QUESTIONS_PER_SESSION)
    assert state["status"] == "completed"
    assert feedback[-1]["is_last"] is True
    assert state["current_question_id"] is None
    with pytest.raises(engine.TeacherError):
        engine.submit_answer(state, "lab-pr-1", 0)


def test_no_question_repeats_within_session():
    state, _ = _run("ai-search-strategies", [False, True, False, True, False])
    ids = [a["question_id"] for a in state["answers"]]
    assert len(ids) == len(set(ids))


def test_engine_is_deterministic():
    a, fa = _run("cn-error-detection", [True, False, True, True, False])
    b, fb = _run("cn-error-detection", [True, False, True, True, False])
    assert a == b and fa == fb


# --- REPORT ------------------------------------------------------------------


def test_perfect_session_report_recommends_advancing():
    state, _ = _run("decision-trees", [True] * 5)
    report = engine.build_report(state)
    assert report["score"] == 1.0
    assert report["mastery"] == 1.0
    assert report["band"] == "Proficient"
    assert report["highest_level_label"] == "Advanced"
    assert report["weak_areas"] == []
    assert report["recommendation"]["action"] == "advance"
    assert report["recommendation"]["next_topic_id"] == "bias-variance"
    assert len(report["review"]) == 5


def test_struggling_session_report_recommends_review_of_same_topic():
    state, _ = _run("os-cpu-scheduling", [False] * 5)
    report = engine.build_report(state)
    assert report["mastery"] == 0.0
    assert report["weak_areas"]
    assert report["recommendation"]["action"] == "review"
    assert report["recommendation"]["next_topic_id"] == "os-cpu-scheduling"


def test_last_topic_in_subject_advances_to_next_subject():
    # Bias-Variance (ML Unit V) is the last ML topic with a question bank;
    # the next one is in Explainable AI.
    state, _ = _run("bias-variance", [True] * 5)
    assert engine.build_report(state)["recommendation"]["next_topic_id"] == "xai-post-hoc"


def test_topic_without_question_bank_cannot_start():
    with pytest.raises(engine.TeacherError):
        engine.start_session("cn-dns")


def test_adaptation_message_matches_next_question_for_every_answer_pattern():
    import itertools

    from skillforge.teacher.curriculum import topic_ids

    for topic_id in topic_ids():
        _, topic = get_topic(topic_id)
        for pattern in itertools.product([True, False], repeat=engine.QUESTIONS_PER_SESSION):
            state = engine.start_session(topic_id)
            for ok in pattern:
                asked = get_question(topic_id, state["current_question_id"])
                fb = _answer(state, ok)
                if fb["is_last"]:
                    break
                nq = get_question(topic_id, state["current_question_id"])
                assert fb["adaptation"]["to_level"] == nq["difficulty"] == state["level"]
                expected = (
                    "up" if nq["difficulty"] > asked["difficulty"]
                    else "down" if nq["difficulty"] < asked["difficulty"] else "hold"
                )
                assert fb["adaptation"]["direction"] == expected
                assert fb["next_concept_name"] == topic["concepts"][nq["concept"]]["name"]
                same = nq["concept"] == asked["concept"]
                if not ok:
                    # Remediation: the missed concept is chosen whenever an unasked
                    # question on it exists at the same or an easier level.
                    available = [
                        q for q in topic["questions"]
                        if q["concept"] == asked["concept"]
                        and q["difficulty"] <= asked["difficulty"]
                        and (q["id"] not in state["asked"] or q["id"] == nq["id"])
                    ]
                    if available:
                        assert same and nq["difficulty"] <= asked["difficulty"]
                    # The teacher only claims to reinforce when it really does.
                    claims = any(w in fb["transition"] for w in ("reinforce", "this idea", "same idea"))
                    assert claims == same
                if expected == "down":
                    assert ("consolidate" if ok else "simpler") in fb["transition"]
                if expected == "up" and ok:
                    assert "deeper" in fb["transition"]
            assert state["status"] == "completed"


def test_missed_concept_is_revisited_when_an_easier_or_equal_question_exists():
    # cn-tl-1 (ports) correct -> cn-tl-3 (UDP/TCP, L2); missing it must bring
    # back the other UDP/TCP question (cn-tl-2, L1), not a new concept.
    state = engine.start_session("cn-transport", learner_model=None)
    _answer(state, True)
    missed = get_question("cn-transport", state["current_question_id"])
    fb = _answer(state, False)
    nxt = get_question("cn-transport", state["current_question_id"])
    assert nxt["concept"] == missed["concept"]
    assert nxt["difficulty"] <= missed["difficulty"]
    assert "reinforce" in fb["transition"]
    assert fb["next_concept_name"] == "UDP and TCP services"


def test_concept_names_keep_acronyms_mid_sentence():
    assert engine._lc("UDP and TCP services") == "UDP and TCP services"
    assert engine._lc("Object-Oriented Programming") == "object-oriented programming"
    state = engine.start_session("cn-transport", learner_model=None)
    _answer(state, True)
    _answer(state, False)  # the next question revisits "UDP and TCP services"
    assert "UDP and TCP services" in engine.session_view(state)["teacher_status"]
