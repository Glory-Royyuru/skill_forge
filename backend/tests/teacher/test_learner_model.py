from __future__ import annotations

from fastapi.testclient import TestClient

from skillforge.api.app import create_app
from skillforge.teacher import engine
from skillforge.teacher.curriculum import get_question, get_topic
from skillforge.teacher.learner_model import BKTLearnerModel, get_learner_model


def _answer(state: dict, correct: bool) -> dict:
    q = get_question(state["topic_id"], state["current_question_id"])
    return engine.submit_answer(state, q["id"], q["answer"] if correct else (q["answer"] + 1) % 4)


# --- BKT maths -----------------------------------------------------------------


def test_bkt_correct_raises_and_incorrect_lowers_estimate():
    m = BKTLearnerModel()
    k = m.init(["a", "b"])
    assert k == {"a": 0.3, "b": 0.3}
    up = m.update(k, "a", 2, True)
    down = m.update(k, "b", 2, False)
    assert up > 0.3 > down > 0


def test_bkt_prediction_is_bounded_by_guess_and_slip():
    m = BKTLearnerModel()
    for p in (0.0, 0.5, 1.0):
        for d in (1, 2, 3):
            pred = m.predict_correct({"a": p}, "a", d)
            assert m.guess[d] - 1e-9 <= pred <= 1 - m.slip[d] + 1e-9


def test_bkt_uses_prior_estimates():
    assert BKTLearnerModel().init(["a", "b"], {"a": 0.9}) == {"a": 0.9, "b": 0.3}


def test_get_learner_model_can_be_disabled():
    assert get_learner_model("bkt").name == "bkt"
    assert get_learner_model("none") is None


# --- Engine integration ----------------------------------------------------------


def test_session_exposes_learner_model_signal():
    state = engine.start_session("decision-trees", learner_model=BKTLearnerModel())
    view = engine.session_view(state)
    assert view["learner_model"]["label"] == "Bayesian Knowledge Tracing"
    assert 0 < view["learner_model"]["predicted_correct"] < 1
    assert all(c["estimate"] == 0.3 for c in view["concepts"])
    fb = _answer(state, True)
    lm = fb["learner_model"]
    assert lm["known_after"] > lm["known_before"]
    assert lm["next_concept_name"]


def test_learner_model_targets_least_known_concept_after_correct_answer():
    state = engine.start_session("decision-trees", learner_model=BKTLearnerModel())
    first = get_question("decision-trees", state["current_question_id"])
    _answer(state, True)
    nxt = get_question("decision-trees", state["current_question_id"])
    assert nxt["concept"] != first["concept"]
    knowledge = state["learner_model"]["knowledge"]
    _, topic = get_topic("decision-trees")
    same_level = [q for q in topic["questions"] if q["difficulty"] == nxt["difficulty"]]
    assert knowledge[nxt["concept"]] == min(knowledge[q["concept"]] for q in same_level)


def test_probable_guess_keeps_teacher_on_the_same_concept():
    _, topic = get_topic("decision-trees")
    weak_prior = {c: 0.1 for c in topic["concepts"]}
    state = engine.start_session(
        "decision-trees", prior_knowledge=weak_prior, learner_model=BKTLearnerModel()
    )
    first = get_question("decision-trees", state["current_question_id"])
    fb = _answer(state, True)
    assert fb["learner_model"]["known_after"] < engine.GUESS_CONFIRM_THRESHOLD
    assert fb["learner_model"]["targeting"] == "confirm"
    nxt = get_question("decision-trees", state["current_question_id"])
    assert nxt["concept"] == first["concept"]
    assert nxt["difficulty"] == 2  # difficulty still steps up deterministically
    assert "same idea" in fb["transition"]


def test_engine_runs_without_learner_model():
    state = engine.start_session("stacks", learner_model=None)
    for ok in [True, False, True, True, False]:
        fb = _answer(state, ok)
        assert fb["learner_model"] is None
    assert state["status"] == "completed"
    assert engine.session_view(state)["learner_model"] is None
    assert engine.build_report(state)["learner_model"] is None


def test_concept_estimates_carry_over_between_sessions(tmp_path):
    client = TestClient(create_app(database_url=f"sqlite:///{tmp_path / 'lm.db'}", seed_demo=False))
    s = client.post("/api/teacher/session/start", json={"topic_id": "arrays"}).json()
    for _ in range(5):
        q = s["current_question"]
        ans = get_question("arrays", q["id"])["answer"]
        s = client.post(
            f"/api/teacher/session/{s['id']}/answer", json={"question_id": q["id"], "choice": ans}
        ).json()["session"]
    finished = {c["id"]: c["estimate"] for c in s["concepts"]}
    again = client.post("/api/teacher/session/start", json={"topic_id": "arrays"}).json()
    assert {c["id"]: c["estimate"] for c in again["concepts"]} == finished
    assert any("Learner model restored" in entry["text"] for entry in again["log"])
