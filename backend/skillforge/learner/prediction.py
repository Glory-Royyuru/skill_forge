"""Extension point for a learned P(correct) predictor.

SkillForge does NOT ship a trained machine-learning model. This module
defines the interface a future model must implement and a deterministic
baseline that is clearly labelled as such.

Target: P(student answers this question correctly).

Candidate features (all available from SkillForge's own evidence log):
  bkt_p_known, concept attempts and weighted attempts, recent accuracy,
  consecutive incorrect, question difficulty, cognitive type, best correct
  difficulty on the concept, days since last practice, session count,
  median response time (secondary).

Data requirements before training anything:
  - SkillForge's own interaction data (evidence_events) with enough students
    and answers, and a held-out evaluation split by student;
  - external datasets such as ASSISTments or EdNet may be useful for
    pre-training or method validation, but they describe other students and
    curricula and must never be presented as representing VNR AIML students.
  No accuracy may be reported until a model is evaluated on real held-out data.
"""

from __future__ import annotations

from typing import Protocol

from skillforge.learner.state import ConceptState
from skillforge.teacher.learner_model import BKTLearnerModel


class CorrectnessPredictor(Protocol):
    name: str
    trained: bool

    def predict(self, concept: ConceptState, difficulty: int) -> float: ...


class BKTBaselinePredictor:
    """P(correct) from the BKT estimate with difficulty-dependent slip/guess.
    Deterministic; not trained on data."""

    name = "bkt-baseline"
    trained = False

    def __init__(self) -> None:
        self._bkt = BKTLearnerModel()

    def predict(self, concept: ConceptState, difficulty: int) -> float:
        p = concept.p_known if concept.p_known is not None else self._bkt.p_init
        return self._bkt.predict_correct({"c": p}, "c", difficulty)


def get_predictor() -> CorrectnessPredictor:
    return BKTBaselinePredictor()
