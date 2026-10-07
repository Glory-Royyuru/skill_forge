"""The Teacher Agent: a deterministic DIAGNOSE -> TEACH -> ASSESS -> ADAPT
-> REPORT loop over the curriculum's question bank.

Session state is a plain JSON-serializable dict so it can be persisted
as-is (see :mod:`skillforge.teacher.store`). Every function here is pure
apart from mutating the state dict it is given: no randomness, no clock, no
I/O — the same answers always produce the same session and report.

Rules, kept deliberately simple and explainable:

* DIAGNOSE — the starting level comes from the student's previous mastery
  of the topic (none or < 80% -> Foundational, >= 80% -> Intermediate). The
  first question is a baseline probe at that level.
* TEACH — the topic lesson is delivered up front; when a concept is missed
  twice the Teacher re-teaches it with the concept's review note.
* ASSESS — each answer is checked against the answer key and recorded
  per concept.
* ADAPT — correct: mastery rises (more for harder questions) and difficulty
  steps up. Incorrect: mastery drops slightly and difficulty steps down,
  preferring a question on the same concept to reinforce it.
* LEARNER MODEL (supporting signal, optional) — a Bayesian Knowledge Tracing
  estimate of P(known) per concept (see `learner_model.py`). It chooses
  which concept to target next (the least-known one) and, when a correct
  answer still leaves the concept unlikely to be known (a probable guess),
  keeps the next question on that concept. Difficulty steps, verdicts,
  mastery, and the report never depend on it.
* REPORT — score, mastery, per-concept status, and a recommendation.
"""

from __future__ import annotations

from typing import Any

from skillforge.teacher.curriculum import LEVEL_NAMES, SUBJECTS, get_topic, public_question, topic_ids
from skillforge.teacher.learner_model import LearnerModel, get_learner_model

QUESTIONS_PER_SESSION = 5
MAX_LEVEL = 3
MASTERY_GAIN_BASE = 0.10
MASTERY_GAIN_PER_LEVEL = 0.05
MASTERY_LOSS = 0.05
ADVANCED_START_THRESHOLD = 0.8
PROFICIENT = 0.8
DEVELOPING = 0.5

# Below this P(known), a correct answer is treated as a possible guess and the
# Teacher stays on the concept to confirm it.
GUESS_CONFIRM_THRESHOLD = 0.5
_CONFIGURED = object()

_PRAISE = ["Correct.", "Exactly right.", "Well reasoned.", "That's right.", "Spot on."]


class TeacherError(ValueError):
    """Raised for invalid session operations (unknown topic, wrong question, ...)."""


# --- Helpers ---------------------------------------------------------------


def _topic(state: dict) -> dict:
    found = get_topic(state["topic_id"])
    if found is None:
        raise TeacherError(f"unknown topic: {state['topic_id']}")
    return found[1]


def _question(topic: dict, question_id: str) -> dict:
    return next(q for q in topic["questions"] if q["id"] == question_id)


def _model(state: dict) -> LearnerModel | None:
    lm = state.get("learner_model")
    return get_learner_model(lm["name"]) if lm else None


def _knowledge(state: dict) -> dict[str, float] | None:
    lm = state.get("learner_model")
    return lm["knowledge"] if lm else None


def _log(state: dict, stage: str, text: str) -> None:
    state["log"].append({"stage": stage, "text": text})


def concept_status(attempted: int, correct: int, best_correct_level: int = 0) -> str:
    """strong / developing / weak for one concept's record in a session."""
    wrong = attempted - correct
    if attempted == 0:
        return "not_covered"
    if wrong >= 2 or (wrong >= 1 and correct == 0):
        return "weak"
    if wrong == 0 and (correct >= 2 or best_correct_level >= MAX_LEVEL):
        return "strong"
    return "developing"


def _concept_record(state: dict, concept: str) -> dict:
    return state["concept_stats"].setdefault(concept, {"attempted": 0, "correct": 0, "best_level": 0})


def _status_of(state: dict, concept: str) -> str:
    r = state["concept_stats"].get(concept)
    if r is None:
        return "not_covered"
    return concept_status(r["attempted"], r["correct"], r["best_level"])


def band(mastery: float) -> str:
    if mastery >= PROFICIENT:
        return "Proficient"
    if mastery >= DEVELOPING:
        return "Developing"
    return "Beginning"


# --- Question selection ------------------------------------------------------


def _pick_next(state: dict, topic: dict, reinforce_concept: str | None, prefer_harder: bool) -> dict | None:
    """Choose the next unasked question for the current level.

    Ordering: closest difficulty to the target level; on ties, harder after a
    correct answer and easier after a miss; then the concept to reinforce (if
    any); otherwise the concept the learner model considers least known (or,
    with no learner model, the least-practiced concept); then bank order.
    """
    asked = set(state["asked"])
    remaining = [(i, q) for i, q in enumerate(topic["questions"]) if q["id"] not in asked]
    if not remaining:
        return None
    target = state["level"]
    knowledge = _knowledge(state)

    def key(item: tuple[int, dict]) -> tuple:
        i, q = item
        distance = abs(q["difficulty"] - target)
        direction = -q["difficulty"] if prefer_harder else q["difficulty"]
        attempted = state["concept_stats"].get(q["concept"], {}).get("attempted", 0)
        if reinforce_concept is not None:
            concept_rank: tuple = (0 if q["concept"] == reinforce_concept else 1,)
        elif knowledge is not None:
            concept_rank = (knowledge.get(q["concept"], 0.0), attempted)
        else:
            concept_rank = (attempted,)
        return (distance, direction, concept_rank, i)

    return min(remaining, key=key)[1]


# --- DIAGNOSE + TEACH --------------------------------------------------------


def start_session(
    topic_id: str,
    prior_mastery: float | None = None,
    prior_knowledge: dict[str, float] | None = None,
    learner_model: LearnerModel | None | object = _CONFIGURED,
) -> dict:
    """Create a new session for a topic. `prior_mastery` / `prior_knowledge`
    come from the student's most recent completed session on this topic, if
    any. `learner_model` defaults to the configured one; pass None to run
    without it.
    """
    model = get_learner_model() if learner_model is _CONFIGURED else learner_model
    found = get_topic(topic_id)
    if found is None:
        raise TeacherError(f"unknown topic: {topic_id}")
    subject, topic = found

    if prior_mastery is not None and prior_mastery >= ADVANCED_START_THRESHOLD:
        level = 2
    else:
        level = 1

    state: dict[str, Any] = {
        "topic_id": topic_id,
        "subject_id": subject["id"],
        "status": "active",
        "stage": "teach",
        "level": level,
        "starting_level": level,
        "prior_mastery": prior_mastery,
        "max_questions": min(QUESTIONS_PER_SESSION, len(topic["questions"])),
        "asked": [],
        "current_question_id": None,
        "answers": [],
        "mastery": 0.0,
        "concept_stats": {},
        "learner_model": None,
        "log": [],
    }
    if model is not None:
        state["learner_model"] = {
            "name": model.name,
            "label": model.label,
            "knowledge": model.init(list(topic["concepts"]), prior_knowledge),
        }

    if prior_mastery is None:
        _log(state, "diagnose", f"No previous sessions on {topic['title']}. Starting with a foundational "
             "baseline question.")
    elif level == 2:
        _log(state, "diagnose", f"Previous mastery was {round(prior_mastery * 100)}%. Skipping the basics "
             "and starting at the Intermediate level.")
    else:
        _log(state, "diagnose", f"Previous mastery was {round(prior_mastery * 100)}%. Starting at the "
             "Foundational level to rebuild the base.")
    if model is not None and prior_knowledge:
        _log(state, "diagnose", "Learner model restored your concept estimates from last time.")
    _log(state, "teach", f"Delivered the core lesson on {topic['title']} "
         f"({len(topic['concepts'])} key concepts).")

    first = _pick_next(state, topic, reinforce_concept=None, prefer_harder=False)
    state["current_question_id"] = first["id"]
    state["asked"].append(first["id"])
    return state


# --- ASSESS + ADAPT ----------------------------------------------------------


def submit_answer(state: dict, question_id: str, choice: int) -> dict:
    """Grade an answer, update mastery/difficulty, choose the next question,
    and return the Teacher's feedback. Mutates `state`.
    """
    if state["status"] != "active":
        raise TeacherError("this session is already complete")
    if question_id != state["current_question_id"]:
        raise TeacherError("that is not the current question")
    topic = _topic(state)
    q = _question(topic, question_id)
    if not isinstance(choice, int) or not 0 <= choice < len(q["options"]):
        raise TeacherError("choice is out of range")

    concept = q["concept"]
    concept_name = topic["concepts"][concept]["name"]
    record = _concept_record(state, concept)
    missed_before = record["attempted"] - record["correct"]
    status_before = _status_of(state, concept)
    correct = choice == q["answer"]
    number = len(state["answers"]) + 1

    # ASSESS
    model, knowledge = _model(state), _knowledge(state)
    lm_feedback = None
    if model is not None:
        known_before = knowledge.get(concept, 0.0)
        predicted = model.predict_correct(knowledge, concept, q["difficulty"])
        known_after = model.update(knowledge, concept, q["difficulty"], correct)
        lm_feedback = {
            "label": state["learner_model"]["label"],
            "concept_name": concept_name,
            "predicted_correct": predicted,
            "known_before": known_before,
            "known_after": known_after,
        }
    record["attempted"] += 1
    if correct:
        record["correct"] += 1
        record["best_level"] = max(record["best_level"], q["difficulty"])
    if correct:
        verdict = "correct"
    elif missed_before >= 1:
        verdict = "needs_review"
    else:
        verdict = "incorrect"

    mastery_before = state["mastery"]
    if correct:
        gain = MASTERY_GAIN_BASE + MASTERY_GAIN_PER_LEVEL * q["difficulty"]
        state["mastery"] = round(min(1.0, mastery_before + gain), 4)
    else:
        state["mastery"] = round(max(0.0, mastery_before - MASTERY_LOSS), 4)

    state["answers"].append(
        {
            "question_id": q["id"],
            "concept": concept,
            "difficulty": q["difficulty"],
            "choice": choice,
            "correct_choice": q["answer"],
            "correct": correct,
            "verdict": verdict,
        }
    )
    result_word = "correct" if correct else "incorrect"
    _log(state, "assess", f"Q{number} · {concept_name} ({LEVEL_NAMES[q['difficulty']]}): {result_word}.")

    status_after = _status_of(state, concept)
    if status_after != status_before:
        if status_after == "weak":
            _log(state, "assess", f"Flagged {concept_name} as an area to review.")
        elif status_after == "strong":
            _log(state, "assess", f"Marked {concept_name} as a strength.")

    # ADAPT: aim one level up after a correct answer, one down after a miss.
    # The level then follows the question actually chosen, since the bank
    # may have run out of questions at the target level.
    from_level = q["difficulty"]
    state["level"] = min(MAX_LEVEL, from_level + 1) if correct else max(1, from_level - 1)

    # A correct answer the learner model still doubts (likely a guess) keeps
    # the next question on the same concept.
    confirm = correct and lm_feedback is not None and lm_feedback["known_after"] < GUESS_CONFIRM_THRESHOLD
    reinforce = concept if (not correct or confirm) else None

    is_last = len(state["answers"]) >= state["max_questions"]
    next_q = None
    if not is_last:
        next_q = _pick_next(state, topic, reinforce_concept=reinforce, prefer_harder=correct)
        is_last = next_q is None
    to_level = next_q["difficulty"] if next_q is not None else state["level"]
    state["level"] = to_level

    if is_last:
        transition = "That completes this session. I'll put together your learning report."
        direction = "complete"
    elif to_level > from_level:
        direction = "up"
        if confirm and next_q["concept"] == concept:
            transition = "Let's move one level deeper on the same idea to make sure it's secure."
        elif correct:
            transition = "Let's move one level deeper."
        else:
            transition = "Let's look at this idea from a more challenging angle."
    elif to_level < from_level:
        direction = "down"
        transition = ("Let's reinforce that distinction with a simpler question." if not correct
                      else "Let's consolidate with a related question.")
    elif correct:
        direction = "hold"
        transition = ("You're already at the advanced level, so let's keep the challenge high."
                      if to_level == MAX_LEVEL else "Let's consolidate at this level with another question.")
    else:
        direction = "hold"
        transition = ("Let's try another foundational question to reinforce it." if to_level == 1
                      else "Let's try another question at this level to reinforce it.")

    if direction == "complete":
        _log(state, "adapt", "Question budget reached. Moving to the report.")
    elif direction == "hold":
        _log(state, "adapt", f"Holding difficulty at {LEVEL_NAMES[to_level]}.")
    else:
        _log(state, "adapt", f"Difficulty {LEVEL_NAMES[from_level]} → {LEVEL_NAMES[to_level]}.")
    if next_q is not None and reinforce == concept and next_q["concept"] == concept:
        _log(state, "adapt", f"Next question reinforces {concept_name}.")
    if lm_feedback is not None:
        _log(state, "adapt", f"Learner model: {concept_name} estimated "
             f"{round(lm_feedback['known_after'] * 100)}% known.")
        if next_q is not None:
            lm_feedback["next_concept_name"] = topic["concepts"][next_q["concept"]]["name"]
            lm_feedback["next_predicted_correct"] = model.predict_correct(
                knowledge, next_q["concept"], next_q["difficulty"]
            )
            if reinforce == concept and next_q["concept"] == concept:
                lm_feedback["targeting"] = "confirm" if confirm else "reinforce"
            else:
                lm_feedback["targeting"] = "weakest"

    if is_last:
        state["status"] = "completed"
        state["stage"] = "report"
        state["current_question_id"] = None
        _log(state, "report", "Learning report generated.")
    else:
        state["stage"] = "assess"
        state["current_question_id"] = next_q["id"]
        state["asked"].append(next_q["id"])

    # Teacher-style feedback
    chosen_text = q["options"][choice]
    correct_text = q["options"][q["answer"]]
    reteach = None
    if correct:
        headline = _PRAISE[(number - 1) % len(_PRAISE)]
        message = [f"You chose “{chosen_text}”. {q['explanation']}"]
        if missed_before >= 1:
            message.append(f"Good recovery — {concept_name.lower()} tripped you up earlier, and this time "
                           "you got it.")
        else:
            message.append(f"That tells me you have a working grasp of {concept_name.lower()}.")
    elif verdict == "needs_review":
        headline = "Needs review."
        reteach = topic["concepts"][concept]["reteach"]
        message = [
            f"You chose “{chosen_text}”, but the answer is “{correct_text}”. {q['explanation']}",
            f"This is the second time {concept_name.lower()} has caused trouble, so I'm marking it for "
            "review. Here's the key idea again:",
        ]
    else:
        headline = "Not quite."
        why = q.get("why_wrong", {}).get(choice)
        if why:
            message = [f"{why} The answer is “{correct_text}”. {q['explanation']}"]
        else:
            message = [f"You chose “{chosen_text}”, but the answer is “{correct_text}”. {q['explanation']}"]

    return {
        "question_id": q["id"],
        "verdict": verdict,
        "correct": correct,
        "choice": choice,
        "correct_choice": q["answer"],
        "headline": headline,
        "message": message,
        "reteach": reteach,
        "transition": transition,
        "concept": concept,
        "concept_name": concept_name,
        "adaptation": {
            "direction": direction,
            "from_level": from_level,
            "to_level": to_level,
            "from_label": LEVEL_NAMES[from_level],
            "to_label": LEVEL_NAMES[to_level],
        },
        "learner_model": lm_feedback,
        "mastery_before": mastery_before,
        "mastery_after": state["mastery"],
        "is_last": is_last,
    }


# --- Views -------------------------------------------------------------------


def _concepts_view(state: dict, topic: dict) -> list[dict]:
    knowledge = _knowledge(state)
    out = []
    for cid, c in topic["concepts"].items():
        r = state["concept_stats"].get(cid, {"attempted": 0, "correct": 0, "best_level": 0})
        out.append(
            {
                "id": cid,
                "name": c["name"],
                "attempted": r["attempted"],
                "correct": r["correct"],
                "status": concept_status(r["attempted"], r["correct"], r["best_level"]),
                "estimate": knowledge.get(cid) if knowledge is not None else None,
            }
        )
    return out


def teacher_status(state: dict, topic: dict) -> str:
    if state["status"] == "completed":
        return "Session complete. Your learning report is ready."
    q = _question(topic, state["current_question_id"])
    concept = topic["concepts"][q["concept"]]["name"]
    if not state["answers"]:
        return f"Diagnosing your starting point with a baseline question on {concept.lower()}."
    last = state["answers"][-1]
    if not last["correct"] and last["concept"] == q["concept"]:
        return f"Reinforcing {concept.lower()} at the {LEVEL_NAMES[q['difficulty']]} level."
    return f"Assessing {concept.lower()} at the {LEVEL_NAMES[q['difficulty']]} level."


def session_view(state: dict) -> dict:
    """Everything the session screen needs, with no answer key for the open
    question."""
    subject, topic = get_topic(state["topic_id"])
    current = None
    if state["current_question_id"] is not None:
        current = public_question(topic, _question(topic, state["current_question_id"]))
    answered = len(state["answers"])
    correct = sum(1 for a in state["answers"] if a["correct"])
    lm = None
    model, knowledge = _model(state), _knowledge(state)
    if model is not None:
        lm = {"label": state["learner_model"]["label"], "predicted_correct": None}
        if current is not None:
            lm["predicted_correct"] = model.predict_correct(
                knowledge, current["concept"], current["difficulty"]
            )
    return {
        "topic_id": topic["id"],
        "topic_title": topic["title"],
        "subject_id": subject["id"],
        "subject_name": subject["name"],
        "status": state["status"],
        "stage": state["stage"],
        "lesson": topic["lesson"],
        "level": state["level"],
        "level_label": LEVEL_NAMES[state["level"]],
        "mastery": state["mastery"],
        "question_number": min(answered + 1, state["max_questions"]),
        "max_questions": state["max_questions"],
        "answered": answered,
        "correct": correct,
        "results": [a["verdict"] for a in state["answers"]],
        "current_question": current,
        "concepts": _concepts_view(state, topic),
        "teacher_status": teacher_status(state, topic),
        "learner_model": lm,
        "log": state["log"],
    }


# --- REPORT ------------------------------------------------------------------


def _next_topic_after(topic_id: str) -> str:
    ids = topic_ids()
    return ids[(ids.index(topic_id) + 1) % len(ids)]


def _same_subject_next(topic_id: str) -> str | None:
    for s in SUBJECTS:
        ids = [t["id"] for t in s["topics"]]
        if topic_id in ids:
            i = ids.index(topic_id)
            return ids[i + 1] if i + 1 < len(ids) else None
    return None


def build_report(state: dict) -> dict:
    subject, topic = get_topic(state["topic_id"])
    answers = state["answers"]
    attempted = len(answers)
    correct = sum(1 for a in answers if a["correct"])
    score = correct / attempted if attempted else 0.0
    mastery = state["mastery"]
    concepts = _concepts_view(state, topic)
    strengths = [c["name"] for c in concepts if c["status"] == "strong"]
    weak = [c["name"] for c in concepts if c["status"] == "weak"]
    developing = [c["name"] for c in concepts if c["status"] == "developing"]
    highest = max((a["difficulty"] for a in answers if a["correct"]), default=0)

    # Recommendation
    if mastery >= PROFICIENT and not weak:
        action = "advance"
        next_id = _same_subject_next(topic["id"]) or _next_topic_after(topic["id"])
    elif mastery >= DEVELOPING and not weak:
        action = "practice"
        next_id = _same_subject_next(topic["id"]) or _next_topic_after(topic["id"])
    else:
        action = "review"
        next_id = topic["id"]
    next_subject, next_topic = get_topic(next_id)

    if action == "advance":
        headline = f"Ready to move on to {next_topic['title']}"
        text = (f"You've shown solid command of {topic['title'].lower()}, including at the "
                f"{LEVEL_NAMES[max(highest, 1)]} level. Build on it with {next_topic['title']}.")
    elif action == "practice":
        focus = f" Keep an eye on {', '.join(n.lower() for n in developing)}." if developing else ""
        headline = f"Continue to {next_topic['title']}, with a quick review first"
        text = (f"You have a reasonable foundation in {topic['title'].lower()} but haven't fully secured it."
                f"{focus} Re-read the key points, then continue with {next_topic['title']}.")
    else:
        focus = ", ".join(n.lower() for n in weak) if weak else "the core concepts"
        headline = f"Revisit {topic['title']} before moving on"
        text = (f"Spend a little more time on {focus}. Re-read the lesson, then retake this session — "
                "I'll start you at the foundational level again.")

    # Summary paragraph
    level_reached = LEVEL_NAMES[highest] if highest else "Foundational"
    parts = [f"You answered {correct} of {attempted} questions correctly"
             + (f" and worked up to the {level_reached} level." if highest else ".")]
    if strengths:
        parts.append(f"You were consistently strong on {_join(strengths)}.")
    if weak:
        parts.append(f"{_join(weak, capitalize=True)} {'need' if len(weak) > 1 else 'needs'} more practice.")
    elif developing:
        verb = "are" if len(developing) > 1 else "is"
        parts.append(f"{_join(developing, capitalize=True)} {verb} developing but not yet secure.")
    summary = " ".join(parts)

    review = []
    for i, a in enumerate(answers, start=1):
        q = _question(topic, a["question_id"])
        review.append(
            {
                "number": i,
                "prompt": q["prompt"],
                "concept_name": topic["concepts"][a["concept"]]["name"],
                "difficulty_label": LEVEL_NAMES[a["difficulty"]],
                "your_answer": q["options"][a["choice"]],
                "correct_answer": q["options"][a["correct_choice"]],
                "correct": a["correct"],
                "verdict": a["verdict"],
                "explanation": q["explanation"],
            }
        )

    return {
        "topic_id": topic["id"],
        "topic_title": topic["title"],
        "subject_name": subject["name"],
        "complete": state["status"] == "completed",
        "score": score,
        "mastery": mastery,
        "band": band(mastery),
        "correct": correct,
        "attempted": attempted,
        "starting_level_label": LEVEL_NAMES[state["starting_level"]],
        "highest_level_label": LEVEL_NAMES[highest] if highest else None,
        "concepts": concepts,
        "strengths": strengths,
        "weak_areas": weak,
        "developing": developing,
        "summary": summary,
        "recommendation": {
            "action": action,
            "headline": headline,
            "text": text,
            "next_topic_id": next_topic["id"],
            "next_topic_title": next_topic["title"],
            "next_subject_name": next_subject["name"],
        },
        "review": review,
        "learner_model": (
            {"label": state["learner_model"]["label"]} if state.get("learner_model") else None
        ),
    }


def _join(names: list[str], capitalize: bool = False) -> str:
    items = [n.lower() for n in names]
    if capitalize and items:
        items[0] = items[0][0].upper() + items[0][1:]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]
