import { api } from "../api.js";
import { areaOf, placeOf } from "../lib/catalog.js";
import { RecCard } from "../components/learning.jsx";
import { Stagger } from "../components/motion.jsx";
import { ErrorState, Icon, Loading } from "../components/ui.jsx";
import { actOn, startTopic } from "../lib/actions.js";
import { formatDate, navigate, pct } from "../lib/router.js";
import { useLoad } from "../lib/useLoad.js";

// Home: a command center built only from the student's own data.

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

const START_LABEL = { take_diagnostic: "Take the diagnostic", continue_session: "Continue" };

function NextAction({ rec, fresh }) {
  if (!rec) {
    return (
      <div className="next-action-lead">
        <div className="kicker">Next best action</div>
        <h2 className="display na-title">Choose a topic to begin</h2>
        <p className="na-reason">There is nothing to recommend yet.</p>
        <button className="btn btn-accent btn-lg" onClick={() => navigate("learn")}>
          Open the curriculum <Icon name="arrowRight" size={16} />
        </button>
      </div>
    );
  }
  const area = rec.subject_id ? areaOf(placeOf({ id: rec.subject_id }).area) : null;
  const path = [area?.short, rec.subject_name, rec.topic_title].filter(Boolean);
  return (
    <div className="next-action-lead">
      <div className="kicker">Your next step</div>
      <h2 className="display na-title">{rec.title}</h2>
      {path.length > 0 && (
        <ol className="na-path" aria-label="Where this sits">
          {path.map((p) => <li key={p}>{p}</li>)}
        </ol>
      )}
      <dl className="na-facts">
        <div className="na-fact na-why">
          <dt>Why</dt>
          <dd>{rec.reason}</dd>
        </div>
        <div className="na-fact">
          <dt>Time</dt>
          <dd className="num">About {rec.estimated_minutes} min</dd>
        </div>
        <div className="na-fact">
          <dt>Target</dt>
          <dd>
            {rec.concept_name || rec.topic_title || rec.subject_name || "Your starting point"}
            {rec.target_difficulty_label ? ` · ${rec.target_difficulty_label}` : ""}
          </dd>
        </div>
      </dl>
      {rec.evidence?.length > 0 && (
        <ul className="marginalia">
          {rec.evidence.slice(0, 3).map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
      )}
      <div className="na-actions">
        <button className="btn btn-accent btn-lg" onClick={() => actOn(rec)}>
          {START_LABEL[rec.action] || "Start"} <Icon name="arrowRight" size={16} />
        </button>
        <button className="btn btn-ghost" onClick={() => navigate(fresh ? "learn" : "practice")}>
          {fresh ? "Browse subjects instead" : "Other options"}
        </button>
      </div>
    </div>
  );
}

function Ledger({ o }) {
  const ov = o.overall;
  const level = o.activity_level;
  return (
    <section className="ledger-strip" aria-label="Learning snapshot">
      <div className="lg-item">
        <span className="lg-k">Estimated knowledge</span>
        <span className="lg-v num">{ov.assessed ? pct(ov.estimate) : "—"}</span>
        <span className="lg-s">
          {ov.assessed} of {ov.total} concepts assessed
        </span>
      </div>
      <div className="lg-item">
        <span className="lg-k">Mastered</span>
        <span className="lg-v num">
          {ov.mastered}
          <small> / {ov.total}</small>
        </span>
        <span className="lg-s">from repeated correct answers</span>
      </div>
      <button className="lg-item lg-link" onClick={() => navigate("practice", null, { tab: "review" })}>
        <span className="lg-k">Needs review</span>
        <span className="lg-v num">{ov.needs_review}</span>
        <span className="lg-s">
          concept{ov.needs_review === 1 ? "" : "s"} · open list <Icon name="arrowRight" size={12} />
        </span>
      </button>
      <div className="lg-item">
        <span className="lg-k">Today</span>
        <span className="lg-v num">
          {o.today ? o.today.graded_answers : 0}
          <small> answers</small>
        </span>
        <span className="lg-s">
          {o.today ? `${o.today.concepts_practised} concepts · ~${o.today.active_minutes} min` : "Nothing yet today"}
        </span>
      </div>
      <div className="lg-item lg-activity">
        <span className="lg-k">Activity level</span>
        <span className="lg-v num">
          {level.level}
          <small> · {level.xp} XP</small>
        </span>
        <span className="lg-s">practice effort, not knowledge</span>
      </div>
    </section>
  );
}

function ComingUp({ classes }) {
  return (
    <section className="dash-col">
      <h2 className="col-title display">Coming up</h2>
      {classes.length ? (
        <ul className="col-list">
          {classes.slice(0, 3).map((c) => (
            <li key={`${c.id}-${c.starts_at}`} className="col-row">
              <div className="col-main">
                <div className="col-name">{c.subject_name}</div>
                <div className="muted small">
                  {c.when}
                  {c.room ? ` · ${c.room}` : ""}
                </div>
                <div className="col-note small">
                  {c.preparation
                    ? `Prepare: ${c.preparation.topic_title} · ${c.preparation.estimated_minutes} min`
                    : c.note}
                </div>
              </div>
              {c.preparation && (
                <button className="btn btn-secondary btn-sm" onClick={() => actOn(c.preparation)}>
                  Prepare
                </button>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <div className="col-empty">
          <p className="muted small">No classes in the next two days on your timetable.</p>
          <button className="link-btn" onClick={() => navigate("profile", null, { tab: "timetable" })}>
            Open timetable
          </button>
        </div>
      )}
    </section>
  );
}

function NeedsReview({ concepts }) {
  return (
    <section className="dash-col">
      <h2 className="col-title display">Needs review</h2>
      {concepts.length ? (
        <ul className="col-list">
          {concepts.slice(0, 3).map((c) => (
            <li key={c.id} className="col-row">
              <div className="col-main">
                <div className="col-name">{c.name}</div>
                <div className="muted small">
                  {c.topic_title} · {pct(c.p_known)} estimated
                </div>
                {c.evidence?.[0] && <div className="col-note small">{c.evidence[0]}</div>}
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => startTopic(c.topic_id, { focus_concept: c.key, target_difficulty: 1 })}
              >
                Review
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <div className="col-empty">
          <p className="muted small">
            Nothing flagged. A concept is flagged after repeated mistakes, never after a single wrong answer.
          </p>
        </div>
      )}
    </section>
  );
}

function RecentProgress({ o }) {
  const imp = o.improved_concept;
  return (
    <section className="dash-col">
      <h2 className="col-title display">Recent progress</h2>
      {imp && (
        <div className="col-highlight">
          <div className="col-name">{imp.name}</div>
          <div className="improve-line num">
            {pct(imp.from)} <Icon name="arrowRight" size={13} /> <strong>{pct(imp.p_known)}</strong>
          </div>
          <div className="muted small">across {imp.attempts} graded answers</div>
        </div>
      )}
      {o.recent_sessions.length ? (
        <ul className="col-list">
          {o.recent_sessions.slice(0, 3).map((s) => (
            <li key={s.id}>
              <button className="col-row col-row-link" onClick={() => navigate("report", s.id)}>
                <span className="score-mark num">
                  {s.correct}/{s.attempted}
                </span>
                <span className="col-main">
                  <span className="col-name">{s.topic_title}</span>
                  <span className="muted small">{formatDate(s.created_at)}</span>
                </span>
                <Icon name="arrowRight" size={14} className="row-arrow" />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        !imp && <p className="muted small">Completed Teacher sessions and improvements appear here.</p>
      )}
    </section>
  );
}

export default function Dashboard({ user }) {
  const { data, error, loading, reload } = useLoad(async () => {
    const [o, state] = await Promise.all([api.overview(), api.learnerState()]);
    return { o, state };
  });
  const today = new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });
  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const { o, state } = data;
  const firstName = user.name.split(" ")[0];
  const fresh = !o.has_evidence && !o.active_session;
  const review = state.subjects
    .flatMap((s) => s.topics.flatMap((t) => t.concepts))
    .filter((c) => c.status === "needs_review")
    .sort((a, b) => (a.p_known ?? 0) - (b.p_known ?? 0));

  return (
    <div className="dash">
      <header className="dash-head rise">
        <div className="eyebrow">{today}</div>
        <h1 className="display dash-title">
          {fresh ? `Welcome, ${firstName}.` : `${greeting()}, ${firstName}.`}
        </h1>
        <p className="dash-sub">
          {fresh
            ? "A short diagnostic, one question from each subject with a question bank, sets your starting point."
            : "Your learning snapshot, calibrated from your own answers."}
        </p>
      </header>

      <section className="dash-lead dash-lead-solo rise" aria-label="Recommended next step">
        <NextAction rec={o.next_up} fresh={fresh} />
      </section>

      {!fresh && <Ledger o={o} />}

      <div className="dash-cols stagger-in">
        <Stagger step={70}>
          <ComingUp classes={o.upcoming_classes} />
          <NeedsReview concepts={review} />
          <RecentProgress o={o} />
        </Stagger>
      </div>

      {o.recommendations.length > 1 && (
        <>
          <div className="section-head">
            <h2 className="display section-title">Also recommended</h2>
            <button className="link-btn" onClick={() => navigate("practice")}>
              All recommendations
            </button>
          </div>
          <div className="rec-grid">
            {o.recommendations.slice(1, 4).map((r) => (
              <RecCard key={r.id} rec={r} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
