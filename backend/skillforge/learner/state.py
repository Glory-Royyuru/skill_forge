"""The unified learner state: what SkillForge believes a student knows, and why.

For every concept the state combines several transparent signals:

- `p_known`      — the persisted BKT estimate (learner_concepts)
- attempts       — graded answers on the concept (and their evidence weight)
- recent         — correctness of the last RECENT_WINDOW answers
- mistakes       — recent and consecutive incorrect answers
- by difficulty  — attempts/correct at each difficulty level
- by cognitive type — attempts/correct per recall/understand/apply/analyze
- recency        — days since the concept was last practised
- response time  — median, reported as a SECONDARY signal only; it never
                   changes mastery or status
- flashcards     — self-reports, a secondary signal for ordering reviews

Only evidence on questions with quality "reviewed" counts.

STATUS RULES (deterministic, in this order):
  not_started   no graded evidence
  needs_review  ≥2 consecutive incorrect, OR ≥2 incorrect among the last 4,
                OR p_known < 0.40 with ≥3 graded attempts (one miss after one hit is
                mixed evidence, not proof of a gap)
  mastered      p_known ≥ 0.85 AND ≥3 graded attempts (by weight) AND recent
                accuracy ≥ 2/3 AND at least one correct answer at
                Intermediate or Advanced difficulty
  learning      anything else with evidence

So one correct answer can never mark a concept mastered, and one wrong answer
never marks it as needing review on its own.

AGGREGATION: a topic's, subject's or the overall estimate is the mean
p_known over the concepts that have evidence ("assessed"), always reported
together with coverage (assessed / total concepts) so a high estimate on one
concept is never mistaken for command of a whole subject.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from skillforge.db.models import EvidenceEvent, FlashcardReview, LearnerConcept, Question
from skillforge.learner.evidence import utcnow
from skillforge.teacher import curriculum

RECENT_WINDOW = 6
NEEDS_REVIEW_P = 0.40
NEEDS_REVIEW_MIN_WEIGHT = 3.0
MASTERED_P = 0.85
MASTERED_MIN_WEIGHT = 3.0
MASTERED_RECENT_ACCURACY = 2 / 3
CONFIDENCE_LEVELS = ((5.0, "high"), (2.0, "medium"), (0.0, "low"))


def _naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


@dataclass
class ConceptState:
    id: str
    key: str
    name: str
    topic_id: str
    topic_title: str
    subject_id: str
    subject_name: str
    unit_number: int
    unit_title: str
    p_known: float | None = None
    attempts: int = 0
    weight: float = 0.0
    correct: int = 0
    recent: list[bool] = field(default_factory=list)  # oldest → newest
    consecutive_incorrect: int = 0
    by_difficulty: dict[int, list[int]] = field(default_factory=lambda: {1: [0, 0], 2: [0, 0], 3: [0, 0]})
    by_cognitive: dict[str, list[int]] = field(default_factory=dict)
    last_practiced: datetime | None = None
    first_practiced: datetime | None = None
    first_p_before: float | None = None
    response_times: list[int] = field(default_factory=list)
    flash_known: int = 0
    flash_review: int = 0
    flash_last: str | None = None
    flash_last_at: datetime | None = None
    status: str = "not_started"
    days_since: int | None = None

    @property
    def accuracy(self) -> float | None:
        return self.correct / self.attempts if self.attempts else None

    @property
    def recent_accuracy(self) -> float | None:
        return sum(self.recent) / len(self.recent) if self.recent else None

    @property
    def recent_incorrect(self) -> int:
        return sum(1 for ok in self.recent if not ok)

    @property
    def confidence(self) -> str:
        if self.attempts == 0:
            return "none"
        return next(label for threshold, label in CONFIDENCE_LEVELS if self.weight >= threshold)

    @property
    def best_correct_difficulty(self) -> int:
        return max((d for d, (_, c) in self.by_difficulty.items() if c), default=0)

    @property
    def median_response_ms(self) -> int | None:
        return int(median(self.response_times)) if self.response_times else None

    def evidence_lines(self) -> list[str]:
        """Human-readable facts behind this concept's status."""
        out = []
        if self.p_known is not None and self.attempts:
            out.append(
                f"Estimated knowledge {round(self.p_known * 100)}% ({self.confidence} confidence, "
                f"{self.attempts} graded answer{'s' if self.attempts != 1 else ''})"
            )
        if self.recent:
            out.append(f"{sum(self.recent)} of your last {len(self.recent)} answers correct")
        if self.consecutive_incorrect >= 2:
            out.append(f"{self.consecutive_incorrect} incorrect answers in a row")
        if self.days_since is not None and self.days_since >= 3:
            out.append(f"Last practised {self.days_since} days ago")
        if self.flash_review:
            out.append(
                f"Marked 'needs review' on {self.flash_review} "
                f"flashcard{'s' if self.flash_review != 1 else ''}"
            )
        return out

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "key": self.key,
            "name": self.name,
            "topic_id": self.topic_id,
            "topic_title": self.topic_title,
            "subject_id": self.subject_id,
            "subject_name": self.subject_name,
            "unit_number": self.unit_number,
            "unit_title": self.unit_title,
            "status": self.status,
            "p_known": self.p_known if self.attempts else None,
            "confidence": self.confidence,
            "attempts": self.attempts,
            "correct": self.correct,
            "accuracy": self.accuracy,
            "recent": self.recent,
            "recent_accuracy": self.recent_accuracy,
            "consecutive_incorrect": self.consecutive_incorrect,
            "by_difficulty": {
                str(d): {"attempts": a, "correct": c} for d, (a, c) in self.by_difficulty.items()
            },
            "by_cognitive": {k: {"attempts": a, "correct": c} for k, (a, c) in self.by_cognitive.items()},
            "last_practiced": self.last_practiced.isoformat() + "Z" if self.last_practiced else None,
            "days_since": self.days_since,
            "median_response_ms": self.median_response_ms,
            "flashcards": {"known": self.flash_known, "review": self.flash_review, "last": self.flash_last},
            "evidence": self.evidence_lines(),
        }


def classify(c: ConceptState) -> str:
    if c.attempts == 0:
        return "not_started"
    last4 = c.recent[-4:]
    if (
        c.consecutive_incorrect >= 2
        or sum(1 for ok in last4 if not ok) >= 2
        or (c.p_known is not None and c.p_known < NEEDS_REVIEW_P and c.weight >= NEEDS_REVIEW_MIN_WEIGHT)
    ):
        return "needs_review"
    if (
        c.p_known is not None
        and c.p_known >= MASTERED_P
        and c.weight >= MASTERED_MIN_WEIGHT
        and (c.recent_accuracy or 0) >= MASTERED_RECENT_ACCURACY
        and c.best_correct_difficulty >= 2
    ):
        return "mastered"
    return "learning"


def _aggregate(concepts: list[ConceptState]) -> dict:
    assessed = [c for c in concepts if c.attempts]
    counts = defaultdict(int)
    for c in concepts:
        counts[c.status] += 1
    return {
        "estimate": sum(c.p_known for c in assessed) / len(assessed) if assessed else None,
        "assessed": len(assessed),
        "total": len(concepts),
        "coverage": len(assessed) / len(concepts) if concepts else 0.0,
        "attempts": sum(c.attempts for c in concepts),
        "correct": sum(c.correct for c in concepts),
        "mastered": counts["mastered"],
        "needs_review": counts["needs_review"],
        "learning": counts["learning"],
        "not_started": counts["not_started"],
    }


def topic_status(concepts: list[ConceptState]) -> str:
    statuses = [c.status for c in concepts]
    if not statuses or all(s == "not_started" for s in statuses):
        return "not_started"
    if "needs_review" in statuses:
        return "needs_review"
    if all(s == "mastered" for s in statuses):
        return "mastered"
    return "in_progress"


@dataclass
class LearnerState:
    user_id: int
    now: datetime
    concepts: dict[str, ConceptState]
    events: int

    def by_topic(self, topic_id: str) -> list[ConceptState]:
        return [c for c in self.concepts.values() if c.topic_id == topic_id]

    def by_subject(self, subject_id: str) -> list[ConceptState]:
        return [c for c in self.concepts.values() if c.subject_id == subject_id]

    def assessed(self) -> list[ConceptState]:
        return [c for c in self.concepts.values() if c.attempts]

    def topic_summary(self, topic_id: str) -> dict:
        concepts = self.by_topic(topic_id)
        return {**_aggregate(concepts), "status": topic_status(concepts)}

    def subject_summary(self, subject_id: str) -> dict:
        return _aggregate(self.by_subject(subject_id))

    def overall(self) -> dict:
        return _aggregate(list(self.concepts.values()))

    def has_evidence(self) -> bool:
        return self.events > 0


def build(db: Session, user_id: int, now: datetime | None = None) -> LearnerState:
    """Assemble the learner state for one student from persisted evidence."""
    now = now or utcnow()
    concepts: dict[str, ConceptState] = {}
    for tid in curriculum.topic_ids():
        subject, topic = curriculum.get_topic(tid)
        for key, c in topic["concepts"].items():
            cid = curriculum.concept_id(tid, key)
            concepts[cid] = ConceptState(
                id=cid,
                key=key,
                name=c["name"],
                topic_id=tid,
                topic_title=topic["title"],
                subject_id=subject["id"],
                subject_name=subject["name"],
                unit_number=topic["unit_number"],
                unit_title=topic["unit_title"],
            )

    for cid, p in db.execute(
        select(LearnerConcept.concept_id, LearnerConcept.p_known).where(LearnerConcept.user_id == user_id)
    ):
        if cid in concepts:
            concepts[cid].p_known = p

    events = (
        db.execute(
            select(EvidenceEvent)
            .join(Question, Question.id == EvidenceEvent.question_id)
            .where(EvidenceEvent.user_id == user_id, Question.quality == "reviewed")
            .order_by(EvidenceEvent.created_at, EvidenceEvent.id)
        )
        .scalars()
        .all()
    )
    for e in events:
        c = concepts.get(e.concept_id)
        if c is None:
            continue
        c.attempts += 1
        c.weight += e.weight
        c.correct += 1 if e.correct else 0
        c.recent = (c.recent + [bool(e.correct)])[-RECENT_WINDOW:]
        c.consecutive_incorrect = 0 if e.correct else c.consecutive_incorrect + 1
        d = c.by_difficulty.setdefault(e.difficulty, [0, 0])
        d[0] += 1
        d[1] += 1 if e.correct else 0
        if e.cognitive_type:
            k = c.by_cognitive.setdefault(e.cognitive_type, [0, 0])
            k[0] += 1
            k[1] += 1 if e.correct else 0
        when = _naive(e.created_at)
        if c.first_practiced is None:
            c.first_practiced = when
            c.first_p_before = e.p_before
        c.last_practiced = when
        if e.response_ms:
            c.response_times.append(e.response_ms)

    for f in db.execute(
        select(FlashcardReview).where(FlashcardReview.user_id == user_id).order_by(FlashcardReview.created_at)
    ).scalars():
        c = concepts.get(f.concept_id)
        if c is None:
            continue
        if f.rating == "known":
            c.flash_known += 1
        elif f.rating == "review":
            c.flash_review += 1
        c.flash_last = f.rating
        c.flash_last_at = _naive(f.created_at)

    for c in concepts.values():
        if c.last_practiced is not None:
            c.days_since = max(0, (now - c.last_practiced).days)
        c.status = classify(c)

    return LearnerState(user_id=user_id, now=now, concepts=concepts, events=len(events))
