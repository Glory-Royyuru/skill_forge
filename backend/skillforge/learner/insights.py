"""Activity calendar, learning trends, PTM (SWOT) analysis and activity level.

Everything here is computed from the student's own persisted records:
evidence_events, learning_sessions, flashcard_reviews, rapid_rounds and
diagnostics. Nothing is estimated from population data or invented.

Dates are the student's local dates: callers pass the browser's UTC offset.

ACTIVE TIME is estimated from interaction timestamps: interactions less than
10 minutes apart count as one continuous stretch, and each stretch adds one
minute for its first interaction. It is labelled as an estimate in the UI.

ACTIVITY LEVEL / XP measures activity, never knowledge:
  10 per Teacher-session answer, 25 per completed session, 5 per diagnostic
  answer, 4 per Rapid Round answer, 2 per flashcard review.
  Level L → L+1 needs 100·L more XP.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from skillforge.db.models import EvidenceEvent, FlashcardReview, LearningSession, RapidRound
from skillforge.learner.state import LearnerState
from skillforge.teacher import curriculum

GAP_MINUTES = 10
# An "improvement" (PTM opportunity) needs at least this many graded answers on the concept.
MIN_ATTEMPTS_FOR_TREND = 3
XP_RULES = {
    "session_answer": 10,
    "session_completed": 25,
    "diagnostic_answer": 5,
    "rapid_answer": 4,
    "flashcard_review": 2,
}


def _naive(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=None) if dt is not None and dt.tzinfo else dt


def _local(dt: datetime, tz_offset_minutes: int) -> datetime:
    # JS getTimezoneOffset(): minutes *behind* UTC (IST = −330).
    return _naive(dt) - timedelta(minutes=tz_offset_minutes)


def _events(db: Session, user_id: int) -> list[EvidenceEvent]:
    return db.scalars(
        select(EvidenceEvent).where(EvidenceEvent.user_id == user_id).order_by(EvidenceEvent.created_at)
    ).all()


def _active_minutes(stamps: list[datetime]) -> int:
    if not stamps:
        return 0
    stamps = sorted(stamps)
    total = 1.0
    for a, b in zip(stamps, stamps[1:], strict=False):
        gap = (b - a).total_seconds() / 60
        total += gap if gap <= GAP_MINUTES else 1
    return round(total)


# --- Calendar -----------------------------------------------------------------------


def activity(db: Session, user_id: int, start: date, end: date, tz_offset_minutes: int = 0) -> dict:
    days: dict[date, dict] = {}

    def day(d: date) -> dict | None:
        if not start <= d <= end:
            return None
        if d not in days:
            days[d] = {
                "date": d.isoformat(),
                "sessions_completed": 0,
                "graded_answers": 0,
                "correct": 0,
                "by_source": {"session": 0, "diagnostic": 0, "rapid_round": 0},
                "flashcards": 0,
                "rapid_rounds": 0,
                "concepts_practised": set(),
                "topics": set(),
                "concept_change": {},
                "_stamps": [],
            }
        return days[d]

    for e in _events(db, user_id):
        local = _local(e.created_at, tz_offset_minutes)
        d = day(local.date())
        if d is None:
            continue
        d["graded_answers"] += 1
        d["correct"] += 1 if e.correct else 0
        d["by_source"][e.source] = d["by_source"].get(e.source, 0) + 1
        d["concepts_practised"].add(e.concept_id)
        found = curriculum.get_topic(e.concept_id.split("/", 1)[0])
        if found:
            d["topics"].add(found[1]["title"])
        if e.p_before is not None and e.p_after is not None:
            first, _ = d["concept_change"].get(e.concept_id, (e.p_before, None))
            d["concept_change"][e.concept_id] = (first, e.p_after)
        d["_stamps"].append(local)

    for completed_at, created_at in db.execute(
        select(LearningSession.completed_at, LearningSession.created_at).where(
            LearningSession.user_id == user_id, LearningSession.status == "completed"
        )
    ):
        d = day(_local(completed_at, tz_offset_minutes).date()) if completed_at else None
        if d is not None:
            d["sessions_completed"] += 1
            d["_stamps"].append(_local(created_at, tz_offset_minutes))

    for f in db.scalars(select(FlashcardReview).where(FlashcardReview.user_id == user_id)):
        local = _local(f.created_at, tz_offset_minutes)
        d = day(local.date())
        if d is not None:
            d["flashcards"] += 1
            d["_stamps"].append(local)

    for r in db.scalars(select(RapidRound).where(RapidRound.user_id == user_id)):
        if r.responses:
            d = day(_local(r.started_at, tz_offset_minutes).date())
            if d is not None:
                d["rapid_rounds"] += 1

    out = []
    for d in sorted(days):
        item = days[d]
        improved = sum(
            1 for first, last in item["concept_change"].values() if last is not None and last - first >= 0.05
        )
        out.append(
            {
                **{k: v for k, v in item.items() if not k.startswith("_") and k not in ("concept_change",)},
                "concepts_practised": len(item["concepts_practised"]),
                "topics": sorted(item["topics"]),
                "concepts_improved": improved,
                "active_minutes": _active_minutes(item["_stamps"]),
            }
        )
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "days": out,
        "active_days": len(out),
        "graded_answers": sum(d["graded_answers"] for d in out),
    }


# --- Trends -------------------------------------------------------------------------


def trends(db: Session, user_id: int, today: date, weeks: int = 8, tz_offset_minutes: int = 0) -> dict:
    week_start = today - timedelta(days=today.weekday())
    starts = [week_start - timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]
    buckets = {
        s: {
            "week_start": s.isoformat(),
            "graded_answers": 0,
            "correct": 0,
            "concepts": set(),
            "active_days": set(),
        }
        for s in starts
    }
    latest_p: dict[str, float] = {}
    snapshots: dict[date, float | None] = {}
    events = _events(db, user_id)
    i = 0
    for s in starts:
        week_end = s + timedelta(days=7)
        while i < len(events) and _local(events[i].created_at, tz_offset_minutes).date() < week_end:
            e = events[i]
            local = _local(e.created_at, tz_offset_minutes).date()
            if local >= s:
                b = buckets[s]
                b["graded_answers"] += 1
                b["correct"] += 1 if e.correct else 0
                b["concepts"].add(e.concept_id)
                b["active_days"].add(local)
            if e.p_after is not None:
                latest_p[e.concept_id] = e.p_after
            i += 1
        snapshots[s] = sum(latest_p.values()) / len(latest_p) if latest_p else None
    out = []
    for s in starts:
        b = buckets[s]
        out.append(
            {
                "week_start": b["week_start"],
                "graded_answers": b["graded_answers"],
                "correct": b["correct"],
                "accuracy": b["correct"] / b["graded_answers"] if b["graded_answers"] else None,
                "concepts_practised": len(b["concepts"]),
                "active_days": len(b["active_days"]),
                # Mean estimated knowledge over all concepts with evidence by the end of the week.
                "estimate": snapshots[s],
            }
        )
    return {"weeks": out}


# --- Activity level --------------------------------------------------------------------


def activity_level(db: Session, user_id: int) -> dict:
    counts = defaultdict(int)
    for (source,) in db.execute(select(EvidenceEvent.source).where(EvidenceEvent.user_id == user_id)):
        counts[source] += 1
    n_completed = db.scalar(
        select(func.count(LearningSession.id)).where(
            LearningSession.user_id == user_id, LearningSession.status == "completed"
        )
    )
    n_flash = db.scalar(select(func.count(FlashcardReview.id)).where(FlashcardReview.user_id == user_id))
    xp = (
        counts["session"] * XP_RULES["session_answer"]
        + n_completed * XP_RULES["session_completed"]
        + counts["diagnostic"] * XP_RULES["diagnostic_answer"]
        + counts["rapid_round"] * XP_RULES["rapid_answer"]
        + n_flash * XP_RULES["flashcard_review"]
    )
    level, floor_xp = 1, 0
    while xp >= floor_xp + 100 * level:
        floor_xp += 100 * level
        level += 1
    return {
        "xp": xp,
        "level": level,
        "level_floor": floor_xp,
        "next_level_at": floor_xp + 100 * level,
        "note": "Activity level reflects how much you have practised, not what you know. Mastery is "
        "measured separately, from your answers.",
    }


# --- PTM / SWOT ----------------------------------------------------------------------------


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{round(x * 100)}%"


def ptm_report(
    db: Session,
    state: LearnerState,
    upcoming: list[dict],
    recommendations: list[dict],
    tz_offset_minutes: int = 0,
) -> dict:
    now = state.now
    events = _events(db, state.user_id)
    recent_cut = now - timedelta(days=14)
    prior_cut = now - timedelta(days=28)

    subjects = []
    for s in curriculum.subjects():
        concepts = state.by_subject(s["id"])
        if not concepts:
            continue
        summary = state.subject_summary(s["id"])
        sub_events = [e for e in events if any(e.concept_id == c.id for c in concepts)]
        recent = [e for e in sub_events if _naive(e.created_at) >= recent_cut]
        prior = [e for e in sub_events if prior_cut <= _naive(e.created_at) < recent_cut]
        acc_recent = sum(e.correct for e in recent) / len(recent) if recent else None
        acc_prior = sum(e.correct for e in prior) / len(prior) if prior else None
        trend = None
        if acc_recent is not None and acc_prior is not None and len(recent) >= 3 and len(prior) >= 3:
            diff = acc_recent - acc_prior
            trend = "improving" if diff >= 0.1 else "declining" if diff <= -0.1 else "steady"
        subjects.append(
            {
                "id": s["id"],
                "name": s["name"],
                "short_name": s["short_name"],
                **summary,
                "recent_attempts": len(recent),
                "recent_accuracy": acc_recent,
                "trend": trend,
                "weak_concepts": [c.name for c in concepts if c.status == "needs_review"],
            }
        )

    strengths, weaknesses, opportunities, threats = [], [], [], []
    for c in state.assessed():
        if c.status == "mastered":
            strengths.append(
                {
                    "concept": c.name,
                    "topic": c.topic_title,
                    "subject": c.subject_name,
                    "text": f"{c.name} ({c.topic_title}): estimated {_pct(c.p_known)}; "
                    f"{sum(c.recent)} of the last {len(c.recent)} answers correct across "
                    f"{c.attempts} graded attempts.",
                    "sort": -(c.p_known or 0) - c.attempts / 100,
                }
            )
        if c.status == "needs_review":
            weaknesses.append(
                {
                    "concept": c.name,
                    "topic": c.topic_title,
                    "subject": c.subject_name,
                    "text": f"{c.name} ({c.topic_title}): estimated {_pct(c.p_known)}, "
                    f"with {c.recent_incorrect} "
                    f"incorrect among the last {len(c.recent)} answers.",
                    "sort": c.p_known or 0,
                }
            )
        if (
            c.attempts >= MIN_ATTEMPTS_FOR_TREND
            and c.first_p_before is not None
            and c.p_known is not None
            and c.p_known - c.first_p_before >= 0.15
            and c.status != "needs_review"
        ):
            opportunities.append(
                {
                    "concept": c.name,
                    "topic": c.topic_title,
                    "subject": c.subject_name,
                    "text": f"{c.name} improved from {_pct(c.first_p_before)} to {_pct(c.p_known)} across "
                    f"{c.attempts} graded answers{'; close to mastery' if c.status == 'learning' else ''}.",
                    "sort": -(c.p_known - c.first_p_before),
                }
            )
        if c.days_since is not None and c.days_since >= 14 and c.status != "mastered":
            threats.append(
                {
                    "concept": c.name,
                    "topic": c.topic_title,
                    "subject": c.subject_name,
                    "text": f"{c.name} ({c.subject_name}) has not been practised in "
                    f"{c.days_since} days and is "
                    f"not yet secure (estimated {_pct(c.p_known)}).",
                    "sort": -c.days_since,
                }
            )
    for cls in upcoming:
        summary = state.subject_summary(cls["subject_id"])
        if summary["needs_review"]:
            threats.append(
                {
                    "concept": None,
                    "topic": None,
                    "subject": cls.get("subject_name"),
                    "text": f"{cls.get('subject_name')} class {cls['when']}, "
                    f"with {summary['needs_review']} concept"
                    f"{'s' if summary['needs_review'] != 1 else ''} needing review in that subject.",
                    "sort": -100,
                }
            )

    def top(items):
        return [
            {k: v for k, v in i.items() if k != "sort"} for i in sorted(items, key=lambda i: i["sort"])[:5]
        ]

    overall = state.overall()
    active_days = {
        _local(e.created_at, tz_offset_minutes).date()
        for e in events
        if _naive(e.created_at) >= now - timedelta(days=30)
    }
    return {
        "overview": {**overall, "graded_answers": len(events), "active_days_30": len(active_days)},
        "subjects": subjects,
        "swot": {
            "strengths": top(strengths),
            "weaknesses": top(weaknesses),
            "opportunities": top(opportunities),
            "threats": top(threats),
        },
        "recommendations": recommendations,
        "evidence_note": "Every statement is derived from your recorded answers. Sections stay empty "
        "until there is enough evidence.",
    }
