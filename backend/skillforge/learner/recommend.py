"""The recommendation engine: learner state + context → next learning actions.

Deterministic and explainable: every recommendation carries the evidence it
was derived from. Rules and their base priorities (higher = more urgent):

  take_diagnostic          0.99  no graded evidence yet and diagnostic not done/skipped
  continue_session         0.97  a Teacher session is in progress
  remediate_misconception  0.90  ≥2 consecutive misses, or ≥3 misses in the last 6
  prepare_for_class        0.86  class within 24 h (0.78 within 48 h) in a subject
                                 with a question bank; +0.05 if that topic needs review
  review_concept           0.70 + 0.20·(1 − p_known) for concepts needing review
  revisit_neglected        0.55 + up to 0.15 by staleness (≥7 days; ≥14 if mastered)
  start_new_topic          0.45 (0.60 while the student has little evidence)
  challenge_up             0.50  ≥2 graded answers, p_known ≥ 0.65, still learning, no correct answer
                                 at the next difficulty
  flashcards               0.50  ≥3 concepts that would benefit from a quick review
  rapid_round              0.40  ≥4 practised concepts (retrieval fluency check)

Concept-level recommendations are de-duplicated per topic (the most urgent
wins). The engine never invents a connection: a timetable class whose subject
has no question bank yields no preparation recommendation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

from skillforge.learner.state import ConceptState, LearnerState
from skillforge.teacher import curriculum
from skillforge.teacher.curriculum import LEVEL_NAMES

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
CLASS_HORIZON_HOURS = 48
# A harder question is only suggested once a concept has at least this much graded evidence.
MIN_EVIDENCE_FOR_CHALLENGE = 2.0


@dataclass
class Recommendation:
    id: str
    action: str
    title: str
    reason: str
    priority: float
    estimated_minutes: int
    confidence: str
    evidence: list[str] = field(default_factory=list)
    subject_id: str | None = None
    subject_name: str | None = None
    unit_number: int | None = None
    unit_title: str | None = None
    topic_id: str | None = None
    topic_title: str | None = None
    concept_id: str | None = None
    concept_key: str | None = None
    concept_name: str | None = None
    target_difficulty: int | None = None
    target_difficulty_label: str | None = None
    # How the frontend acts on it: {"kind": "diagnostic" | "resume" | "session" |
    # "flashcards" | "rapid_round", ...}
    cta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        out = asdict(self)
        out["priority"] = round(self.priority, 3)
        return out


@dataclass
class Context:
    """Everything outside the learner state the engine may use."""

    local_now: datetime
    active_session: dict | None = None
    diagnostic_status: str = "none"  # none | active | completed | skipped
    timetable: list[dict] = field(default_factory=list)  # {day_of_week, start_time "HH:MM", subject_id, ...}


def _diagnostic_size() -> int:
    from skillforge.learner.diagnostic import choose_questions

    return len(choose_questions())


def _with_concept(r: Recommendation, c: ConceptState) -> Recommendation:
    r.subject_id, r.subject_name = c.subject_id, c.subject_name
    r.unit_number, r.unit_title = c.unit_number, c.unit_title
    r.topic_id, r.topic_title = c.topic_id, c.topic_title
    r.concept_id, r.concept_key, r.concept_name = c.id, c.key, c.name
    if r.target_difficulty:
        r.target_difficulty_label = LEVEL_NAMES[r.target_difficulty]
    r.cta = {
        "kind": "session",
        "topic_id": c.topic_id,
        "concept_key": c.key,
        "target_difficulty": r.target_difficulty,
    }
    return r


def _when(delta: timedelta, start: datetime, now: datetime) -> str:
    if start.date() == now.date():
        return f"today at {start:%H:%M}"
    if start.date() == (now + timedelta(days=1)).date():
        return f"tomorrow at {start:%H:%M}"
    return f"{DAY_NAMES[start.weekday()]} at {start:%H:%M}"


def upcoming_classes(
    timetable: list[dict], now: datetime, horizon_hours: int = CLASS_HORIZON_HOURS
) -> list[dict]:
    """Next occurrence of each timetable slot within the horizon, soonest first."""
    out = []
    for e in timetable:
        hh, mm = (int(x) for x in e["start_time"].split(":")[:2])
        days_ahead = (e["day_of_week"] - now.weekday()) % 7
        start = (now + timedelta(days=days_ahead)).replace(hour=hh, minute=mm, second=0, microsecond=0)
        if start < now:
            start += timedelta(days=7)
        delta = start - now
        if delta <= timedelta(hours=horizon_hours):
            out.append(
                {
                    **e,
                    "starts_at": start.isoformat(timespec="minutes"),
                    "hours_until": round(delta.total_seconds() / 3600, 1),
                    "when": _when(delta, start, now),
                }
            )
    return sorted(out, key=lambda x: x["hours_until"])


def _target_difficulty(c: ConceptState) -> int:
    """Productive challenge: one step above the hardest level answered
    correctly, one step below the easiest level recently missed."""
    if c.attempts == 0:
        return 1
    best = c.best_correct_difficulty
    if c.status == "needs_review":
        failed = [d for d, (a, ok) in c.by_difficulty.items() if a > ok]
        return max(1, min(failed) - 1) if failed else 1
    return min(3, best + 1) if best else 1


def prepare_for_class(state: LearnerState, cls: dict) -> Recommendation | None:
    subject_id = cls["subject_id"]
    topics = curriculum.assessable_in_subject(subject_id)
    if not topics:
        return None  # subject has no question bank: no invented preparation
    summaries = [(t, state.topic_summary(t)) for t in topics]
    started = [(t, s) for t, s in summaries if s["assessed"]]
    if started:
        topic_id, summary = min(
            started, key=lambda ts: (ts[1]["status"] != "needs_review", ts[1]["estimate"])
        )
    else:
        topic_id, summary = summaries[0]
    concepts = state.by_topic(topic_id)
    concept = min(concepts, key=lambda c: (c.attempts > 0, c.p_known if c.p_known is not None else 0))
    subject, topic = curriculum.get_topic(topic_id)
    priority = (0.86 if cls["hours_until"] <= 24 else 0.78) + (
        0.05 if summary["status"] == "needs_review" else 0
    )
    evidence = [f"{subject['name']} class {cls['when']}" + (f" in {cls['room']}" if cls.get("room") else "")]
    if summary["assessed"]:
        evidence.append(
            f"{topic['title']}: estimated knowledge {round(summary['estimate'] * 100)}% "
            f"across {summary['assessed']} of {summary['total']} concepts"
        )
    else:
        evidence.append(f"You have not practised {topic['title']} yet")
    r = Recommendation(
        id=f"class:{cls.get('id', subject_id)}:{topic_id}",
        action="prepare_for_class",
        title=f"Prepare for {subject['short_name']} {cls['when'].split(' at ')[0]}: {topic['title']}",
        reason=f"Your {subject['name']} class is {cls['when']}.",
        priority=priority,
        estimated_minutes=10,
        confidence=concept.confidence if concept.attempts else "low",
        evidence=evidence,
        target_difficulty=_target_difficulty(concept),
    )
    return _with_concept(r, concept)


def recommend(state: LearnerState, ctx: Context, limit: int = 6) -> list[Recommendation]:
    recs: list[Recommendation] = []
    evidence_total = sum(c.attempts for c in state.concepts.values())

    if ctx.active_session:
        a = ctx.active_session
        recs.append(
            Recommendation(
                id=f"resume:{a['id']}",
                action="continue_session",
                title=f"Continue {a['topic_title']}",
                reason=f"You are part-way through this session (question {a['question_number']} of "
                f"{a['max_questions']}).",
                priority=0.97,
                estimated_minutes=4,
                confidence="high",
                evidence=[f"Session started {a.get('created_at', '')[:10]}"] if a.get("created_at") else [],
                topic_id=a["topic_id"],
                topic_title=a["topic_title"],
                subject_name=a["subject_name"],
                cta={"kind": "resume", "session_id": a["id"]},
            )
        )

    if evidence_total == 0 and ctx.diagnostic_status in ("none", "active"):
        recs.append(
            Recommendation(
                id="diagnostic",
                action="take_diagnostic",
                title="Take the starting-point diagnostic",
                reason=f"{_diagnostic_size()} questions, one from each subject with a question bank, give "
                "SkillForge a starting point, so recommendations are based on evidence rather than guesses.",
                priority=0.99,
                estimated_minutes=6,
                confidence="high",
                cta={"kind": "diagnostic"},
            )
        )

    for cls in upcoming_classes(ctx.timetable, ctx.local_now):
        r = prepare_for_class(state, cls)
        if r is not None:
            recs.append(r)

    for c in state.assessed():
        if c.consecutive_incorrect >= 2 or c.recent_incorrect >= 3:
            r = Recommendation(
                id=f"remediate:{c.id}",
                action="remediate_misconception",
                title=f"Fix a recurring mistake: {c.name}",
                reason="Repeated incorrect answers on this concept point to a misconception worth "
                "addressing directly.",
                priority=0.90,
                estimated_minutes=8,
                confidence=c.confidence,
                evidence=c.evidence_lines(),
                target_difficulty=_target_difficulty(c),
            )
            recs.append(_with_concept(r, c))
        elif c.status == "needs_review":
            r = Recommendation(
                id=f"review:{c.id}",
                action="review_concept",
                title=f"Review {c.name}",
                reason="Your recent answers show this concept is not secure yet.",
                priority=0.70 + 0.20 * (1 - (c.p_known or 0)),
                estimated_minutes=8,
                confidence=c.confidence,
                evidence=c.evidence_lines(),
                target_difficulty=_target_difficulty(c),
            )
            recs.append(_with_concept(r, c))
        elif c.days_since is not None and c.days_since >= (14 if c.status == "mastered" else 7):
            r = Recommendation(
                id=f"revisit:{c.id}",
                action="revisit_neglected",
                title=f"Revisit {c.name}",
                reason=f"You have not practised this concept for {c.days_since} days.",
                priority=0.55 + min(c.days_since, 30) / 30 * 0.15,
                estimated_minutes=6,
                confidence=c.confidence,
                evidence=c.evidence_lines(),
                target_difficulty=_target_difficulty(c),
            )
            recs.append(_with_concept(r, c))
        elif (
            c.status == "learning"
            and c.weight >= MIN_EVIDENCE_FOR_CHALLENGE
            and (c.p_known or 0) >= 0.65
            and c.best_correct_difficulty < 3
        ):
            r = Recommendation(
                id=f"challenge:{c.id}",
                action="challenge_up",
                title=f"Try a harder question on {c.name}",
                reason="You are answering this concept well; a harder question will confirm it.",
                priority=0.50,
                estimated_minutes=5,
                confidence=c.confidence,
                evidence=c.evidence_lines(),
                target_difficulty=min(3, c.best_correct_difficulty + 1),
            )
            recs.append(_with_concept(r, c))

    unstarted = [t for t in curriculum.topic_ids() if state.topic_summary(t)["assessed"] == 0]
    if unstarted and (evidence_total > 0 or ctx.diagnostic_status in ("completed", "skipped")):
        class_subjects = [c["subject_id"] for c in upcoming_classes(ctx.timetable, ctx.local_now, 24 * 7)]
        unstarted.sort(key=lambda t: (curriculum.get_topic(t)[0]["id"] not in class_subjects,))
        subject, topic = curriculum.get_topic(unstarted[0])
        recs.append(
            Recommendation(
                id=f"new:{topic['id']}",
                action="start_new_topic",
                title=f"Start {topic['title']}",
                reason="A topic you have not studied yet"
                + (", in a subject on your timetable this week." if subject["id"] in class_subjects else "."),
                priority=0.60 if evidence_total < 10 else 0.45,
                estimated_minutes=5,
                confidence="low",
                evidence=[
                    f"{subject['name']} · {subject['unit_label']} {topic['unit_number']}: "
                    f"{topic['unit_title']}"
                ],
                subject_id=subject["id"],
                subject_name=subject["name"],
                unit_number=topic["unit_number"],
                unit_title=topic["unit_title"],
                topic_id=topic["id"],
                topic_title=topic["title"],
                cta={"kind": "session", "topic_id": topic["id"]},
            )
        )

    reviewable = [
        c for c in state.assessed() if c.status in ("needs_review", "learning") or (c.days_since or 0) >= 3
    ]
    if len(reviewable) >= 3:
        recs.append(
            Recommendation(
                id="flashcards",
                action="flashcards",
                title="Review with personalised flashcards",
                reason=f"{len(reviewable)} concepts would benefit from a quick review.",
                priority=0.50,
                estimated_minutes=5,
                confidence="medium",
                evidence=[
                    f"{c.name} ({c.topic_title})"
                    for c in sorted(reviewable, key=lambda c: c.p_known or 0)[:3]
                ],
                cta={"kind": "flashcards"},
            )
        )
    if len(state.assessed()) >= 4:
        recs.append(
            Recommendation(
                id="rapid",
                action="rapid_round",
                title="Rapid Round: 60-second retrieval check",
                reason="Quick recall of concepts you have practised builds fluency.",
                priority=0.40,
                estimated_minutes=1,
                confidence="medium",
                evidence=[f"{len(state.assessed())} concepts practised"],
                cta={"kind": "rapid_round"},
            )
        )

    # De-duplicate: one concept-level recommendation per topic, the most urgent.
    recs.sort(key=lambda r: -r.priority)
    seen_topics: set[str] = set()
    out: list[Recommendation] = []
    for r in recs:
        if r.concept_id and r.topic_id in seen_topics:
            continue
        if r.concept_id:
            seen_topics.add(r.topic_id)
        out.append(r)
    return out[:limit]
