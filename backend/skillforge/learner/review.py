"""Student Performance Review — the full PTM-mode report.

A teacher-style review of ONE student's own record, built deterministically
from persisted evidence (evidence_events, learning_sessions, diagnostics,
rapid_rounds, flashcard_reviews) and the learner state. No language model,
no population data, nothing estimated that is not labelled as such.

Every section states its evidence threshold and reports "too early" below
it, so nothing is concluded from one or two answers:

- a subject is assessed only with ≥ MIN_SUBJECT_ANSWERS graded answers;
- a cognitive type or difficulty level is shown with ≥ MIN_BUCKET_ANSWERS;
- a difficulty level is "demonstrated" with ≥ MIN_BUCKET_ANSWERS answers at
  ≥ RELIABLE_ACCURACY accuracy;
- a subject trend compares its last TREND_WINDOW answers with the
  TREND_WINDOW before them (needs 2 × TREND_WINDOW answers);
- behaviour claims about consistency need ≥ MIN_ACTIVE_DAYS active days.

"Assessment score" (share correct in a sitting) and "estimated mastery"
(BKT knowledge estimate per concept) are reported separately on purpose:
they are different measurements.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from skillforge.db.models import Diagnostic, EvidenceEvent, FlashcardReview, LearningSession, RapidRound
from skillforge.learner import insights
from skillforge.learner.state import ConceptState, LearnerState, topic_status
from skillforge.teacher import curriculum
from skillforge.teacher.curriculum import LEVEL_NAMES

MIN_SUBJECT_ANSWERS = 3
MIN_BUCKET_ANSWERS = 3
RELIABLE_ACCURACY = 2 / 3
TREND_WINDOW = 5
TREND_DELTA = 0.15
MIN_ACTIVE_DAYS = 3
COGNITIVE_LABELS = {"recall": "Recall", "understand": "Understand", "apply": "Apply", "analyze": "Analyze"}
SUBJECT_STATUS = {
    "too_early": "Too early to assess",
    "needs_attention": "Needs attention",
    "developing": "Developing",
    "strong": "Strong",
}


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{round(x * 100)}%"


def _acc(correct: int, attempts: int) -> float | None:
    return correct / attempts if attempts else None


def _iso(dt) -> str | None:
    return insights._naive(dt).isoformat() + "Z" if dt else None


# --- Per-concept detail -------------------------------------------------------------


def _concept_trajectory(events: list[EvidenceEvent]) -> list[float]:
    """Estimated knowledge over time for one concept: the estimate before the
    first answer, then after each answer, sampled to at most four points."""
    points = [events[0].p_before] + [e.p_after for e in events]
    points = [p for p in points if p is not None]
    if len(points) <= 4:
        return [round(p, 4) for p in points]
    idx = sorted({0, len(points) // 3, (2 * len(points)) // 3, len(points) - 1})
    return [round(points[i], 4) for i in idx]


def _concept_action(c: ConceptState) -> dict:
    """A deterministic next step for one concept, with the session it opens."""
    if c.status == "not_started":
        return {"text": "Start this concept in a Teacher session", "minutes": 8, "difficulty": 1}
    if c.status == "needs_review":
        return {"text": "Review the key idea, then practise at Foundational", "minutes": 10, "difficulty": 1}
    if c.status == "mastered":
        return {"text": "Revisit with one Advanced question in a week", "minutes": 4, "difficulty": 3}
    if (c.p_known or 0) < 0.6:
        return {"text": "Practise at Intermediate to build the estimate", "minutes": 8, "difficulty": 2}
    return {"text": "Try an Advanced question to confirm it", "minutes": 6, "difficulty": 3}


def _concept_detail(c: ConceptState, events: list[EvidenceEvent]) -> dict:
    cog = {
        k: {"attempts": a, "correct": n, "accuracy": _acc(n, a)}
        for k, (a, n) in sorted(c.by_cognitive.items())
    }
    trajectory = _concept_trajectory(events) if events else []
    action = _concept_action(c)
    return {
        "id": c.id,
        "key": c.key,
        "name": c.name,
        "topic_id": c.topic_id,
        "status": c.status,
        "p_known": c.p_known if c.attempts else None,
        "confidence": c.confidence,
        "attempts": c.attempts,
        "correct": c.correct,
        "recent_accuracy": c.recent_accuracy,
        "highest_level": LEVEL_NAMES.get(c.best_correct_difficulty) if c.best_correct_difficulty else None,
        "cognitive": cog,
        "last_practiced": _iso(c.last_practiced),
        "days_since": c.days_since,
        "trajectory": trajectory,
        "change": (trajectory[-1] - trajectory[0]) if len(trajectory) >= 2 and c.attempts >= 3 else None,
        "evidence": c.evidence_lines(),
        "action": {**action, "topic_id": c.topic_id, "concept": c.key},
    }


# --- Sections ------------------------------------------------------------------------


def _subject_trend(events: list[EvidenceEvent]) -> str | None:
    if len(events) < 2 * TREND_WINDOW:
        return None
    last = events[-TREND_WINDOW:]
    prev = events[-2 * TREND_WINDOW:-TREND_WINDOW]
    diff = sum(e.correct for e in last) / TREND_WINDOW - sum(e.correct for e in prev) / TREND_WINDOW
    return "improving" if diff >= TREND_DELTA else "declining" if diff <= -TREND_DELTA else "steady"


def _subject_status(summary: dict) -> str:
    if summary["attempts"] < MIN_SUBJECT_ANSWERS:
        return "too_early"
    if summary["needs_review"] or (summary["estimate"] or 0) < 0.5:
        return "needs_attention"
    if (summary["estimate"] or 0) >= 0.75:
        return "strong"
    return "developing"


def _subjects(state: LearnerState, events_by_concept: dict[str, list[EvidenceEvent]]) -> list[dict]:
    out = []
    for s in curriculum.subjects():
        concepts = state.by_subject(s["id"])
        summary = state.subject_summary(s["id"])
        sub_events = sorted(
            (e for c in concepts for e in events_by_concept.get(c.id, [])),
            key=lambda e: (e.created_at, e.id),
        )
        recent = sub_events[-10:]
        units: dict[int, dict] = {}
        for tid in curriculum.assessable_in_subject(s["id"]):
            _, topic = curriculum.get_topic(tid)
            tconcepts = state.by_topic(tid)
            unit = units.setdefault(
                topic["unit_number"],
                {"number": topic["unit_number"], "title": topic["unit_title"], "topics": []},
            )
            tsum = state.topic_summary(tid)
            unit["topics"].append(
                {
                    "id": tid,
                    "title": topic["title"],
                    "estimate": tsum["estimate"],
                    "assessed": tsum["assessed"],
                    "total": tsum["total"],
                    "attempts": tsum["attempts"],
                    "status": topic_status(tconcepts),
                    "concepts": [_concept_detail(c, events_by_concept.get(c.id, [])) for c in tconcepts],
                }
            )
        status = _subject_status(summary) if concepts else "no_bank"
        out.append(
            {
                "id": s["id"],
                "name": s["name"],
                "short_name": s["short_name"],
                "area": s.get("area", "vnr-aiml-r22"),
                "has_bank": bool(concepts),
                "estimate": summary["estimate"],
                "assessed": summary["assessed"],
                "total": summary["total"],
                "attempts": summary["attempts"],
                "correct": summary["correct"],
                "accuracy": _acc(summary["correct"], summary["attempts"]),
                "recent_attempts": len(recent),
                "recent_accuracy": _acc(sum(e.correct for e in recent), len(recent)),
                "trend": _subject_trend(sub_events),
                "mastered": summary["mastered"],
                "needs_review": summary["needs_review"],
                "status": status,
                "status_label": SUBJECT_STATUS.get(status, "No question bank yet"),
                "units": sorted(units.values(), key=lambda u: u["number"]),
            }
        )
    return out


def _assessment(db: Session, user_id: int, events: list[EvidenceEvent]) -> dict:
    sessions = db.scalars(
        select(LearningSession)
        .where(LearningSession.user_id == user_id, LearningSession.status == "completed")
        .order_by(LearningSession.completed_at)
    ).all()
    session_rows = []
    for ls in sessions:
        found = curriculum.get_topic(ls.topic_id)
        session_rows.append(
            {
                "id": ls.id,
                "topic_title": found[1]["title"] if found else ls.topic_id,
                "subject_name": found[0]["name"] if found else "",
                "completed_at": _iso(ls.completed_at),
                "correct": ls.correct_count,
                "attempted": ls.answered_count,
                "score": _acc(ls.correct_count, ls.answered_count),
            }
        )
    scored = [r for r in session_rows if r["attempted"]]
    diag = db.scalar(
        select(Diagnostic)
        .where(Diagnostic.user_id == user_id, Diagnostic.status == "completed")
        .order_by(Diagnostic.id.desc())
        .limit(1)
    )
    diagnostic = None
    if diag is not None:
        answered = [r for r in diag.responses if r.get("choice") is not None]
        diagnostic = {
            "completed_at": _iso(diag.completed_at),
            "questions": len(diag.question_ids),
            "answered": len(answered),
            "correct": sum(1 for r in answered if r.get("correct")),
            "skipped": len(diag.responses) - len(answered),
        }
    rounds = [r for r in db.scalars(select(RapidRound).where(RapidRound.user_id == user_id)) if r.responses]
    rapid_answers = [x for r in rounds for x in r.responses]
    times = [x["response_ms"] for x in rapid_answers if x.get("response_ms")]
    by_source = defaultdict(lambda: [0, 0])
    for e in events:
        by_source[e.source][0] += 1
        by_source[e.source][1] += 1 if e.correct else 0
    return {
        "sessions": session_rows[-10:],
        "sessions_completed": len(session_rows),
        "average_session_score": (
            sum(r["correct"] for r in scored) / sum(r["attempted"] for r in scored) if scored else None
        ),
        "diagnostic": diagnostic,
        "rapid": {
            "rounds": len(rounds),
            "answered": len(rapid_answers),
            "correct": sum(1 for x in rapid_answers if x.get("correct")),
            "accuracy": _acc(sum(1 for x in rapid_answers if x.get("correct")), len(rapid_answers)),
            "median_response_ms": int(median(times)) if times else None,
        },
        "accuracy_by_source": {
            k: {"attempts": a, "correct": c, "accuracy": _acc(c, a)}
            for k, (a, c) in sorted(by_source.items())
        },
        "note": "Assessment scores are the share of answers correct in a sitting. Estimated mastery is the "
        "Bayesian Knowledge Tracing estimate per concept, built across every graded answer. They are "
        "different measurements and can disagree.",
    }


def _cognitive(state: LearnerState) -> dict:
    totals = defaultdict(lambda: [0, 0])
    for c in state.concepts.values():
        for k, (a, n) in c.by_cognitive.items():
            totals[k][0] += a
            totals[k][1] += n
    rows = []
    for key, label in COGNITIVE_LABELS.items():
        a, n = totals.get(key, [0, 0])
        rows.append(
            {
                "type": key,
                "label": label,
                "attempts": a,
                "correct": n,
                "accuracy": _acc(n, a),
                "enough": a >= MIN_BUCKET_ANSWERS,
            }
        )
    shown = [r for r in rows if r["enough"]]
    summary = None
    if len(shown) >= 2:
        best = max(shown, key=lambda r: r["accuracy"])
        worst = min(shown, key=lambda r: r["accuracy"])
        if best["accuracy"] - worst["accuracy"] >= TREND_DELTA:
            summary = (
                f"{best['label']} questions ({_pct(best['accuracy'])}) are currently answered more reliably "
                f"than {worst['label'].lower()} questions ({_pct(worst['accuracy'])})."
            )
        else:
            summary = "Accuracy is similar across the question types with enough evidence."
    return {"rows": rows, "summary": summary, "min_answers": MIN_BUCKET_ANSWERS}


def _difficulty(state: LearnerState) -> dict:
    rows = []
    for level in (1, 2, 3):
        a = sum(c.by_difficulty.get(level, [0, 0])[0] for c in state.concepts.values())
        n = sum(c.by_difficulty.get(level, [0, 0])[1] for c in state.concepts.values())
        rows.append(
            {
                "level": level,
                "label": LEVEL_NAMES[level],
                "attempts": a,
                "correct": n,
                "accuracy": _acc(n, a),
                "demonstrated": a >= MIN_BUCKET_ANSWERS and (n / a) >= RELIABLE_ACCURACY,
                "enough": a >= MIN_BUCKET_ANSWERS,
            }
        )
    reliable = [r for r in rows if r["demonstrated"]]
    return {
        "rows": rows,
        "highest_demonstrated": reliable[-1]["label"] if reliable else None,
        "rule": f"A level counts as demonstrated after at least {MIN_BUCKET_ANSWERS} answers at it with "
        f"{round(RELIABLE_ACCURACY * 100)}% or more correct.",
    }


def _behaviour(db: Session, user_id: int, events: list[EvidenceEvent], tz: int, now) -> dict:
    days = sorted({insights._local(e.created_at, tz).date() for e in events})
    flash = db.scalars(select(FlashcardReview).where(FlashcardReview.user_id == user_id)).all()
    days = sorted(set(days) | {insights._local(f.created_at, tz).date() for f in flash})
    sessions = db.scalars(select(LearningSession).where(LearningSession.user_id == user_id)).all()
    durations = [
        (insights._naive(s.completed_at) - insights._naive(s.created_at)).total_seconds() / 60
        for s in sessions
        if s.status == "completed" and s.completed_at is not None
    ]
    # Sessions left open for hours are not "learning time"; exclude them.
    durations = [d for d in durations if 0 < d <= 180]
    longest_gap = max(((b - a).days for a, b in zip(days, days[1:], strict=False)), default=None)
    streak = best = 0
    for i, d in enumerate(days):
        streak = streak + 1 if i and (d - days[i - 1]).days == 1 else 1
        best = max(best, streak)
    span_weeks = max(1.0, ((days[-1] - days[0]).days + 1) / 7) if days else None
    seen: set[str] = set()
    revisits = 0
    for e in events:
        if e.concept_id in seen:
            revisits += 1
        seen.add(e.concept_id)
    ratings = defaultdict(int)
    for f in flash:
        ratings[f.rating] += 1
    rapid_rounds = sum(
        1 for r in db.scalars(select(RapidRound).where(RapidRound.user_id == user_id)) if r.responses
    )
    times = [e.response_ms for e in events if e.response_ms]
    enough = len(days) >= MIN_ACTIVE_DAYS
    last_30 = [d for d in days if d >= (insights._local(now, tz).date() - timedelta(days=29))]
    return {
        "active_days": len(days),
        "active_days_30": len(last_30),
        "first_active": days[0].isoformat() if days else None,
        "last_active": days[-1].isoformat() if days else None,
        "sessions_started": len(sessions),
        "sessions_completed": sum(1 for s in sessions if s.status == "completed"),
        "median_session_minutes": round(median(durations), 1) if len(durations) >= 2 else None,
        "days_per_week": round(len(days) / span_weeks, 1) if enough and span_weeks else None,
        "revision_answers": revisits,
        "flashcards": {
            "reviewed": len(flash),
            **{k: ratings.get(k, 0) for k in ("known", "review", "skipped")},
        },
        "rapid_rounds": rapid_rounds,
        "longest_streak": best if days else 0,
        "longest_gap_days": longest_gap if enough else None,
        "median_response_ms": int(median(times)) if len(times) >= MIN_BUCKET_ANSWERS else None,
        "enough": enough,
        "note": "Response time is shown as behaviour only; it never lowers a mastery estimate.",
    }


def _strengths_and_gaps(state: LearnerState, recs: list[dict]) -> tuple[list[dict], list[dict]]:
    strengths = []
    for c in state.assessed():
        reliable = (
            c.status == "mastered"
            or (
                (c.p_known or 0) >= 0.75
                and c.weight >= 3
                and (c.recent_accuracy or 0) >= RELIABLE_ACCURACY
                and c.best_correct_difficulty >= 2
                and c.status != "needs_review"
            )
        )
        if reliable:
            strengths.append(
                {
                    "concept": c.name,
                    "topic": c.topic_title,
                    "subject": c.subject_name,
                    "status": c.status,
                    "p_known": c.p_known,
                    "recent": f"{sum(c.recent)}/{len(c.recent)}",
                    "highest_level": LEVEL_NAMES.get(c.best_correct_difficulty),
                    "attempts": c.attempts,
                }
            )
    strengths.sort(key=lambda s: -(s["p_known"] or 0))

    by_concept = {(r.get("topic_id"), r.get("concept_key")): r for r in recs if r.get("concept_key")}
    gaps = []
    for c in state.assessed():
        if c.status != "needs_review":
            continue
        rec = by_concept.get((c.topic_id, c.key))
        action = _concept_action(c)
        gaps.append(
            {
                "concept": c.name,
                "topic": c.topic_title,
                "subject": c.subject_name,
                "p_known": c.p_known,
                "recent_accuracy": c.recent_accuracy,
                "recent": f"{sum(c.recent)}/{len(c.recent)}",
                "consecutive_incorrect": c.consecutive_incorrect,
                "suggestion": (
                    f"{rec['title']} — {rec['estimated_minutes']} min" if rec
                    else f"{action['text']} — {action['minutes']} min"
                ),
                "cta": {"topic_id": c.topic_id, "concept": c.key, "difficulty": 1},
            }
        )
    gaps.sort(key=lambda g: g["p_known"] or 0)
    return strengths[:6], gaps[:6]


def _progress(db: Session, state: LearnerState, subjects: list[dict], tz: int) -> dict:
    today = insights._local(state.now, tz).date()
    weeks = insights.trends(db, state.user_id, today, 8, tz)["weeks"]
    changes = []
    for s in subjects:
        for u in s["units"]:
            for t in u["topics"]:
                for c in t["concepts"]:
                    if c["change"] is not None:
                        changes.append(
                            {"concept": c["name"], "topic": t["title"], "subject": s["name"],
                             "trajectory": c["trajectory"], "change": c["change"], "attempts": c["attempts"]}
                        )
    changes.sort(key=lambda c: -c["change"])
    return {
        "weeks": weeks,
        "improvements": [c for c in changes if c["change"] >= 0.05][:5],
        "declines": [c for c in reversed(changes) if c["change"] <= -0.05][:3],
    }


def _summary_line(state: LearnerState) -> dict:
    o = state.overall()
    if o["attempts"] == 0:
        return {"key": "insufficient", "label": "Not enough evidence yet"}
    if o["attempts"] < 10:
        return {"key": "early", "label": "Early evidence"}
    est = o["estimate"] or 0
    if o["needs_review"] > o["mastered"] and est < 0.5:
        return {"key": "support", "label": "Needs support"}
    if est >= 0.75 and o["needs_review"] == 0:
        return {"key": "secure", "label": "Secure"}
    return {"key": "developing", "label": "Developing"}


def _teacher_summary(name: str, state: LearnerState, overview: dict, strengths, gaps, cognitive, difficulty,
                     actions) -> list[dict]:
    """A short, templated narrative. Every clause is filled from the numbers above."""
    o = state.overall()
    first = name.split()[0] if name else "The student"
    if o["attempts"] == 0:
        return [{"heading": "Overall assessment",
                 "text": f"{first} has no graded answers yet, so there is nothing to assess. A short "
                 "diagnostic or one Teacher session will start the record."}]
    paras = [{
        "heading": "Overall assessment",
        "text": (
            f"{first} has answered {o['attempts']} graded questions across {o['assessed']} of {o['total']} "
            f"concepts with a question bank ({_pct(o['coverage'])} coverage), with "
            f"{_pct(overview['accuracy'])} correct overall. The mean estimated mastery of the assessed "
            f"concepts is {_pct(o['estimate'])}; "
            f"{o['mastered']} concept{'s are' if o['mastered'] != 1 else ' is'} mastered and "
            f"{o['needs_review']} need{'s' if o['needs_review'] == 1 else ''} review."
            + (" This is early evidence, so conclusions are provisional." if o["attempts"] < 10 else "")
        ),
    }]
    demo = difficulty["highest_demonstrated"]
    paras.append({
        "heading": "Demonstrated",
        "text": (
            f"Reliable performance has been demonstrated up to the {demo} level."
            if demo
            else "No difficulty level has been answered reliably often enough to count as demonstrated yet."
        ) + (f" {cognitive['summary']}" if cognitive["summary"] else ""),
    })
    if strengths:
        names = ", ".join(s["concept"] for s in strengths[:3])
        paras.append({"heading": "Primary strengths", "text": f"Strongest evidence: {names}."})
    if gaps:
        names = ", ".join(g["concept"] for g in gaps[:3])
        paras.append({"heading": "Areas requiring attention",
                      "text": f"Repeated mistakes or low estimates on: {names}."})
    if actions:
        steps = "; ".join(f"{a['title']} ({a['estimated_minutes']} min)" for a in actions[:3])
        paras.append({"heading": "Recommended next steps", "text": steps + "."})
    return paras


# --- Entry point ---------------------------------------------------------------------------


def performance_review(
    db: Session,
    student: dict,
    state: LearnerState,
    upcoming: list[dict],
    recommendations: list[dict],
    tz_offset_minutes: int = 0,
) -> dict:
    events = db.scalars(
        select(EvidenceEvent)
        .where(EvidenceEvent.user_id == state.user_id)
        .order_by(EvidenceEvent.created_at, EvidenceEvent.id)
    ).all()
    events = [e for e in events if e.concept_id in state.concepts]
    by_concept: dict[str, list[EvidenceEvent]] = defaultdict(list)
    for e in events:
        by_concept[e.concept_id].append(e)

    subjects = _subjects(state, by_concept)
    assessment = _assessment(db, state.user_id, events)
    cognitive = _cognitive(state)
    difficulty = _difficulty(state)
    behaviour = _behaviour(db, state.user_id, events, tz_offset_minutes, state.now)
    strengths, gaps = _strengths_and_gaps(state, recommendations)
    progress = _progress(db, state, subjects, tz_offset_minutes)
    swot = insights.ptm_report(db, state, upcoming, recommendations, tz_offset_minutes)["swot"]
    o = state.overall()
    topic_statuses = [
        t["status"] for s in subjects for u in s["units"] for t in u["topics"]
    ]
    with_level = insights.activity_level(db, state.user_id)
    overview = {
        **_summary_line(state),
        "estimate": o["estimate"],
        "assessed": o["assessed"],
        "total": o["total"],
        "coverage": o["coverage"],
        "accuracy": _acc(o["correct"], o["attempts"]),
        "questions_attempted": o["attempts"],
        "correct": o["correct"],
        "sessions_completed": assessment["sessions_completed"],
        "concepts_mastered": o["mastered"],
        "concepts_needing_review": o["needs_review"],
        "topics_mastered": topic_statuses.count("mastered"),
        "topics_needing_review": topic_statuses.count("needs_review"),
        "active_days": behaviour["active_days"],
        "active_days_30": behaviour["active_days_30"],
        "recent_improvement": progress["improvements"][0] if progress["improvements"] else None,
        "activity_level": with_level,
        "has_evidence": o["attempts"] > 0,
    }
    return {
        "student": student,
        "generated_at": _iso(state.now),
        "overview": overview,
        "assessment": assessment,
        "subjects": subjects,
        "progress": progress,
        "strengths": strengths,
        "improvement_areas": gaps,
        "behaviour": behaviour,
        "cognitive": cognitive,
        "difficulty": difficulty,
        "swot": swot,
        "action_plan": recommendations[:5],
        "teacher_summary": _teacher_summary(
            student.get("name", ""), state, overview, strengths, gaps, cognitive, difficulty, recommendations
        ),
        "thresholds": {
            "subject_answers": MIN_SUBJECT_ANSWERS,
            "bucket_answers": MIN_BUCKET_ANSWERS,
            "reliable_accuracy": RELIABLE_ACCURACY,
            "trend_window": TREND_WINDOW,
            "active_days": MIN_ACTIVE_DAYS,
        },
        "evidence_note": "Every figure is computed from your own recorded answers and activity. Sections "
        "say 'too early' until there is enough evidence.",
    }
