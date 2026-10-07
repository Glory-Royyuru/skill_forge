import { api } from "../api.js";
import { Bar, Card, ErrorState, Icon, Loading, Metric, PageHeader, StatusPill } from "../components/ui.jsx";
import { startTopic } from "../lib/actions.js";
import { formatDate, navigate, pct } from "../lib/router.js";
import { useLoad } from "../lib/useLoad.js";

export default function LearningProgress() {
  const { data: p, error, loading, reload } = useLoad(() => api.teacherProgress());

  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  return (
    <>
      <PageHeader
        eyebrow="Progress"
        title="Your learning progress"
        subtitle="Mastery reflects your most recent session on each topic."
      />

      <div className="grid grid-4">
        <Metric label="Overall mastery" value={pct(p.overall_mastery)} sub="Across topics studied" delay={40} />
        <Metric label="Topics started" value={`${p.topics_started} / ${p.topics_total}`} sub={`${p.topics_mastered} mastered`} delay={90} />
        <Metric label="Sessions completed" value={p.sessions_completed} delay={140} />
        <Metric label="Accuracy" value={pct(p.accuracy)} sub={`${p.correct_answers} of ${p.questions_answered} correct`} delay={190} />
      </div>

      <section className="card next-action rise" style={{ animationDelay: "220ms" }}>
        <div className="card-body next-action-body">
          <div>
            <div className="eyebrow">Recommended next action</div>
            <h2 className="display next-action-title">{p.recommended.headline}</h2>
            <p className="muted">{p.recommended.reason}</p>
          </div>
          <button className="btn btn-primary" onClick={() => startTopic(p.recommended.topic_id)}>
            Start {p.recommended.topic_title} <Icon name="arrowRight" size={16} />
          </button>
        </div>
      </section>

      <div className="grid grid-2-1">
        <Card title="Topic progress" padded={false} className="rise" style={{ animationDelay: "260ms" }}>
          <table className="table table-padded">
            <thead>
              <tr>
                <th>Topic</th>
                <th className="w-bar">Mastery</th>
                <th className="right">Sessions</th>
                <th className="right">Status</th>
              </tr>
            </thead>
            <tbody>
              {p.subjects.map((s) => [
                <tr key={s.id} className="group-row">
                  <td colSpan={4}>
                    {s.name}
                    <span className="muted"> · {pct(s.mastery)} subject mastery</span>
                  </td>
                </tr>,
                ...s.topics.map((t) => (
                  <tr key={t.id}>
                    <td>
                      <button className="link-btn strong-link" onClick={() => startTopic(t.id)}>
                        {t.title}
                      </button>
                    </td>
                    <td className="w-bar">
                      <div className="bar-cell">
                        <Bar value={t.mastery} size="sm" />
                        <span className="num small">{pct(t.mastery)}</span>
                      </div>
                    </td>
                    <td className="right num">{t.sessions}</td>
                    <td className="right">
                      <StatusPill status={t.status} />
                    </td>
                  </tr>
                )),
              ])}
            </tbody>
          </table>
        </Card>

        <div className="stack">
          <Card title="Subject progress">
            <div className="stack-sm">
              {p.subjects.map((s) => (
                <div key={s.id} className="labeled-bar">
                  <div className="labeled-bar-top">
                    <span>{s.name}</span>
                    <span className="num">{pct(s.mastery)}</span>
                  </div>
                  <Bar value={s.mastery} />
                  <div className="muted small">
                    {s.topics_started} of {s.topics_total} topics started
                  </div>
                </div>
              ))}
            </div>
          </Card>
          <Card title="Strengths">
            {p.strengths.length ? (
              <ul className="focus-list">
                {p.strengths.map((a) => (
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
              <p className="muted">No strengths recorded yet.</p>
            )}
          </Card>
          <Card title="Areas to improve">
            {p.areas_to_improve.length ? (
              <ul className="focus-list">
                {p.areas_to_improve.map((a) => (
                  <li key={`${a.topic_id}-${a.concept}`}>
                    <div>
                      <div className="focus-name">{a.concept}</div>
                      <div className="muted small">{a.topic_title}</div>
                    </div>
                    <StatusPill status={a.status} />
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">Nothing flagged. Nice work.</p>
            )}
          </Card>
        </div>
      </div>

      <Card title="Recent sessions" padded={false} className="rise" style={{ animationDelay: "300ms" }}>
        {p.recent_sessions.length ? (
          <table className="table table-padded">
            <thead>
              <tr>
                <th>Topic</th>
                <th>Date</th>
                <th className="right">Score</th>
                <th className="right">Mastery</th>
                <th className="right">Result</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {p.recent_sessions.map((s) => (
                <tr key={s.id}>
                  <td>
                    <div className="strong">{s.topic_title}</div>
                    <div className="muted small">{s.subject_name}</div>
                  </td>
                  <td className="muted">{formatDate(s.created_at)}</td>
                  <td className="right num">
                    {s.correct}/{s.attempted}
                  </td>
                  <td className="right num">{pct(s.mastery)}</td>
                  <td className="right">
                    <span className={`band band-${s.band.toLowerCase()}`}>{s.band}</span>
                  </td>
                  <td className="right">
                    <button className="link-btn" onClick={() => navigate("report", s.id)}>
                      View report
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="card-body muted">No completed sessions yet.</div>
        )}
      </Card>
    </>
  );
}
