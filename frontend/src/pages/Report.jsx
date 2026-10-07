import { api } from "../api.js";
import { Card, ErrorState, Icon, Loading, MasteryRing, Metric, PageHeader, StatusPill } from "../components/ui.jsx";
import { startTopic } from "../lib/actions.js";
import { navigate, pct } from "../lib/router.js";
import { useLoad } from "../lib/useLoad.js";

const VERDICT_LABELS = { correct: "Correct", incorrect: "Incorrect", needs_review: "Needs review" };

export default function Report({ id }) {
  const { data: r, error, loading, reload } = useLoad(() => api.report(id), [id]);

  if (loading) return <Loading label="Preparing your learning report…" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const rec = r.recommendation;
  const retakeIsNext = rec.next_topic_id === r.topic_id;

  return (
    <>
      <PageHeader
        eyebrow={`Learning Report · ${r.subject_name}`}
        title={r.topic_title}
        subtitle="Teacher assessment of your most recent session on this topic."
        actions={
          <>
            <button className="btn btn-secondary" onClick={() => navigate("dashboard")}>
              Dashboard
            </button>
            <button className="btn btn-secondary" onClick={() => startTopic(r.topic_id)}>
              <Icon name="refresh" size={15} /> Restart topic
            </button>
          </>
        }
      />

      <section className="card assessment rise">
        <div className="assessment-ring">
          <MasteryRing value={r.mastery} size={132} stroke={10} />
          <span className={`band band-${r.band.toLowerCase()}`}>{r.band}</span>
        </div>
        <div className="assessment-body">
          <div className="eyebrow">Teacher's assessment</div>
          <p className="assessment-text">{r.summary}</p>
          <div className="assessment-sign">— SkillForge Teacher Agent</div>
          {r.learner_model && (
            <div className="lm-note">
              <span className="status-dot" /> Adaptive learner model updated · your concept estimates carry into the
              next session
            </div>
          )}
        </div>
      </section>

      <div className="grid grid-5">
        <Metric label="Overall score" value={pct(r.score)} delay={60} />
        <Metric label="Mastery" value={pct(r.mastery)} sub={r.band} delay={110} />
        <Metric label="Correct answers" value={`${r.correct} / ${r.attempted}`} delay={160} />
        <Metric label="Questions completed" value={r.attempted} delay={210} />
        <Metric label="Highest level" value={r.highest_level_label || "—"} sub={`Started at ${r.starting_level_label}`} delay={260} />
      </div>

      <div className="grid grid-2">
        <Card title="Concept breakdown" className="rise" style={{ animationDelay: "200ms" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Concept</th>
                <th className="right">Result</th>
                {r.learner_model && <th className="right">Model estimate</th>}
                <th className="right">Status</th>
              </tr>
            </thead>
            <tbody>
              {r.concepts.map((c) => (
                <tr key={c.id}>
                  <td>{c.name}</td>
                  <td className="right num">{c.attempted ? `${c.correct} / ${c.attempted}` : "—"}</td>
                  {r.learner_model && <td className="right num">{pct(c.estimate)}</td>}
                  <td className="right">
                    <StatusPill status={c.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="table-note muted small">
            Status reflects your answers in this session.
            {r.learner_model &&
              " Model estimate is the offline Bayesian learner model's probability that you know the concept, accumulated across sessions (configured parameters, not a trained model)."}
          </p>
        </Card>

        <Card title="Strengths and areas to improve" className="rise" style={{ animationDelay: "260ms" }}>
          <div className="sw">
            <div>
              <div className="sw-title ok">Strong concepts</div>
              {r.strengths.length ? (
                <ul className="sw-list">
                  {r.strengths.map((s) => (
                    <li key={s}>
                      <Icon name="check" size={14} /> {s}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="muted small">None secured yet — strengths appear after consistent correct answers.</p>
              )}
            </div>
            <div>
              <div className="sw-title bad">Areas to improve</div>
              {r.weak_areas.length || r.developing.length ? (
                <ul className="sw-list">
                  {r.weak_areas.map((s) => (
                    <li key={s}>
                      <Icon name="flag" size={14} /> {s} <span className="small">(needs review)</span>
                    </li>
                  ))}
                  {r.developing.map((s) => (
                    <li key={s} className="muted">
                      <Icon name="arrowRight" size={14} /> {s} <span className="small">(developing)</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="muted small">No weak concepts in this session.</p>
              )}
            </div>
          </div>
        </Card>
      </div>

      <section className={`card recommendation rec-${rec.action} rise`} style={{ animationDelay: "320ms" }}>
        <div className="card-body rec-body">
          <div>
            <div className="eyebrow">Teacher recommendation</div>
            <h2 className="rec-title">{rec.headline}</h2>
            <p>{rec.text}</p>
            <div className="rec-next">
              Suggested next topic: <strong>{rec.next_topic_title}</strong>
              <span className="muted"> · {rec.next_subject_name}</span>
            </div>
          </div>
          <div className="rec-actions">
            <button className="btn btn-primary" onClick={() => startTopic(rec.next_topic_id)}>
              {retakeIsNext ? `Retake ${r.topic_title}` : `Continue to ${rec.next_topic_title}`}
              <Icon name="arrowRight" size={16} />
            </button>
            {!retakeIsNext && (
              <button className="btn btn-secondary" onClick={() => startTopic(r.topic_id)}>
                Retake {r.topic_title}
              </button>
            )}
          </div>
        </div>
      </section>

      <Card title="Question review" padded={false} className="rise" style={{ animationDelay: "380ms" }}>
        <ol className="review">
          {r.review.map((q) => (
            <li key={q.number} className="review-item">
              <span className={`review-mark mark-${q.verdict}`}>
                <Icon name={q.correct ? "check" : "x"} size={14} />
              </span>
              <div className="review-body">
                <div className="review-meta">
                  Q{q.number} · {q.concept_name} · {q.difficulty_label}
                  <span className={`verdict-text v-${q.verdict}`}>{VERDICT_LABELS[q.verdict]}</span>
                </div>
                <div className="review-prompt">{q.prompt.split("\n\n").pop()}</div>
                <div className="review-answers">
                  <span>
                    Your answer: <strong>{q.your_answer}</strong>
                  </span>
                  {!q.correct && (
                    <span>
                      Correct answer: <strong>{q.correct_answer}</strong>
                    </span>
                  )}
                </div>
                <p className="review-expl muted">{q.explanation}</p>
              </div>
            </li>
          ))}
        </ol>
      </Card>
    </>
  );
}
