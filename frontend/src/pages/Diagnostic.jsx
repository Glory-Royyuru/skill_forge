import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { ErrorState, Icon, Loading, PageHeader } from "../components/ui.jsx";
import { navigate } from "../lib/router.js";

const LETTERS = ["A", "B", "C", "D"];

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

function Intro({ count, onStart, onSkip, busy }) {
  return (
    <section className="card diag-intro rise">
      <div className="card-body">
        <div className="eyebrow">Starting point</div>
        <h2 className="display">{count} questions, one from each subject</h2>
        <p>
          This short diagnostic gives SkillForge first evidence about where you are, so its recommendations are
          based on your answers instead of assumptions. It takes about 6 minutes.
        </p>
        <ul className="diag-points">
          <li><Icon name="check" size={15} /> It establishes a starting point. It cannot mark anything as mastered.</li>
          <li><Icon name="check" size={15} /> Not sure? Skip a question; skipped questions are not counted.</li>
          <li><Icon name="check" size={15} /> You will see every answer with an explanation at the end.</li>
        </ul>
        <div className="hero-actions">
          <button className="btn btn-primary btn-lg" onClick={onStart} disabled={busy}>
            Begin diagnostic <Icon name="arrowRight" size={16} />
          </button>
          <button className="btn btn-ghost" onClick={onSkip} disabled={busy}>
            Skip for now
          </button>
        </div>
      </div>
    </section>
  );
}

function Summary({ summary }) {
  return (
    <>
      <section className="card diag-summary rise">
        <div className="card-body">
          <div className="eyebrow">Diagnostic complete</div>
          <h2 className="display">
            {summary.correct} of {summary.answered} answered correctly
            {summary.skipped ? ` · ${summary.skipped} skipped` : ""}
          </h2>
          <p className="muted">{summary.note}</p>
          <div className="hero-actions">
            <button className="btn btn-primary" onClick={() => navigate("dashboard")}>
              See your recommendations <Icon name="arrowRight" size={16} />
            </button>
          </div>
        </div>
      </section>
      <section className="card rise" style={{ animationDelay: "80ms" }}>
        <div className="card-head">
          <h2 className="card-title">Your answers</h2>
        </div>
        <ol className="review">
          {summary.items.map((i, n) => (
            <li key={n} className="review-item">
              <span className={`review-mark mark-${i.skipped ? "skipped" : i.correct ? "correct" : "incorrect"}`}>
                <Icon name={i.skipped ? "arrowRight" : i.correct ? "check" : "x"} size={14} />
              </span>
              <div className="review-body">
                <div className="review-meta">
                  {i.subject_name} · {i.concept_name} · {i.difficulty_label}
                  <span className="verdict-text">{i.starting_point}</span>
                </div>
                <div className="review-prompt">{i.prompt.split("\n\n").pop()}</div>
                <div className="review-answers">
                  {i.skipped ? <span>Skipped</span> : <span>Your answer: <strong>{i.your_answer}</strong></span>}
                  {!i.correct && (
                    <span>
                      Correct answer: <strong>{i.correct_answer}</strong>
                    </span>
                  )}
                </div>
                <p className="review-expl muted">{i.explanation}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </>
  );
}

export default function Diagnostic() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);
  const shownAt = useRef(Date.now());
  const inFlight = useRef(false);

  const load = useCallback(() => {
    setError(null);
    api.diagnostic().then(setData).catch(setError);
  }, []);
  useEffect(load, [load]);

  const current = data?.diagnostic?.status === "active" ? data.diagnostic : null;
  const qid = current?.current_question?.id;
  useEffect(() => {
    shownAt.current = Date.now();
    setSelected(null);
  }, [qid]);

  // One request at a time; the ref blocks a second click in the same tick.
  const act = async (fn) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      setError(e);
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };

  if (error) return <ErrorState error={error} onRetry={load} />;
  if (!data) return <Loading />;

  const d = data.diagnostic;
  const answer = (choice) =>
    act(async () => {
      const next = await api.answerDiagnostic(qid, choice, Date.now() - shownAt.current);
      setData((x) => ({ ...x, status: next.status, diagnostic: next }));
    });

  return (
    <>
      <PageHeader eyebrow="Diagnostic" title="Find your starting point" />
      {data.status === "completed" && d?.summary && <Summary summary={d.summary} />}
      {(data.status === "none" || data.status === "skipped") && (
        <Intro
          count={data.question_count}
          busy={busy}
          onStart={() =>
            act(async () => {
              const dg = await api.startDiagnostic();
              setData((x) => ({ ...x, status: "active", diagnostic: dg }));
            })
          }
          onSkip={() =>
            act(async () => {
              await api.skipDiagnostic();
              navigate("dashboard");
            })
          }
        />
      )}
      {current && current.current_question && (
        <section className="card question-card rise" key={qid}>
          <div className="q-enter card-body">
            <div className="diag-progress">
              <span className="q-number">
                Question {current.answered + 1} <span className="muted">of {current.total}</span>
              </span>
              <div className="segments">
                {Array.from({ length: current.total }, (_, i) => (
                  <div key={i} className={`segment ${i < current.answered ? "seg-done" : ""} ${i === current.answered ? "seg-current" : ""}`} />
                ))}
              </div>
            </div>
            <div className="q-meta">
              <span className="chip">{current.current_question.subject_name}</span>
              <span className="chip">{current.current_question.concept_name}</span>
            </div>
            <Prompt text={current.current_question.prompt} />
            <div className="options" role="radiogroup">
              {current.current_question.options.map((opt, i) => (
                <button
                  key={i}
                  role="radio"
                  aria-checked={selected === i}
                  className={`option ${selected === i ? "is-selected" : ""}`}
                  onClick={() => setSelected(i)}
                  disabled={busy}
                >
                  <span className="option-letter">{LETTERS[i]}</span>
                  <span className="option-text">{opt}</span>
                </button>
              ))}
            </div>
            <div className="q-actions">
              <button className="btn btn-ghost" onClick={() => answer(null)} disabled={busy}>
                Skip question
              </button>
              <button className="btn btn-primary" onClick={() => answer(selected)} disabled={busy || selected == null}>
                {current.answered + 1 === current.total ? "Finish" : "Next"} <Icon name="arrowRight" size={16} />
              </button>
            </div>
          </div>
        </section>
      )}
    </>
  );
}
