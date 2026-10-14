import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { ErrorState, Icon, LevelMeter, Loading, useCountUp } from "../components/ui.jsx";
import { LoopPath } from "../components/world.jsx";
import { prefersReducedMotion } from "../components/motion.jsx";
import { STATUS_LABELS, navigate, pct, roman } from "../lib/router.js";

const LETTERS = ["A", "B", "C", "D", "E", "F"];
const LOOP = ["diagnose", "teach", "assess", "adapt", "report"];
const LOOP_LABELS = { diagnose: "Diagnose", teach: "Teach", assess: "Assess", adapt: "Adapt", report: "Report" };
const VERDICT_LABELS = { correct: "Correct", incorrect: "Incorrect", needs_review: "Needs review" };
const CONCEPT_MARK = { strong: "✓", developing: "◐", weak: "!", not_covered: "○" };
const STEP_MS = 380;

// Code-style prompts are written as "<code>\n\n<question>".
function Prompt({ text }) {
  if (!text.includes("\n")) return <p className="q-prompt">{text}</p>;
  const parts = text.split("\n\n");
  const question = parts.length > 1 ? parts.pop() : null;
  return (
    <div className="q-prompt">
      <pre className="code">{parts.join("\n\n")}</pre>
      {question && <p>{question}</p>}
    </div>
  );
}

// After a wrong answer the explanation reads in a fixed order: the correct
// answer, why it is correct, what to remember, the related concept, then
// verified further reading. The student's own choice is shown, but second.
// The tone is "here is what to take from this", never a penalty.
function WrongAnswerReview({ review }) {
  const rel = review.related;
  const link = `#/learn?subject=${encodeURIComponent(rel.subject_id)}&topic=${encodeURIComponent(rel.topic_id)}`;
  return (
    <div className="teach">
      <section className="teach-correct" aria-label="Correct answer">
        <span className="teach-n" aria-hidden="true">1</span>
        <div>
          <h4 className="teach-k">Correct answer</h4>
          <p className="teach-answer">
            <span className="ans-letter ok">{review.correct_answer.letter}</span>
            {review.correct_answer.text}
          </p>
          <p className="teach-yours">
            You chose <span className="ans-letter bad">{review.your_answer.letter}</span>
            <span className="teach-yours-t">{review.your_answer.text}</span>
          </p>
        </div>
      </section>
      <section className="teach-block">
        <span className="teach-n" aria-hidden="true">2</span>
        <div>
          <h4 className="teach-k">Why it is correct</h4>
          <p>{review.why}</p>
          {review.why_not_yours && (
            <p className="teach-aside">
              <strong>About {review.your_answer.letter}:</strong> {review.why_not_yours}
            </p>
          )}
        </div>
      </section>
      <section className="teach-block teach-remember">
        <span className="teach-n" aria-hidden="true">3</span>
        <div>
          <h4 className="teach-k">What to remember</h4>
          <p>{review.remember}</p>
        </div>
      </section>
      <section className="teach-block">
        <span className="teach-n" aria-hidden="true">4</span>
        <div>
          <h4 className="teach-k">Related concept</h4>
          <a className="teach-related" href={link} target="_blank" rel="noopener noreferrer">
            {rel.concept_name}
            <span className="teach-meta"> · {rel.topic_title} · opens Learn in a new tab</span>
          </a>
        </div>
      </section>
      {review.resources.length > 0 && (
        <section className="teach-block">
          <span className="teach-n" aria-hidden="true">5</span>
          <div>
            <h4 className="teach-k">Further reading</h4>
            <ul className="teach-res">
              {review.resources.map((r) => (
                <li key={r.url}>
                  <a href={r.url} target="_blank" rel="noopener noreferrer">
                    {r.title}
                  </a>
                  <span className="teach-meta"> · {r.publisher} · external site, new tab</span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}
      <p className="teach-note">A wrong answer is evidence, not a penalty: it tells the Teacher what to explain next.</p>
    </div>
  );
}

function Segments({ session, current }) {
  return (
    <div className="segments">
      {Array.from({ length: session.max_questions }, (_, i) => {
        const v = session.results[i];
        return <div key={i} className={`segment ${v ? `seg-${v}` : ""} ${i === current ? "seg-current" : ""}`} />;
      })}
    </div>
  );
}

function statusFor(phase, session, feedback, steps, stepIdx) {
  if (phase === "evaluating") return steps[Math.min(stepIdx, steps.length - 1)];
  if (phase === "feedback" && feedback) {
    if (feedback.is_last) return "Preparing your learning report";
    // Only claim reinforcement when the next question really revisits the
    // concept just missed (or a probable guess the learner model wants to confirm).
    const same = feedback.next_concept_name === feedback.concept_name;
    if (same && (!feedback.correct || feedback.learner_model?.targeting === "confirm"))
      return "Reinforcing this concept";
    if (feedback.adaptation.direction === "up") return "Preparing the next challenge";
    return "Adjusting difficulty";
  }
  if (session.answered === 0) return "Diagnosing your starting point";
  // The backend's status already knows whether this question revisits a missed concept.
  return session.teacher_status.startsWith("Reinforcing") ? "Reinforcing this concept" : "Assessing understanding";
}

export default function Session({ id }) {
  const [session, setSession] = useState(null);
  const [question, setQuestion] = useState(null); // the question on screen
  const [selected, setSelected] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [phase, setPhase] = useState("answering"); // answering | evaluating | feedback
  const [steps, setSteps] = useState([]);
  const [stepIdx, setStepIdx] = useState(0);
  const [error, setError] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [lessonOpen, setLessonOpen] = useState(true);
  const questionRef = useRef(null);
  const feedbackRef = useRef(null);
  const timers = useRef([]);
  const submitting = useRef(false);
  const shownAt = useRef(Date.now());
  useEffect(() => {
    shownAt.current = Date.now();
  }, [question?.id]);

  const mastery = useCountUp(session ? session.mastery : null, 800);

  const load = useCallback(() => {
    setError(null);
    api
      .getSession(id)
      .then((s) => {
        setSession(s);
        setQuestion(s.current_question);
        setLessonOpen(s.answered === 0);
      })
      .catch(setError);
  }, [id]);

  useEffect(load, [load]);
  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  const submit = useCallback(async () => {
    if (selected == null || phase !== "answering" || submitting.current) return;
    submitting.current = true; // a second Enter or click in the same tick must not answer twice
    setSubmitError(null);
    setPhase("evaluating");
    setSteps(["Assessing understanding"]);
    setStepIdx(0);
    try {
      // Response time is sent as a secondary signal; it never affects grading.
      const r = await api.answer(id, question.id, selected, Date.now() - shownAt.current);
      const fb = r.feedback;
      const seq = [
        "Assessing understanding",
        fb.correct ? "Confirming understanding" : "Identifying weak concept",
        fb.is_last ? "Preparing your learning report" : "Adjusting difficulty",
      ];
      setSteps(seq);
      seq.forEach((_, i) => timers.current.push(setTimeout(() => setStepIdx(i), i * STEP_MS)));
      timers.current.push(
        setTimeout(() => {
          setFeedback(fb);
          setSession(r.session);
          setPhase("feedback");
          // Move keyboard and screen-reader focus to the verdict, then bring it into view.
          setTimeout(() => {
            feedbackRef.current?.focus({ preventScroll: true });
            feedbackRef.current?.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "nearest" });
          }, 60);
        }, seq.length * STEP_MS)
      );
    } catch (e) {
      // Keep the question and the chosen answer on screen; say what failed.
      submitting.current = false;
      setPhase("answering");
      setSubmitError(e);
    }
  }, [id, question, selected, phase]);

  const next = useCallback(() => {
    if (!feedback) return;
    if (feedback.is_last) {
      navigate("report", id);
      return;
    }
    setQuestion(session.current_question);
    setSelected(null);
    setFeedback(null);
    setPhase("answering");
    setLessonOpen(false);
    setSubmitError(null);
    submitting.current = false;
    setTimeout(() => {
      questionRef.current?.focus({ preventScroll: true });
      questionRef.current?.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "start" });
    }, 60);
  }, [feedback, session, id]);

  // Keyboard: A–D / 1–4 to choose, arrow keys to move between options,
  // Enter to submit or continue. Enter on another button or link keeps its
  // own meaning, so the shortcut never fires twice.
  useEffect(() => {
    const onKey = (e) => {
      if (!question || e.metaKey || e.ctrlKey || e.altKey) return;
      const onControl = e.target.closest?.("a, button:not(.option), input, textarea, select, summary");
      const k = e.key.toUpperCase();
      if (phase === "answering") {
        const n = question.options.length;
        if ((e.key === "ArrowDown" || e.key === "ArrowUp") && e.target.closest?.(".options")) {
          e.preventDefault();
          const cur = selected ?? (e.key === "ArrowDown" ? -1 : n);
          const idx = (cur + (e.key === "ArrowDown" ? 1 : -1) + n) % n;
          setSelected(idx);
          questionRef.current?.querySelectorAll(".option")[idx]?.focus();
          return;
        }
        if (onControl) return;
        const idx = LETTERS.indexOf(k) >= 0 ? LETTERS.indexOf(k) : Number(k) - 1;
        if (idx >= 0 && idx < n) setSelected(idx);
        if (e.key === "Enter") {
          e.preventDefault();
          submit();
        }
      } else if (phase === "feedback" && e.key === "Enter" && !onControl) {
        e.preventDefault();
        next();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [question, phase, selected, submit, next]);

  if (error) return <ErrorState error={error} onRetry={load} />;
  if (!session) return <Loading label="Preparing your session…" />;

  if (session.status !== "active" && !feedback) {
    return (
      <div className="card center-card rise">
        <div className="card-body center-block">
          <h2 className="display">
            {session.status === "completed" ? "This session is complete" : "This session was replaced by a newer one"}
          </h2>
          <p className="muted">{session.topic_title}</p>
          <div className="hero-actions center">
            {session.status === "completed" && (
              <button className="btn btn-primary" onClick={() => navigate("report", id)}>
                View learning report
              </button>
            )}
            <button className="btn btn-secondary" onClick={() => navigate("dashboard")}>
              Back to dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  const stage =
    phase === "feedback"
      ? feedback.is_last
        ? "report"
        : "adapt"
      : phase === "evaluating"
        ? stepIdx >= 2
          ? "adapt"
          : "assess"
        : session.answered === 0
          ? "teach"
          : "assess";
  const qNumber = phase === "feedback" ? session.answered : session.answered + 1;
  const delta = feedback ? Math.round((feedback.mastery_after - feedback.mastery_before) * 100) : 0;
  const lm = session.learner_model;
  const status = statusFor(phase, session, feedback, steps, stepIdx);
  const lesson = session.lesson;
  const busy = phase === "evaluating";

  return (
    <>
      <div className="session-top rise">
        <div>
          <div className="crumbs">
            <button className="link-btn" onClick={() => navigate("learn", null, { subject: session.subject_id })}>
              {session.subject_name}
            </button>
            <span>/</span>
            <span>
              {session.unit_label} {roman(session.unit_number)}
            </span>
            <span>/</span>
            <span className="crumb-topic">{session.topic_title}</span>
          </div>
          <h1 className="display">{session.topic_title}</h1>
        </div>
        <LoopPath stages={LOOP.map((s) => LOOP_LABELS[s])} current={LOOP_LABELS[stage]} />
      </div>

      <div className="session-grid">
        <div className="session-main">
          <section className="card teacher-card rise">
            <div className="teacher-head">
              <div className={`teacher-avatar ${busy ? "thinking" : ""}`}>
                <Icon name="teacher" size={20} />
              </div>
              <div className="teacher-id">
                <div className="teacher-name">Teacher Agent</div>
                <div className="lesson-progress">
                  <span className="muted small">
                    Lesson progress · {session.answered} of {session.max_questions}
                  </span>
                  <Segments session={session} current={phase === "answering" ? session.answered : -1} />
                </div>
              </div>
              <button className="link-btn" onClick={() => setLessonOpen((o) => !o)}>
                {lessonOpen ? "Hide lesson" : "Review lesson"}
              </button>
            </div>
            {lessonOpen ? (
              <div className="lesson">
                <p className="lesson-intro">{lesson.intro}</p>
                {lesson.body.map((p, i) => (
                  <p key={i}>{p}</p>
                ))}
                <div className="key-points">
                  <div className="key-points-title">Key points</div>
                  <ul>
                    {lesson.key_points.map((k) => (
                      <li key={k}>
                        <Icon name="check" size={14} />
                        {k}
                      </li>
                    ))}
                  </ul>
                </div>
                {session.answered === 0 && (
                  <p className="lesson-handoff">
                    Let's see where you are. I'll start with a baseline question and adjust from there.
                  </p>
                )}
              </div>
            ) : (
              <p className="lesson-collapsed">{lesson.intro}</p>
            )}
          </section>

          {question && (
            <section className="card question-card" ref={questionRef} tabIndex={-1} aria-label={`Question ${qNumber} of ${session.max_questions}`}>
              <div className="q-enter" key={question.id}>
                <div className="card-body">
                  <div className="q-meta">
                    <span className="q-number">
                      Question {qNumber} <span className="muted">of {session.max_questions}</span>
                    </span>
                    <span className={`chip chip-level-${question.difficulty}`}>{question.difficulty_label}</span>
                    <span className="chip">{question.concept_name}</span>
                    {qNumber === 1 && <span className="chip chip-outline">Baseline</span>}
                  </div>
                  <Prompt text={question.prompt} />
                  <div className="options" role="radiogroup" aria-label="Answer options">
                    {question.options.map((opt, i) => {
                      let cls = "option";
                      if (feedback) {
                        if (i === feedback.correct_choice) cls += " is-correct";
                        else if (i === feedback.choice) cls += " is-wrong";
                        else cls += " is-dim";
                      } else if (selected === i) cls += " is-selected";
                      return (
                        <button
                          key={i}
                          className={cls}
                          role="radio"
                          aria-checked={selected === i}
                          disabled={phase !== "answering"}
                          onClick={() => setSelected(i)}
                        >
                          <span className="option-letter">{LETTERS[i]}</span>
                          <span className="option-text">{opt}</span>
                          {feedback && i === feedback.correct_choice && <Icon name="check" size={16} />}
                          {feedback && i === feedback.choice && i !== feedback.correct_choice && (
                            <Icon name="x" size={16} />
                          )}
                        </button>
                      );
                    })}
                  </div>
                  {phase !== "feedback" && (
                    <div className="q-actions">
                      {submitError ? (
                        <span className="q-error" role="alert">
                          {submitError.message} Your choice is kept; submit again when ready.
                        </span>
                      ) : (
                        <span className="muted small">
                          {selected == null ? "Choose an answer. Keys A–D or the arrow keys work too." : `Answer ${LETTERS[selected]} selected. Press Enter or Submit.`}
                        </span>
                      )}
                      <button className="btn btn-primary" disabled={selected == null || busy} onClick={submit}>
                        {busy ? (
                          <>
                            <span className="btn-spinner" /> Checking
                          </>
                        ) : (
                          "Submit Answer"
                        )}
                      </button>
                    </div>
                  )}
                </div>

                {feedback && (
                  <div className={`feedback fb-${feedback.verdict}`} ref={feedbackRef} tabIndex={-1} role="region" aria-label="Feedback on your answer">
                    <div className="feedback-head">
                      <span className={`verdict verdict-${feedback.verdict}`}>
                        <Icon
                          name={feedback.correct ? "check" : feedback.verdict === "needs_review" ? "flag" : "x"}
                          size={14}
                        />
                        {VERDICT_LABELS[feedback.verdict]}
                      </span>
                      {delta !== 0 && (
                        <span className={`gain ${delta > 0 ? "up" : "down"}`}>
                          {delta > 0 ? "+" : "−"}
                          {Math.abs(delta)} mastery
                        </span>
                      )}
                    </div>
                    <p className="feedback-headline display">{feedback.headline}</p>
                    {feedback.review ? (
                      <WrongAnswerReview review={feedback.review} />
                    ) : (
                      feedback.message.map((m, i) => (
                        <p key={i} className="feedback-text">
                          {m}
                        </p>
                      ))
                    )}
                    {feedback.reteach && !feedback.review && (
                      <div className="reteach">
                        <div className="reteach-title">Key idea · {feedback.concept_name}</div>
                        <p>{feedback.reteach}</p>
                      </div>
                    )}

                    {!feedback.is_last && (
                      <section className="next-step" aria-label="What happens next">
                        <h4 className="next-step-k">{feedback.correct ? "What happens next" : "Changing direction"}</h4>
                        <p className="next-step-t">{feedback.transition}</p>
                        <dl className="next-step-facts">
                          <div>
                            <dt>{feedback.adaptation.direction === "hold" ? "Difficulty held" : "Difficulty adjusted"}</dt>
                            <dd>
                              {feedback.adaptation.direction === "hold" ? (
                                feedback.adaptation.to_label
                              ) : (
                                <>
                                  {feedback.adaptation.from_label}
                                  <Icon name={feedback.adaptation.direction === "up" ? "arrowUp" : "arrowDown"} size={13} />
                                  {feedback.adaptation.to_label}
                                </>
                              )}
                            </dd>
                          </div>
                          {feedback.next_concept_name && (
                            <div>
                              <dt>Next concept</dt>
                              <dd>{feedback.next_concept_name}</dd>
                            </div>
                          )}
                        </dl>
                      </section>
                    )}

                    <div className="feedback-foot">
                      {feedback.is_last ? (
                        <span className="adapt-text">{feedback.transition}</span>
                      ) : (
                        <span className="muted small kbd-hint">Press Enter to continue</span>
                      )}
                      <button className="btn btn-primary" onClick={next}>
                        {feedback.is_last ? "View Learning Report" : "Next Question"}
                        <Icon name="arrowRight" size={16} />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}
        </div>

        <aside className="session-side">
          <section className="card side-card status-card">
            <div className="side-block">
              <div className="side-label">Teacher status</div>
              <div className="status-line" key={status}>
                <span className={`status-dot ${busy ? "busy" : ""}`} />
                <span className="status-text">{status}</span>
              </div>
              <div className="status-detail muted small">{session.teacher_status}</div>
            </div>
            <div className="side-block side-split">
              <div>
                <div className="side-label">Difficulty</div>
                <LevelMeter level={session.level} />
              </div>
            </div>
            <div className="side-block">
              <div className="side-label">Mastery</div>
              <div className="mastery-line">
                <span className="mastery-big num">{Math.round(mastery * 100)}%</span>
                {phase === "feedback" && delta !== 0 && (
                  <span className={`delta-float ${delta > 0 ? "up" : "down"}`} key={session.answered}>
                    {delta > 0 ? "+" : "−"}
                    {Math.abs(delta)}
                  </span>
                )}
              </div>
              <div className="bar bar-md">
                <div className="bar-fill tone-accent live" style={{ width: `${Math.round(session.mastery * 100)}%` }} />
              </div>
            </div>
          </section>

          <section className="card side-card">
            <div className="side-block">
              <div className="side-label">Concepts</div>
              <ul className="concept-list">
                {session.concepts.map((c) => (
                  <li key={c.id} className={`cl-${c.status}`}>
                    <span className="concept-mark" role="img" aria-label={STATUS_LABELS[c.status]} title={STATUS_LABELS[c.status]}>
                      {CONCEPT_MARK[c.status]}
                    </span>
                    <span className="concept-body">
                      <span className="concept-name">{c.name}</span>
                      {c.estimate != null && (
                        <span className="concept-est">
                          <span className="concept-est-bar">
                            <span style={{ width: `${Math.round(c.estimate * 100)}%` }} />
                          </span>
                          <span className="num">{Math.round(c.estimate * 100)}%</span>
                        </span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
              {lm && <div className="concept-foot muted small">Bars show the learner model's estimate that each concept is known.</div>}
            </div>
          </section>

          {lm && (
            <section className="card side-card">
              <div className="side-block">
                <div className="side-label">Learner model</div>
                <div className="lm-head">
                  <span className="lm-active">
                    <span className="status-dot" /> Active
                  </span>
                  <span className="muted small">{lm.label}</span>
                </div>
                <div className="lm-sub muted small">Runs offline with configured parameters; not a trained model.</div>
                {phase === "feedback" && feedback?.learner_model ? (
                  <p className="lm-text">
                    {feedback.learner_model.concept_name}:{" "}
                    <span className="num">{pct(feedback.learner_model.known_before)}</span> →{" "}
                    <span className="num strong">{pct(feedback.learner_model.known_after)}</span> estimated known
                  </p>
                ) : (
                  lm.predicted_correct != null && (
                    <p className="lm-text">
                      Expected chance of answering this question correctly:{" "}
                      <span className="num strong">{pct(lm.predicted_correct)}</span>
                    </p>
                  )
                )}
              </div>
            </section>
          )}
        </aside>
      </div>
    </>
  );
}
