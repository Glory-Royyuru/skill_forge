import { api } from "../api.js";
import KnowledgeMap from "../components/KnowledgeMap.jsx";
import { Bar, Card, ErrorState, Icon, Loading, MasteryRing, StatusPill } from "../components/ui.jsx";
import { startTopic } from "../lib/actions.js";
import { formatDate, navigate, pct } from "../lib/router.js";
import { useLoad } from "../lib/useLoad.js";

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

export default function Dashboard() {
  const { data: p, error, loading, reload } = useLoad(() => api.teacherProgress());
  const today = new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });

  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const active = p.active_session;
  const rec = p.recommended;

  return (
    <>
      <section className="hero rise">
        <div className="hero-copy">
          <div className="eyebrow">{today}</div>
          <h1 className="display hero-heading">
            {greeting()}.
            <br />
            <span className="hero-sub">Let's pick up where you left off.</span>
          </h1>
          <p className="hero-lede">
            {p.sessions_completed
              ? `You've completed ${p.sessions_completed} session${p.sessions_completed > 1 ? "s" : ""} and answered ${p.questions_answered} questions. Your teacher has reviewed them and prepared a next step.`
              : "Choose a topic and your teacher will diagnose where you are, teach, and adapt every question to you."}
          </p>

          {active ? (
            <div className="next-step">
              <div className="next-step-label">
                <span className="live-dot" /> Session in progress
              </div>
              <div className="next-step-title">{active.topic_title}</div>
              <div className="next-step-meta">
                {active.subject_name} · Question {active.question_number} of {active.max_questions}
              </div>
              <div className="next-step-actions">
                <button className="btn btn-primary btn-lg" onClick={() => navigate("session", active.id)}>
                  Continue Session <Icon name="arrowRight" size={16} />
                </button>
                <button className="btn btn-ghost" onClick={() => startTopic(rec.topic_id)}>
                  Start {rec.topic_title} instead
                </button>
              </div>
            </div>
          ) : (
            <div className="next-step">
              <div className="next-step-label">Recommended next · {rec.subject_name}</div>
              <div className="next-step-title">{rec.topic_title}</div>
              <div className="next-step-meta">{rec.reason}</div>
              <div className="next-step-actions">
                <button className="btn btn-primary btn-lg" onClick={() => startTopic(rec.topic_id)}>
                  Start Learning <Icon name="arrowRight" size={16} />
                </button>
                <button className="btn btn-ghost" onClick={() => navigate("topics")}>
                  Explore the curriculum
                </button>
              </div>
            </div>
          )}
        </div>
        <div className="hero-visual">
          <KnowledgeMap subjects={p.subjects} onSelect={startTopic} />
        </div>
      </section>

      <div className="grid grid-3 dash-row">
        <Card title="Mastery overview" className="rise" style={{ animationDelay: "80ms" }}>
          <div className="mastery-summary">
            <MasteryRing value={p.overall_mastery} size={118} />
            <dl className="facts">
              <div>
                <dt>Topics started</dt>
                <dd className="num">
                  {p.topics_started}
                  <span className="muted"> / {p.topics_total}</span>
                </dd>
              </div>
              <div>
                <dt>Mastered</dt>
                <dd className="num">{p.topics_mastered}</dd>
              </div>
              <div>
                <dt>Accuracy</dt>
                <dd className="num">{pct(p.accuracy)}</dd>
              </div>
            </dl>
          </div>
        </Card>

        <Card
          title="Recent activity"
          className="rise"
          style={{ animationDelay: "140ms" }}
          action={
            <button className="link-btn" onClick={() => navigate("progress")}>
              All sessions
            </button>
          }
        >
          {p.recent_sessions.length ? (
            <ul className="activity">
              {p.recent_sessions.slice(0, 3).map((s) => (
                <li key={s.id}>
                  <button className="activity-row" onClick={() => navigate("report", s.id)}>
                    <span className={`activity-mark band-${s.band.toLowerCase()}`}>{Math.round(s.mastery * 100)}</span>
                    <span className="activity-body">
                      <span className="activity-title">{s.topic_title}</span>
                      <span className="muted small">
                        {s.correct}/{s.attempted} correct · {formatDate(s.created_at)}
                      </span>
                    </span>
                    <Icon name="arrowRight" size={14} className="row-arrow" />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No sessions yet. Your reports will appear here.</p>
          )}
        </Card>

        <Card title="Teacher's focus" className="rise" style={{ animationDelay: "200ms" }}>
          {p.areas_to_improve.length || p.strengths.length ? (
            <ul className="focus-list">
              {p.areas_to_improve.slice(0, 2).map((a) => (
                <li key={`${a.topic_id}-${a.concept}`}>
                  <div>
                    <div className="focus-name">{a.concept}</div>
                    <div className="muted small">{a.topic_title}</div>
                  </div>
                  <StatusPill status={a.status} />
                </li>
              ))}
              {p.strengths.slice(0, 2).map((a) => (
                <li key={`${a.topic_id}-${a.concept}`}>
                  <div>
                    <div className="focus-name">{a.concept}</div>
                    <div className="muted small">{a.topic_title}</div>
                  </div>
                  <StatusPill status="strong" />
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">Complete a session to see your strengths and gaps.</p>
          )}
        </Card>
      </div>

      <div className="section-head">
        <h2 className="display section-title">Explore subjects</h2>
        <button className="link-btn" onClick={() => navigate("topics")}>
          Full curriculum <Icon name="arrowRight" size={13} />
        </button>
      </div>
      <div className="grid grid-3">
        {p.subjects.map((s, si) => (
          <section key={s.id} className={`card subject-card subj-${s.id} rise`} style={{ animationDelay: `${si * 70}ms` }}>
            <div className="card-body">
              <div className="subject-top">
                <h3 className="display">{s.name}</h3>
                <span className="num subject-pct">{pct(s.mastery)}</span>
              </div>
              <Bar value={s.mastery} delay={200 + si * 80} />
              <ul className="subject-topics">
                {s.topics.map((t) => (
                  <li key={t.id}>
                    <button className="topic-row" onClick={() => startTopic(t.id)} title={`Start ${t.title}`}>
                      <span className={`dot dot-${t.status}`} />
                      <span className="topic-row-name">{t.title}</span>
                      <span className="num muted small">{t.mastery == null ? "New" : pct(t.mastery)}</span>
                      <Icon name="arrowRight" size={14} className="row-arrow" />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        ))}
      </div>
    </>
  );
}
