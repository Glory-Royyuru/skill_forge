import { api } from "../api.js";
import { ConceptRow, Estimate, RecList, TrendChart } from "../components/learning.jsx";
import { Card, ErrorState, Loading, PageHeader } from "../components/ui.jsx";
import { formatDate, navigate, pct } from "../lib/router.js";
import { useLoad } from "../lib/useLoad.js";
import Review from "./Review.jsx";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "subjects", label: "Subject analysis" },
  { id: "trends", label: "Trends" },
  { id: "recommendations", label: "Recommendations" },
];

function useAll() {
  return useLoad(async () => {
    const [state, overview, trends, recs] = await Promise.all([
      api.learnerState(),
      api.overview(),
      api.trends(8),
      api.recommendations(),
    ]);
    return { state, overview, trends, recs };
  });
}

function LevelCard({ level }) {
  const span = level.next_level_at - level.level_floor;
  const done = Math.round(((level.xp - level.level_floor) / span) * 100);
  return (
    <Card title="Activity level" action={<span className="muted small">Separate from mastery</span>}>
      <div className="level-row">
        <span className="level-badge display">Level {level.level}</span>
        <div className="level-bar">
          <div style={{ width: `${done}%` }} />
        </div>
        <span className="muted small num">{level.xp} XP</span>
      </div>
      <p className="muted small">{level.note}</p>
    </Card>
  );
}

function Overview({ state, overview }) {
  const o = state.overall;
  const subjects = state.subjects.filter((s) => s.assessed > 0);
  // A subject is only called strong or weak once it has enough answers to say so.
  const enough = (s) => s.attempts >= MIN_SUBJECT_ANSWERS;
  const strong = subjects.filter((s) => enough(s) && s.estimate >= 0.7 && s.needs_review === 0);
  const attention = subjects.filter((s) => s.needs_review > 0 || (enough(s) && s.estimate < 0.5));
  const early = subjects.filter((s) => !strong.includes(s) && !attention.includes(s));
  return (
    <>
      <h2 className="ledger-heading display">Mastery <span>estimated per concept from graded answers</span></h2>
      <section className="ledger-strip ledger-4" aria-label="Knowledge summary">
        <div className="lg-item">
          <span className="lg-k">Estimated knowledge</span>
          <span className="lg-v num">{pct(o.estimate)}</span>
          <span className="lg-s">{o.assessed ? `across ${o.assessed} of ${o.total} concepts` : "no evidence yet"}</span>
        </div>
        <div className="lg-item">
          <span className="lg-k">Mastered</span>
          <span className="lg-v num">{o.mastered}</span>
          <span className="lg-s">several correct answers, incl. harder ones</span>
        </div>
        <div className="lg-item">
          <span className="lg-k">Needs review</span>
          <span className="lg-v num">{o.needs_review}</span>
          <span className="lg-s">repeated mistakes or a low estimate</span>
        </div>
        <div className="lg-item">
          <span className="lg-k">Graded answers</span>
          <span className="lg-v num">{o.attempts}</span>
          <span className="lg-s">{o.attempts ? `${o.correct} correct` : "none yet"}</span>
        </div>
      </section>
      {!o.assessed ? (
        <Card>
          <div className="empty">
            <p>No learning evidence yet.</p>
            <p className="muted small">Progress is built from graded answers. Take the diagnostic or a Teacher session to begin.</p>
            <button className="btn btn-primary btn-sm" onClick={() => navigate("diagnostic")}>Take the diagnostic</button>
          </div>
        </Card>
      ) : (
        <div className="grid grid-2">
          <Card title="Progressing well">
            {strong.length ? (
              <ul className="focus-list">
                {strong.map((s) => (
                  <li key={s.id}>
                    <div><div className="focus-name">{s.name}</div><div className="muted small">{s.assessed} of {s.total} concepts assessed · {s.attempts} graded answers</div></div>
                    <span className="focus-est"><span className="num strong">{pct(s.estimate)}</span><span className="muted small">estimated</span></span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">No subject is consistently strong yet. That takes several correct answers per concept.</p>
            )}
          </Card>
          <Card title="Needs attention">
            {attention.length ? (
              <ul className="focus-list">
                {attention.map((s) => (
                  <li key={s.id}>
                    <div>
                      <div className="focus-name">{s.name}</div>
                      <div className="muted small">
                        {s.needs_review
                          ? `${s.needs_review} concept${s.needs_review === 1 ? " needs" : "s need"} review`
                          : "low estimate"}{" "}
                        · {s.attempts} graded answer{s.attempts === 1 ? "" : "s"}
                      </div>
                    </div>
                    <span className="focus-est"><span className="num strong">{pct(s.estimate)}</span><span className="muted small">estimated</span></span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">Nothing flagged.</p>
            )}
          </Card>
        </div>
      )}
      {early.length > 0 && (
        <p className="muted small early-note">
          Too early to say for {early.map((s) => s.name).join(", ")}: fewer than {MIN_SUBJECT_ANSWERS} graded answers
          so far.
        </p>
      )}
      {overview.recent_sessions.length > 0 && (
        <h2 className="ledger-heading display">Assessment <span>scores from recent Teacher sessions</span></h2>
      )}
      {overview.recent_sessions.length > 0 && (
        <Card title="Recent sessions" padded={false}>
          <table className="table table-padded">
            <thead><tr><th>Topic</th><th>When</th><th className="right">Score</th><th /></tr></thead>
            <tbody>
              {overview.recent_sessions.map((s) => (
                <tr key={s.id}>
                  <td><div className="strong">{s.topic_title}</div><div className="muted small">{s.subject_name}</div></td>
                  <td className="muted">{formatDate(s.created_at)}</td>
                  <td className="right num">{s.correct}/{s.attempted}</td>
                  <td className="right"><button className="link-btn" onClick={() => navigate("report", s.id)}>Report</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      <h2 className="ledger-heading display">Activity <span>practice effort, kept separate from knowledge</span></h2>
      <LevelCard level={overview.activity_level} />
    </>
  );
}

const MIN_SUBJECT_ANSWERS = 3;

function Subjects({ state }) {
  return (
    <>
      {state.subjects.map((s) => (
        <Card key={s.id} title={s.name} action={<span className="muted small">{s.topics.length} topics</span>}>
          <div className="subject-analysis">
            <Estimate value={s.estimate} assessed={s.assessed} total={s.total} />
            <div className="sa-stats small">
              <span><strong className="num">{s.attempts}</strong> graded answers</span>
              <span><strong className="num">{s.attempts ? pct(s.correct / s.attempts) : "—"}</strong> correct</span>
              <span><strong className="num">{s.mastered}</strong> mastered</span>
              <span><strong className="num">{s.needs_review}</strong> need review</span>
            </div>
          </div>
          {s.assessed === 0 ? (
            <p className="muted small">No evidence in this subject yet.</p>
          ) : (
            s.topics.filter((t) => t.assessed).map((t) => (
              <div key={t.id} className="sa-topic">
                <div className="sa-topic-head">
                  <span className="strong">{t.title}</span>
                  <span className="muted small">{t.assessed}/{t.total} concepts · {pct(t.estimate)}</span>
                </div>
                <ul className="concept-rows">
                  {t.concepts.filter((c) => c.attempts).map((c) => <ConceptRow key={c.id} c={c} />)}
                </ul>
              </div>
            ))
          )}
        </Card>
      ))}
      <p className="muted small">{state.method}</p>
    </>
  );
}

function Trends({ weeks }) {
  const any = weeks.some((w) => w.graded_answers > 0);
  return (
    <Card title="Weekly learning">
      {!any ? (
        <p className="muted">Trends appear once you have answered questions.</p>
      ) : (
        <>
          <TrendChart weeks={weeks} />
          <div className="trend-legend muted small">
            <span><i className="lg-bar" /> Graded answers</span>
            <span><i className="lg-line" /> Mean estimated knowledge of practised concepts</span>
          </div>
          <div className="card-flush">
            <table className="table">
              <thead><tr><th>Week of</th><th className="right">Answers</th><th className="right">Correct</th><th className="right">Concepts</th><th className="right">Active days</th></tr></thead>
              <tbody>
                {weeks.filter((w) => w.graded_answers).map((w) => (
                  <tr key={w.week_start}>
                    <td>{w.week_start}</td><td className="right num">{w.graded_answers}</td><td className="right num">{pct(w.accuracy)}</td>
                    <td className="right num">{w.concepts_practised}</td><td className="right num">{w.active_days}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Card>
  );
}

// PTM mode replaces Progress with the full Student Performance Review.
export default function LearningProgress({ query, mode }) {
  return mode === "ptm" ? <Review /> : <StudentProgress query={query} />;
}

// Activity ≠ Assessment ≠ Mastery: three separate tracks, never one number.
function ThreeMeasures({ overview, state }) {
  const lvl = overview.activity_level;
  const span = Math.max(1, lvl.next_level_at - lvl.level_floor);
  const sessions = overview.recent_sessions || [];
  const att = sessions.reduce((n, s) => n + s.attempted, 0);
  const cor = sessions.reduce((n, s) => n + s.correct, 0);
  const o = state.overall;
  const tracks = [
    {
      k: "Activity", tone: "gold", what: "how much you practised",
      v: `Level ${lvl.level}`, sub: `${lvl.xp} XP · ${lvl.next_level_at - lvl.xp} to the next level`,
      fill: (lvl.xp - lvl.level_floor) / span,
    },
    {
      k: "Assessment", tone: "orange", what: "how recent sessions went",
      v: att ? pct(cor / att) : "—",
      sub: att ? `${cor} of ${att} correct in ${sessions.length} recent session${sessions.length === 1 ? "" : "s"}` : "no completed Teacher sessions yet",
      fill: att ? cor / att : 0,
    },
    {
      k: "Mastery", tone: "cobalt", what: "what you know",
      v: o.assessed ? pct(o.estimate) : "—",
      sub: o.assessed
        ? `estimate over ${o.assessed} of ${o.total} concepts (${Math.round((o.coverage || 0) * 100)}% coverage) · ${o.total - o.assessed} with no evidence yet`
        : `no graded answers yet · ${o.total} concepts with a question bank`,
      fill: o.assessed ? o.estimate * o.coverage : 0,
    },
  ];
  return (
    <>
    <section className="measures rise" aria-label="Activity, assessment and mastery">
      {tracks.map((t, i) => (
        <div key={t.k} className={`measure tone-${t.tone}`} style={{ "--i": i }}>
          <div className="measure-head">
            <span className="measure-k">{t.k}</span>
            <span className="measure-what">{t.what}</span>
          </div>
          <div className="measure-v display num">{t.v}</div>
          <div className="measure-track" aria-hidden="true">
            <span style={{ "--f": Math.max(0, Math.min(1, t.fill)) }} />
          </div>
          <div className="measure-sub">{t.sub}</div>
          {i < 2 && <span className="measure-neq" aria-hidden="true">≠</span>}
        </div>
      ))}
    </section>
    <p className="measures-note">
      Three separate measures, never combined into one score. Activity counts effort, assessment is how sittings went,
      and mastery is the per-concept estimate with how much evidence stands behind it.
    </p>
    </>
  );
}
function StudentProgress({ query }) {
  const tab = TABS.some((t) => t.id === query?.tab) ? query.tab : "overview";
  const { data, error, loading, reload } = useAll();
  return (
    <>
      <PageHeader eyebrow="Progress" title="What you know, and why"
        subtitle="Built from your graded answers, concept by concept. Every estimate shows how much evidence stands behind it." />
      {data && <ThreeMeasures overview={data.overview} state={data.state} />}
      <div className="tabs rise" role="tablist">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} className={`tab ${tab === t.id ? "on" : ""}`}
            onClick={() => navigate("progress", null, { tab: t.id })}>{t.label}</button>
        ))}
      </div>
      {loading && <Loading />}
      {error && <ErrorState error={error} onRetry={reload} />}
      {data && (
        <div key={tab} className="rise stack">
          {tab === "overview" && <Overview state={data.state} overview={data.overview} />}
          {tab === "subjects" && <Subjects state={data.state} />}
          {tab === "trends" && <Trends weeks={data.trends.weeks} />}
          {tab === "recommendations" && (
            <Card title="Recommended next steps" action={<span className="muted small">Ordered by priority</span>}>
              <RecList recs={data.recs.recommendations} empty="Take the diagnostic or a session to get recommendations." />
            </Card>
          )}
        </div>
      )}
    </>
  );
}
