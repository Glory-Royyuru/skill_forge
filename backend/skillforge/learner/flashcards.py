"""Personalised flashcards, selected from the learner state.

Card kinds:
- concept card  — front: the concept and a prompt to recall its key idea;
                  back: the concept's key-idea (re-teach) note.
- question card — only for questions the student has ALREADY answered (so a
                  flashcard can never reveal the answer key of an unseen
                  question); front: the prompt; back: the correct answer and
                  explanation.

The deck only ever contains fronts. A card's back is returned by `reveal`,
after the student chooses to flip it.

Ranking (higher first) adds up:
  +0.50 concept needs review        +0.30 last graded answer was incorrect
  +0.25 approaching mastery (0.6 ≤ p < 0.85)
  +0.20 not practised for ≥3 days (+ up to 0.20 more for staleness)
  +0.30 the concept's subject has a class in the next 48 h
  +0.20 last flashcard rating was "needs review"
  −0.30 marked "known" on a flashcard in the last 2 days

Ratings ("known", "review", "skipped") are self-reports: stored as a
secondary signal that only influences ordering, never mastery.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from skillforge.db.models import EvidenceEvent, FlashcardReview
from skillforge.learner.evidence import utcnow
from skillforge.learner.state import ConceptState, LearnerState
from skillforge.teacher import curriculum

DECK_SIZE = 10
RATINGS = ("known", "review", "skipped")


class CardError(LookupError):
    pass


def _score(c: ConceptState, class_subjects: set[str], now) -> tuple[float, list[str]]:
    score, reasons = 0.0, []
    if c.status == "needs_review":
        score += 0.5
        reasons.append("Needs review")
    if c.recent and not c.recent[-1]:
        score += 0.3
        reasons.append("Last answer was incorrect")
    if c.p_known is not None and c.attempts and 0.6 <= c.p_known < 0.85:
        score += 0.25
        reasons.append("Close to mastery")
    if c.days_since is not None and c.days_since >= 3:
        score += 0.2 + min(c.days_since, 30) / 30 * 0.2
        reasons.append(f"Not practised for {c.days_since} days")
    if c.subject_id in class_subjects:
        score += 0.3
        reasons.append("Class coming up")
    if c.flash_last == "review":
        score += 0.2
    if c.flash_last == "known" and c.flash_last_at and now - c.flash_last_at < timedelta(days=2):
        score -= 0.3
    return score, reasons


def build_deck(db: Session, state: LearnerState, class_subjects: set[str]) -> list[dict]:
    seen = {}
    for qid, correct in db.execute(
        select(EvidenceEvent.question_id, EvidenceEvent.correct)
        .where(EvidenceEvent.user_id == state.user_id)
        .order_by(EvidenceEvent.created_at)
    ):
        seen[qid] = correct  # last outcome wins

    ranked = []
    for c in state.concepts.values():
        if c.attempts == 0 and c.subject_id not in class_subjects:
            continue
        score, reasons = _score(c, class_subjects, state.now)
        if score <= 0 and c.attempts == 0:
            continue
        ranked.append((score, c, reasons))
    ranked.sort(key=lambda x: (-x[0], x[1].p_known or 0, x[1].id))

    deck = []
    for _score_value, c, reasons in ranked:
        if len(deck) >= DECK_SIZE:
            break
        _, topic = curriculum.get_topic(c.topic_id)
        deck.append(
            {
                "id": f"concept:{c.id}",
                "kind": "concept",
                "concept_name": c.name,
                "topic_title": c.topic_title,
                "subject_name": c.subject_name,
                "front": f"What is the key idea of {c.name}?",
                "reasons": reasons or ["Practised before"],
                "p_known": c.p_known if c.attempts else None,
            }
        )
        # One question card per concept: prefer a question answered incorrectly.
        missed = [
            q
            for q in topic["questions"]
            if q["concept"] == c.key and q["id"] in seen and curriculum.is_reviewed(q)
        ]
        missed.sort(key=lambda q: seen[q["id"]])  # incorrect (False) first
        if missed and len(deck) < DECK_SIZE:
            q = missed[0]
            deck.append(
                {
                    "id": f"question:{q['id']}",
                    "kind": "question",
                    "concept_name": c.name,
                    "topic_title": c.topic_title,
                    "subject_name": c.subject_name,
                    "front": q["prompt"],
                    "reasons": (["You answered this incorrectly"] if not seen[q["id"]] else ["Seen before"]),
                    "p_known": c.p_known if c.attempts else None,
                }
            )
    return deck


def _resolve(db: Session, user_id: int, card_id: str) -> tuple[str, dict]:
    """Return (concept_id, back) for a card the student may see, else raise."""
    kind, _, ref = card_id.partition(":")
    if kind == "concept":
        topic_id, _, key = ref.partition("/")
        found = curriculum.get_topic(topic_id)
        if found is None or key not in found[1]["concepts"]:
            raise CardError("card not found")
        topic = found[1]
        return ref, {
            "title": topic["concepts"][key]["name"],
            "text": topic["concepts"][key]["reteach"],
            "key_points": (topic.get("lesson") or {}).get("key_points", []),
        }
    if kind == "question":
        found = curriculum.find_question(ref)
        answered = db.scalar(
            select(EvidenceEvent.id)
            .where(EvidenceEvent.user_id == user_id, EvidenceEvent.question_id == ref)
            .limit(1)
        )
        if found is None or answered is None:
            raise CardError("card not found")
        _, topic, q = found
        return curriculum.concept_id(topic["id"], q["concept"]), {
            "title": q["options"][q["answer"]],
            "text": q["explanation"],
            "key_points": [],
        }
    raise CardError("card not found")


def reveal(db: Session, user_id: int, card_id: str) -> dict:
    return _resolve(db, user_id, card_id)[1]


def review(db: Session, user_id: int, card_id: str, rating: str) -> FlashcardReview:
    if rating not in RATINGS:
        raise CardError("unknown rating")
    concept_id, _ = _resolve(db, user_id, card_id)
    row = FlashcardReview(
        user_id=user_id, card_id=card_id, concept_id=concept_id, rating=rating, created_at=utcnow()
    )
    db.add(row)
    return row
