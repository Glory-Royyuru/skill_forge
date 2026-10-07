"""Learner model: a probabilistic estimate of what the student knows.

The Teacher engine talks to this through a small interface so the model is
a pluggable *supporting signal* — the deterministic pedagogy (difficulty
steps, remediation, reporting) never depends on it being present.

The shipped implementation is Bayesian Knowledge Tracing (Corbett &
Anderson, 1995): each concept is a hidden binary "known / not known" state.
After every answer the posterior P(known) is updated with Bayes' rule using
slip and guess probabilities, then a learning transition is applied. It is
pure Python, deterministic, and runs offline.

Parameters are standard textbook defaults, lightly adjusted per question
difficulty (harder questions are easier to slip on and harder to guess) —
they are not fitted to data.
"""

from __future__ import annotations

from typing import Protocol

from skillforge.core.settings import get_settings


class LearnerModel(Protocol):
    name: str
    label: str

    def init(self, concepts: list[str], prior: dict[str, float] | None = None) -> dict[str, float]:
        """Initial P(known) per concept, optionally carried over from a prior session."""

    def update(self, knowledge: dict[str, float], concept: str, difficulty: int, correct: bool) -> float:
        """Update `knowledge` in place for one observed answer; return the new P(known)."""

    def predict_correct(self, knowledge: dict[str, float], concept: str, difficulty: int) -> float:
        """Probability the student answers a question on `concept` at `difficulty` correctly."""


class BKTLearnerModel:
    name = "bkt"
    label = "Bayesian Knowledge Tracing"

    def __init__(
        self,
        p_init: float = 0.3,
        p_learn: float = 0.15,
        slip: dict[int, float] | None = None,
        guess: dict[int, float] | None = None,
    ):
        self.p_init = p_init
        self.p_learn = p_learn
        self.slip = slip or {1: 0.08, 2: 0.12, 3: 0.18}
        self.guess = guess or {1: 0.25, 2: 0.20, 3: 0.15}

    def init(self, concepts: list[str], prior: dict[str, float] | None = None) -> dict[str, float]:
        prior = prior or {}
        return {c: round(float(prior.get(c, self.p_init)), 4) for c in concepts}

    def update(self, knowledge: dict[str, float], concept: str, difficulty: int, correct: bool) -> float:
        p = knowledge.get(concept, self.p_init)
        s, g = self.slip[difficulty], self.guess[difficulty]
        if correct:
            posterior = p * (1 - s) / (p * (1 - s) + (1 - p) * g)
        else:
            posterior = p * s / (p * s + (1 - p) * (1 - g))
        p_next = posterior + (1 - posterior) * self.p_learn
        knowledge[concept] = round(p_next, 4)
        return knowledge[concept]

    def predict_correct(self, knowledge: dict[str, float], concept: str, difficulty: int) -> float:
        p = knowledge.get(concept, self.p_init)
        return round(p * (1 - self.slip[difficulty]) + (1 - p) * self.guess[difficulty], 4)


_MODELS = {"bkt": BKTLearnerModel}


def get_learner_model(name: str | None = None) -> LearnerModel | None:
    """The configured learner model, or None when disabled
    (``TEACHER_LEARNER_MODEL=none``)."""
    key = (name if name is not None else get_settings().teacher_learner_model).lower()
    cls = _MODELS.get(key)
    return cls() if cls else None
