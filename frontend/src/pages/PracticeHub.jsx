import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { ConceptRow, RecList } from "../components/learning.jsx";
import { prefersReducedMotion } from "../components/motion.jsx";
import { ErrorState, Icon, Loading, PageHeader } from "../components/ui.jsx";
import { actOn, startTopic } from "../lib/actions.js";
import { navigate, pct } from "../lib/router.js";
import { useLoad } from "../lib/useLoad.js";

const TABS = [
  { id: "recommended", label: "Overview" },
  { id: "flashcards", label: "Flashcards" },
  { id: "rapid", label: "Rapid Round" },
  { id: "review", label: "Needs Review" },
];
const LETTERS = ["A", "B", "C", "D"];
const RATING_LABELS = { known: "I knew this", review: "Needs review", skipped: "Skipped" };

// The three activities, described by what they actually do. The Teacher
// Agent's action follows the first recommendation that opens a session.
function Activities({ recs }) {
  const lead = (recs || []).find((r) => ["session", "resume", "diagnostic"].includes(r.cta?.kind));
  return (
    <section className="activities" aria-label="Ways to practise">
      <article className="activity activity-teacher">
        <div className="activity-k"><Icon name="teacher" size={16} /> Teacher Agent</div>
        <h2 className="activity-title display">A guided lesson on one topic</h2>
        <p className="activity-what">
          A short lesson, then one question at a time. After every answer you see whether it was right and why, and the
          next question adapts to it. The session ends with a learning report.
        </p>
        <dl className="activity-facts">
          <div><dt>Use it when</dt><dd>You are learning a topic, or a concept keeps going wrong.</dd></div>
          <div><dt>Counts as</dt><dd>Full graded evidence for your concept estimates.</dd></div>
        </dl>
        <div className="activity-actions">
          {lead ? (
            <button className="btn btn-accent" onClick={() => actOn(lead)}>
              {lead.cta.kind === "diagnostic"
                ? "Start the diagnostic"
                : `${lead.cta.kind === "resume" ? "Continue" : "Start"}: ${lead.topic_title || lead.title}`}
              <Icon name="arrowRight" size={15} />
            </button>
          ) : null}
          <button className={`btn ${lead ? "btn-ghost" : "btn-accent"}`} onClick={() => navigate("learn")}>
            Choose a topic in Learn
          </button>
        </div>
      </article>
      <div className="activity-side">
        <article className="activity activity-cards">
          <div className="activity-k"><Icon name="layers" size={16} /> Flashcards</div>
          <h2 className="activity-title display">Review from your own answers</h2>
          <p className="activity-what">Read the prompt, reveal the answer, then rate how well you knew it.</p>
          <dl className="activity-facts">
            <div><dt>Use it when</dt><dd>You have a few minutes between sessions.</dd></div>
            <div><dt>Counts as</dt><dd>A self-check. Ratings order your reviews and never change mastery.</dd></div>
          </dl>
          <button className="btn btn-secondary" onClick={() => navigate("practice", null, { tab: "flashcards" })}>
            Open flashcards <Icon name="arrowRight" size={15} />
          </button>
        </article>
        <article className="activity activity-rapid">
          <div className="activity-k"><Icon name="clock" size={16} /> Rapid Round</div>
          <h2 className="activity-title display">60 seconds of quick recall</h2>
          <p className="activity-what">Up to 10 short questions, mostly on concepts you have practised. Answer as many as you can.</p>
          <dl className="activity-facts">
            <div><dt>Use it when</dt><dd>You want to check what you can recall quickly.</dd></div>
            <div><dt>Counts as</dt><dd>Lighter evidence than a Teacher session.</dd></div>
          </dl>
          <button className="btn btn-secondary" onClick={() => navigate("practice", null, { tab: "rapid" })}>
            Go to Rapid Round <Icon name="arrowRight" size={15} />
          </button>
        </article>
      </div>
    </section>
  );
}

function Recommended() {
  const { data, error, loading, reload } = useLoad(() => api.recommendations());
  if (loading) return <Loading label="Loading your practice options…" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  return (
    <>
      <Activities recs={data.recommendations} />
      <h2 className="section-h display">Chosen from your evidence</h2>
      <RecList recs={data.recommendations} empty="Complete the diagnostic or a session to get recommendations." />
    </>
  );
}

const LEAVE = { known: "right", review: "left", skipped: "down" };

function Flashcards() {
  const { data, error, loading, reload } = useLoad(() => api.flashcards());
  const [i, setI] = useState(0);
  const [back, setBack] = useState(null);
  const [flipped, setFlipped] = useState(false);
  const [flipping, setFlipping] = useState(false);
  const [leaving, setLeaving] = useState(null);
  const [saving, setSaving] = useState(false);
  const [tally, setTally] = useState({ known: 0, review: 0, skipped: 0 });
  const [status, setStatus] = useState("");
  const [cardError, setCardError] = useState(null);
  const keys = useRef({});
  const ratingLock = useRef(false); // one rating per card, even on a fast double-click
  const backRef = useRef(null);
  const revealRef = useRef(null);

  useEffect(() => {
    const onKey = (e) => {
      if (e.metaKey || e.ctrlKey || e.altKey || e.target.closest?.("input, textarea, select")) return;
      const k = keys.current;
      if ((e.key === " " || e.key === "Enter") && k.flip && !k.flipped && !e.target.closest?.("a, button:not(.fc-flip)")) {
        e.preventDefault();
        k.flip();
      } else if (k.flipped && k.rate && ["1", "2", "3"].includes(e.key)) {
        k.rate({ 1: "review", 2: "skipped", 3: "known" }[e.key]);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (loading) return <Loading label="Building your deck…" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const cards = data.cards;
  if (!cards.length) {
    return (
      <div className="empty-panel">
        <h2 className="display">No flashcards yet</h2>
        <p>Cards are built from your own graded answers, so there is nothing to review until you have answered some questions.</p>
        <button className="btn btn-primary btn-sm" onClick={() => navigate("diagnostic")}>Take the diagnostic</button>
      </div>
    );
  }
  const done = i >= cards.length;
  const card = cards[i];

  // The back is only fetched from the server when the student asks to see it.
  const flip = async () => {
    if (flipping || flipped) return;
    setFlipping(true);
    setCardError(null);
    try {
      setBack((await api.revealCard(card.id)).back);
      requestAnimationFrame(() => {
        setFlipped(true);
        setStatus("Answer shown. Rate how well you knew it: 1 needs review, 2 skip, 3 I knew this.");
        setTimeout(() => backRef.current?.focus({ preventScroll: true }), 60);
      });
    } catch (e) {
      setCardError(`The answer could not be loaded. ${e.message}`);
    } finally {
      setFlipping(false);
    }
  };
  const rate = async (rating) => {
    if (leaving || ratingLock.current) return;
    ratingLock.current = true;
    setSaving(true);
    setCardError(null);
    try {
      await api.reviewCard(card.id, rating);
    } catch (e) {
      setCardError(`Your rating was not saved. ${e.message}`);
      setSaving(false);
      ratingLock.current = false;
      return;
    }
    setSaving(false);
    setTally((t) => ({ ...t, [rating]: t[rating] + 1 }));
    setStatus(`Saved: ${RATING_LABELS[rating]}.${i + 1 < cards.length ? ` Card ${i + 2} of ${cards.length}.` : ""}`);
    setLeaving(LEAVE[rating]);
    setTimeout(() => {
      ratingLock.current = false;
      setLeaving(null);
      setFlipped(false);
      setBack(null);
      setI((n) => n + 1);
      setTimeout(() => revealRef.current?.focus({ preventScroll: true }), 30);
    }, prefersReducedMotion() ? 0 : 300);
  };
  keys.current = done ? {} : { flip, rate, flipped };

  if (done) {
    return (
      <div className="fc-done">
        <div className="kicker">Deck complete</div>
        <h2 className="display">{cards.length} cards reviewed</h2>
        <dl className="fc-tally">
          <div><dt>I knew this</dt><dd className="num">{tally.known}</dd></div>
          <div><dt>Needs review</dt><dd className="num">{tally.review}</dd></div>
          <div><dt>Skipped</dt><dd className="num">{tally.skipped}</dd></div>
        </dl>
        <p className="muted">
          Your ratings help order future reviews. They do not change your mastery estimates, which come only from graded
          answers.
        </p>
        <div className="hero-actions">
          <button className="btn btn-primary" onClick={() => (setI(0), setTally({ known: 0, review: 0, skipped: 0 }), setStatus(""), reload())}>New deck</button>
          <button className="btn btn-ghost" onClick={() => navigate("practice", null, { tab: "rapid" })}>Try a Rapid Round</button>
        </div>
      </div>
    );
  }

  return (
    <div className="fc-wrap">
      <div className="fc-progress">
        <span>Card <strong className="num">{i + 1}</strong> of {cards.length}</span>
        <div className="segments" aria-hidden="true">
          {cards.map((c, n) => <div key={c.id} className={`segment ${n < i ? "seg-done" : ""} ${n === i ? "seg-current" : ""}`} />)}
        </div>
      </div>
      <div className="deck">
        {cards.length - i > 1 && <div className="deck-under u1" aria-hidden="true" />}
        <div className={`fcard ${flipped ? "flipped" : ""} ${leaving ? `leave-${leaving}` : ""}`} key={card.id}>
          <div className="fcard-inner">
            <section className="fcard-face fcard-front" aria-hidden={flipped} aria-label="Card front">
              <div className="fc-meta">
                <span className="chip">{card.subject_name}</span>
                <span className="muted small">{card.topic_title}</span>
              </div>
              <div className="fc-kind">{card.kind === "question" ? "From your answers" : card.concept_name}</div>
              <p className="fc-text display">{card.front.split("\n\n").pop()}</p>
              {card.reasons.length > 0 && (
                <div className="fc-reasons" aria-label="Why this card">
                  {card.reasons.map((r) => (
                    <span key={r} className="fc-reason">{r}</span>
                  ))}
                </div>
              )}
              <button ref={revealRef} className="btn btn-primary fc-flip" onClick={flip} disabled={flipping} tabIndex={flipped ? -1 : 0}>
                {flipping ? "Revealing…" : "Reveal answer"}
              </button>
            </section>
            <section className="fcard-face fcard-back" aria-hidden={!flipped} aria-label="Card back" ref={backRef} tabIndex={flipped ? -1 : undefined}>
              {back && (
                <>
                  <div className="fc-kind">{card.kind === "question" ? "Answer" : "Key idea"}</div>
                  <p className="fc-answer display">{back.title}</p>
                  <p className="fc-expl">{back.text}</p>
                </>
              )}
            </section>
          </div>
        </div>
      </div>
      {cardError && <p className="fc-error" role="alert">{cardError}</p>}
      <div className={`fc-rate ${flipped ? "show" : ""}`}>
        <span className="fc-rate-q">{flipped ? "How well did you know it?" : "Reveal the answer first (Space or Enter)."}</span>
        <div className="fc-rate-btns" role="group" aria-label="Rate this card">
          <button className="btn btn-secondary btn-sm" disabled={!flipped || saving} onClick={() => rate("review")}>
            <span className="kbd" aria-hidden="true">1</span> Needs review
          </button>
          <button className="btn btn-ghost btn-sm" disabled={!flipped || saving} onClick={() => rate("skipped")}>
            <span className="kbd" aria-hidden="true">2</span> Skip
          </button>
          <button className="btn btn-primary btn-sm" disabled={!flipped || saving} onClick={() => rate("known")}>
            <span className="kbd" aria-hidden="true">3</span> I knew this
          </button>
        </div>
      </div>
      <p className="sr-only" role="status" aria-live="polite">{status}</p>
      <p className="muted small fc-note">{data.note}</p>
    </div>
  );
}

// Spoken countdown: a few announcements instead of a label that changes five times a second.
const ANNOUNCE_AT = [30, 10];

function RapidRound() {
  const [round, setRound] = useState(null);
  const [idx, setIdx] = useState(0);
  const [left, setLeft] = useState(60);
  const [last, setLast] = useState(null);
  const [pending, setPending] = useState(false);
  const [results, setResults] = useState(null);
  const [expired, setExpired] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [announce, setAnnounce] = useState("");
  const [error, setError] = useState(null);
  const shownAt = useRef(Date.now());
  const deadline = useRef(0);
  const finished = useRef(false);
  const announced = useRef(new Set());
  const qRef = useRef(null);
  const inFlight = useRef(false); // synchronous guard: state updates arrive too late for fast double-clicks

  // The server owns the deadline; finishing twice (timer, last answer and
  // "End round" can race) must only send one request.
  const finish = useCallback(async (id) => {
    if (finished.current) return;
    finished.current = true;
    setFinishing(true);
    try {
      setResults(await api.finishRapid(id));
    } catch (e) {
      setError(e);
    } finally {
      setFinishing(false);
    }
  }, []);

  useEffect(() => {
    if (!round || results) return undefined;
    const t = setInterval(() => {
      const s = Math.max(0, (deadline.current - Date.now()) / 1000);
      setLeft(s);
      for (const at of ANNOUNCE_AT) {
        if (s <= at && !announced.current.has(at)) {
          announced.current.add(at);
          setAnnounce(`${at} seconds left`);
        }
      }
      if (s <= 0) {
        clearInterval(t);
        setExpired(true);
        setAnnounce("Time is up. Saving your round.");
        finish(round.id);
      }
    }, 200);
    return () => clearInterval(t);
  }, [round, results, finish]);

  useEffect(() => {
    if (round && !results) qRef.current?.focus({ preventScroll: true });
  }, [round, idx, results]);

  const start = async () => {
    setError(null);
    setResults(null);
    setExpired(false);
    setIdx(0);
    setLast(null);
    setAnnounce("");
    finished.current = false;
    inFlight.current = false;
    announced.current = new Set();
    try {
      const r = await api.startRapid();
      deadline.current = Date.now() + r.remaining_seconds * 1000;
      setLeft(r.remaining_seconds);
      shownAt.current = Date.now();
      setRound(r);
    } catch (e) {
      setError(e);
    }
  };

  const choose = useCallback(async (choice) => {
    if (!round || last || inFlight.current || finished.current) return;
    const q = round.questions[idx];
    inFlight.current = true;
    setPending(true);
    try {
      const res = await api.answerRapid(round.id, q.id, choice, Date.now() - shownAt.current);
      setLast({ ok: res.correct, choice, correct: res.correct_choice });
      setAnnounce(res.correct ? "Correct." : `Not quite. The answer was ${LETTERS[res.correct_choice]}.`);
      setTimeout(() => {
        inFlight.current = false;
        setLast(null);
        shownAt.current = Date.now();
        if (idx + 1 >= round.questions.length) finish(round.id);
        else setIdx(idx + 1);
      }, prefersReducedMotion() ? 700 : 550);
    } catch (e) {
      inFlight.current = false;
      if (e.status === 409) {
        setExpired(true);
        finish(round.id);
      } else setError(e);
    } finally {
      setPending(false);
    }
  }, [round, idx, last, finish]);

  // A–D or 1–4 answer the current question.
  useEffect(() => {
    if (!round || results) return undefined;
    const onKey = (e) => {
      if (e.metaKey || e.ctrlKey || e.altKey || e.target.closest?.("input, textarea, select")) return;
      const k = e.key.toUpperCase();
      const n = LETTERS.indexOf(k) >= 0 ? LETTERS.indexOf(k) : Number(k) - 1;
      const q = round.questions[idx];
      if (q && n >= 0 && n < q.options.length) {
        e.preventDefault();
        choose(n);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [round, idx, results, choose]);

  if (error) return <ErrorState error={error} onRetry={start} />;

  if (results) {
    return (
      <div className="rapid-results">
        <div className="kicker">{expired ? "Time is up · Rapid Round result" : "Rapid Round result"}</div>
        <h2 className="display">{results.headline}</h2>
        <p className="rapid-detail">{results.detail}</p>
        <dl className="rapid-stats">
          <div><dt>Answered</dt><dd className="num">{results.attempted}</dd></div>
          <div><dt>Correct</dt><dd className="num">{results.correct}</dd></div>
          <div><dt>Accuracy</dt><dd className="num">{pct(results.accuracy)}</dd></div>
          <div><dt>Typical answer time</dt><dd className="num">{results.median_response_ms ? `${(results.median_response_ms / 1000).toFixed(1)} s` : "—"}</dd></div>
        </dl>
        {results.concepts.length > 0 && (
          <>
            <h3 className="rapid-sub">By concept</h3>
            <ul className="rapid-concepts">
              {results.concepts.map((c) => (
                <li key={c.concept}><span>{c.concept} <span className="muted small">· {c.topic_title}</span></span><span className="num">{c.correct}/{c.attempted}</span></li>
              ))}
            </ul>
          </>
        )}
        <p className="muted small">{results.note}</p>
        <div className="hero-actions">
          <button className="btn btn-primary" onClick={start}>Another round</button>
          <button className="btn btn-ghost" onClick={() => navigate("practice", null, { tab: "flashcards" })}>Review with flashcards</button>
        </div>
      </div>
    );
  }

  if (!round) {
    return (
      <div className="rapid-intro">
        <div className="kicker">Rapid Round</div>
        <h2 className="display">60 seconds of quick recall</h2>
        <ol className="rapid-how">
          <li>Up to 10 short questions, mostly on concepts you have already practised.</li>
          <li>Answer as many as you can. There is no penalty for leaving any unanswered.</li>
          <li>The clock is kept by the server, so the round ends at 60 seconds even if this page is slow.</li>
        </ol>
        <p className="muted small">Rapid Round measures recall speed, so it counts as lighter evidence than a Teacher session.</p>
        <button className="btn btn-accent btn-lg" onClick={start}>Start the clock <Icon name="arrowRight" size={16} /></button>
      </div>
    );
  }

  const q = round.questions[idx];
  const frac = left / round.duration_seconds;
  const secs = Math.ceil(left);
  return (
    <div className="rapid">
      <div className={`rapid-clock ${left < 10 ? "low" : ""}`}>
        <div className="rapid-time" aria-hidden="true">
          <span className="num">{secs}</span>
          <span className="small">s left</span>
        </div>
        <div className="rapid-track" aria-hidden="true">
          <div className="rapid-fill" style={{ transform: `scaleX(${frac})` }} />
        </div>
        <button className="btn btn-ghost btn-sm" onClick={() => finish(round.id)} disabled={finishing}>
          {finishing ? "Saving…" : "End round"}
        </button>
      </div>
      <p className="sr-only" role="status" aria-live="polite">{announce}</p>
      <div className="rapid-count">
        <span className="rapid-count-t">Question <strong className="num">{idx + 1}</strong> of {round.questions.length}</span>
        <ol className="rapid-dots" aria-hidden="true">
          {round.questions.map((qq, n) => (
            <li key={qq.id} className={n < idx ? "done" : n === idx ? "now" : ""} />
          ))}
        </ol>
      </div>
      {expired || finishing ? (
        <div className="rapid-q rapid-saving" role="status">
          <p className="display">{expired ? "Time is up." : "Ending the round."}</p>
          <p className="muted">Saving your answers…</p>
        </div>
      ) : (
        <div className="rapid-q" key={q.id} ref={qRef} tabIndex={-1} aria-label={`Question ${idx + 1}`}>
          <div className="q-meta"><span className="chip">{q.subject_name}</span><span className="chip">{q.concept_name}</span></div>
          {q.prompt.includes("\n\n") && <pre className="code">{q.prompt.split("\n\n").slice(0, -1).join("\n\n")}</pre>}
          <p className="q-prompt">{q.prompt.split("\n\n").pop()}</p>
          <div className="options" role="group" aria-label="Answer options. Keys A to D also answer.">
            {q.options.map((opt, i) => {
              let cls = "option";
              if (last) cls += i === last.correct ? " is-correct" : i === last.choice ? " is-wrong" : " is-dim";
              return (
                <button key={i} className={cls} disabled={!!last || pending} onClick={() => choose(i)}>
                  <span className="option-letter">{LETTERS[i]}</span><span className="option-text">{opt}</span>
                  {last && i === last.correct && <span className="option-mark">Correct answer</span>}
                  {last && i === last.choice && i !== last.correct && <span className="option-mark">Your answer</span>}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// Only concepts the learner model has flagged, or with a low estimate backed
// by several answers. One wrong answer alone does not put a concept here.
const MIN_REVIEW_ANSWERS = 3;

function NeedsReview() {
  const { data, error, loading, reload } = useLoad(() => api.learnerState());
  if (loading) return <Loading label="Checking your concepts…" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const concepts = data.subjects.flatMap((s) => s.topics.flatMap((t) => t.concepts));
  const review = concepts
    .filter((c) => c.status === "needs_review" || (c.status === "learning" && (c.attempts ?? 0) >= MIN_REVIEW_ANSWERS && (c.p_known ?? 1) < 0.5))
    .sort((a, b) => (a.status === "needs_review" ? 0 : 1) - (b.status === "needs_review" ? 0 : 1) || a.p_known - b.p_known);
  if (!review.length) {
    return (
      <div className="empty-panel">
        <h2 className="display">Nothing needs review right now</h2>
        <p>Concepts appear here after repeated mistakes, or when a low estimate is backed by at least {MIN_REVIEW_ANSWERS} answers. A single wrong answer is not enough.</p>
      </div>
    );
  }
  return (
    <>
      <p className="tab-lede">Flagged from repeated mistakes or a low estimate backed by several answers. Review starts a short Teacher session at Foundational level on that concept.</p>
      <ul className="review-list">
        {review.map((c) => (
          <li key={c.id} className="concept-review">
            <ConceptRow c={c} as="div" />
            <button className="btn btn-primary btn-sm" onClick={() => startTopic(c.topic_id, { focus_concept: c.key, target_difficulty: 1 })}>
              Review <span className="sr-only">{c.name}</span> <Icon name="arrowRight" size={14} />
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}

export default function PracticeHub({ query }) {
  const tab = TABS.some((t) => t.id === query?.tab) ? query.tab : "recommended";
  return (
    <>
      <PageHeader eyebrow="Practice" title="Practice that follows your evidence" subtitle="Three ways to practise, each chosen from your own answers: what you missed, what is getting stale, and what is coming up in class." />
      <div className="tabs" role="tablist" aria-label="Practice">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} className={`tab ${tab === t.id ? "on" : ""}`} onClick={() => navigate("practice", null, { tab: t.id })}>
            {t.label}
          </button>
        ))}
      </div>
      <div key={tab} className="tab-panel" role="tabpanel" aria-label={TABS.find((t) => t.id === tab).label}>
        {tab === "recommended" && <Recommended />}
        {tab === "flashcards" && <Flashcards />}
        {tab === "rapid" && <RapidRound />}
        {tab === "review" && <NeedsReview />}
      </div>
    </>
  );
}
