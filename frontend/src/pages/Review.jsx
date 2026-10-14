import { useState } from "react";
import { api } from "../api.js";
import { RecCard, TrendChart } from "../components/learning.jsx";
import { Reveal } from "../components/motion.jsx";
import { ErrorState, Icon, Loading, PageHeader, StatusPill } from "../components/ui.jsx";
import { startTopic } from "../lib/actions.js";
import { STATUS_LABELS, formatDate, navigate, pct, roman } from "../lib/router.js";
import { useLoad } from "../lib/useLoad.js";

// Student Performance Review (PTM mode): a teacher-style review of the
// signed-in student's own record. Every figure comes from /api/learner/review,
// which computes it from persisted evidence; nothing here is invented.

const SECTIONS = [
  ["summary", "Summary"],
  ["assessment", "Assessment"],
  ["subjects", "Subjects"],
  ["progress", "Progress"],
  ["strengths", "Strengths & focus"],
  ["behaviour", "Learning patterns"],
  ["profile", "Thinking & difficulty"],
  ["swot", "Findings"],
  ["plan", "Next steps"],
];

const TREND = { improving: "↑ Improving", declining: "↓ Declining", steady: "→ Steady" };
const SOURCE = { session: "Teacher sessions", diagnostic: "Diagnostic", rapid_round: "Rapid Round" };
const CONCEPT_STATUS = { learning: "in_progress" };

function Fig({ k, v, sub }) {
  return (
    <div className="lg-item">
      <span className="lg-k">{k}</span>
      <span className="lg-v num">{v}</span>
      {sub && <span className="lg-s">{sub}</span>}
    </div>
  );
}

// Each section says whether it shows recorded evidence or an interpretation
// derived from it, so a reader can tell figures from judgement.
const BASIS = {
  evidence: "Recorded evidence",
  interpretation: "Interpretation of the record",
  plan: "From the recommendation engine",
};

function Section({ id, title, kicker, basis = "evidence", children }) {
  return (
    <Reveal as="section" className="rv-section" id={`rv-${id}`} aria-labelledby={`rv-${id}-h`}>
      <div className="rv-kick">
        {kicker && <span className="kicker">{kicker}</span>}
        <span className={`rv-basis rv-basis-${basis}`}>{BASIS[basis]}</span>
      </div>
      <h2 className="display rv-h" id={`rv-${id}-h`}>
        {title}
      </h2>
      {children}
    </Reveal>
  );
}

function Empty({ children }) {
  return <p className="rv-empty">{children}</p>;
}

function Trajectory({ points }) {
  if (!points || points.length < 2) return <span className="muted">—</span>;
  return (
    <span className="trajectory num">
      {points.map((p, i) => (
        <span key={i}>
          {i > 0 && <Icon name="arrowRight" size={11} />}
          {Math.round(p * 100)}%
        </span>
      ))}
    </span>
  );
}

function ConceptTable({ concepts }) {
  return (
    <div className="table-scroll">
      <table className="table rv-concepts">
        <thead>
          <tr>
            <th>Concept</th>
            <th className="right">Mastery</th>
            <th className="right">Answers</th>
            <th className="right">Recent</th>
            <th>Highest level</th>
            <th>By question type</th>
            <th>Last practised</th>
            <th>Trend</th>
            <th>Status</th>
            <th>Next step</th>
          </tr>
        </thead>
        <tbody>
          {concepts.map((c) => (
            <tr key={c.id}>
              <td>
                <div className="strong">{c.name}</div>
                {c.evidence.length > 0 && <div className="rv-ev">{c.evidence[0]}</div>}
              </td>
              <td className="right num">{c.attempts ? pct(c.p_known) : "—"}</td>
              <td className="right num">{c.attempts ? `${c.correct}/${c.attempts}` : "0"}</td>
              <td className="right num">{pct(c.recent_accuracy)}</td>
              <td>{c.highest_level || <span className="muted">—</span>}</td>
              <td className="small">
                {Object.keys(c.cognitive).length
                  ? Object.entries(c.cognitive).map(([k, v]) => (
                      <span key={k} className="cog-chip">
                        {k} {v.correct}/{v.attempts}
                      </span>
                    ))
                  : <span className="muted">—</span>}
              </td>
              <td className="small">{c.last_practiced ? formatDate(c.last_practiced) : <span className="muted">Never</span>}</td>
              <td className="small">
                <Trajectory points={c.attempts >= 3 ? c.trajectory : null} />
              </td>
              <td>
                <StatusPill
                  status={CONCEPT_STATUS[c.status] || c.status}
                  label={c.status === "learning" ? "Learning" : STATUS_LABELS[c.status]}
                />
              </td>
              <td>
                <button
                  className="link-btn small"
                  onClick={() =>
                    startTopic(c.action.topic_id, { focus_concept: c.action.concept, target_difficulty: c.action.difficulty })
                  }
                >
                  {c.action.text} · {c.action.minutes} min
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SubjectDrill({ s }) {
  const [open, setOpen] = useState(false);
  return (
    <li className={`rv-subject ${open ? "open" : ""} st-${s.status}`}>
      <button className="rv-subject-row" aria-expanded={open} onClick={() => setOpen((o) => !o)} disabled={!s.has_bank}>
        <span className="rv-subject-name">
          <span className="strong">{s.name}</span>
          <span className="muted small">
            {s.has_bank ? `${s.assessed} of ${s.total} concepts assessed` : "No question bank yet"}
          </span>
        </span>
        <span className="num rv-col">{s.attempts ? pct(s.estimate) : "—"}</span>
        <span className="num rv-col">{s.recent_attempts ? `${pct(s.recent_accuracy)}` : "—"}</span>
        <span className="num rv-col">{s.attempts}</span>
        <span className="rv-col small">{s.trend ? TREND[s.trend] : <span className="muted">—</span>}</span>
        <span className={`rv-status rv-status-${s.status}`}>{s.status_label}</span>
        {s.has_bank && <Icon name="plus" size={14} className="rv-toggle" />}
      </button>
      {open && (
        <div className="rv-units">
          {s.units.map((u) => (
            <div key={u.number} className="rv-unit">
              <div className="unit-mark">
                Unit {roman(u.number)} · <span className="rv-unit-title">{u.title}</span>
              </div>
              {u.topics.map((t) => (
                <div key={t.id} className="rv-topic">
                  <div className="rv-topic-head">
                    <span className="strong">{t.title}</span>
                    <span className="muted small">
                      {t.assessed}/{t.total} concepts · {t.attempts ? pct(t.estimate) : "not started"}
                    </span>
                  </div>
                  <ConceptTable concepts={t.concepts} />
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </li>
  );
}

export default function Review() {
  const { data: r, error, loading, reload } = useLoad(() => api.review());
  if (loading) return <Loading label="Preparing the performance review…" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const o = r.overview;
  const a = r.assessment;
  const b = r.behaviour;
  const imp = o.recent_improvement;

  return (
    <div className="review">
      <PageHeader
        eyebrow="PTM mode · Student Performance Review"
        title={r.student.name}
        subtitle={`${r.student.student_id ? `Registration ID ${r.student.student_id} · ` : ""}Generated ${new Date(
          r.generated_at
        ).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })} from the student's own learning record.`}
        actions={
          <>
            <button className="btn btn-secondary btn-sm no-print" onClick={() => navigate("profile", null, { tab: "settings" })}>
              Mode settings
            </button>
            <button className="btn btn-primary btn-sm no-print" onClick={() => window.print()}>
              Print
            </button>
          </>
        }
      />

      <nav className="rv-toc no-print" aria-label="Review sections">
        {SECTIONS.map(([id, label]) => (
          <a key={id} href={`#rv-${id}`} onClick={(e) => (e.preventDefault(), document.getElementById(`rv-${id}`)?.scrollIntoView({ behavior: "smooth" }))}>
            {label}
          </a>
        ))}
      </nav>

      <Section id="summary" kicker="Executive summary" title={o.label}>
        {!o.has_evidence ? (
          <Empty>
            There are no graded answers yet, so there is nothing to review. Taking the diagnostic or one Teacher
            session will start the record; nothing is shown until then.
          </Empty>
        ) : (
          <>
            <p className="rv-basis-line">
              Based on <strong className="num">{o.questions_attempted}</strong> graded answer{o.questions_attempted === 1 ? "" : "s"} covering{" "}
              <strong className="num">{o.assessed}</strong> of {o.total} concepts that have a question bank
              {o.total ? ` (${Math.round((o.assessed / o.total) * 100)}% coverage)` : ""}. Figures below are counted from that record.
            </p>
            <div className="ledger-strip rv-ledger">
              <Fig k="Estimated mastery" v={pct(o.estimate)} sub={`${o.assessed} of ${o.total} concepts assessed`} />
              <Fig k="Overall accuracy" v={pct(o.accuracy)} sub={`${o.correct} of ${o.questions_attempted} graded answers`} />
              <Fig k="Sessions completed" v={o.sessions_completed} />
              <Fig k="Concepts mastered" v={o.concepts_mastered} sub={`${o.concepts_needing_review} need review`} />
              <Fig k="Topics" v={o.topics_mastered} sub={`mastered · ${o.topics_needing_review} need review`} />
              <Fig k="Active days" v={o.active_days} sub={`${o.active_days_30} in the last 30 days`} />
              <Fig
                k="Recent improvement"
                v={imp ? `+${Math.round(imp.change * 100)} pts` : "—"}
                sub={imp ? `${imp.concept} (${imp.topic})` : "Needs 3+ answers on a concept"}
              />
              <Fig k="Activity level" v={o.activity_level.level} sub={`${o.activity_level.xp} XP · effort, not knowledge`} />
            </div>
          </>
        )}
        <div className="rv-letter">
          <div className="rv-letter-k">Summary for the meeting · interpretation of the figures above</div>
          <dl className="rv-letter-body">
            {r.teacher_summary.map((p) => (
              <div key={p.heading}>
                <dt>{p.heading}</dt>
                <dd>{p.text}</dd>
              </div>
            ))}
          </dl>
          <div className="assessment-sign">Prepared by SkillForge from recorded evidence. No observations were added by hand.</div>
        </div>
      </Section>

      <Section id="assessment" kicker="Marks" title="Assessment performance">
        <p className="rv-note">{a.note}</p>
        <div className="rv-grid-2">
          <div>
            <h3 className="rv-h3">Teacher sessions</h3>
            {a.sessions.length ? (
              <div className="table-scroll">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Topic</th>
                      <th>Completed</th>
                      <th className="right">Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {a.sessions.map((s) => (
                      <tr key={s.id}>
                        <td>
                          <div className="strong">{s.topic_title}</div>
                          <div className="muted small">{s.subject_name}</div>
                        </td>
                        <td className="small">{formatDate(s.completed_at)}</td>
                        <td className="right num">
                          {s.correct}/{s.attempted} <span className="muted">({pct(s.score)})</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="muted small">
                  Average session score: <strong className="num">{pct(a.average_session_score)}</strong> across{" "}
                  {a.sessions_completed} completed session{a.sessions_completed === 1 ? "" : "s"}.
                </p>
              </div>
            ) : (
              <Empty>No completed Teacher sessions yet.</Empty>
            )}
          </div>
          <div>
            <h3 className="rv-h3">Diagnostic and practice</h3>
            <ul className="rv-facts">
              <li>
                <span>Diagnostic</span>
                <strong>
                  {a.diagnostic
                    ? `${a.diagnostic.correct}/${a.diagnostic.answered} correct${a.diagnostic.skipped ? `, ${a.diagnostic.skipped} skipped` : ""}`
                    : "Not taken"}
                </strong>
              </li>
              <li>
                <span>Rapid Round</span>
                <strong>
                  {a.rapid.rounds
                    ? `${a.rapid.correct}/${a.rapid.answered} correct in ${a.rapid.rounds} round${a.rapid.rounds === 1 ? "" : "s"}`
                    : "None yet"}
                </strong>
              </li>
              {Object.entries(a.accuracy_by_source).map(([k, v]) => (
                <li key={k}>
                  <span>{SOURCE[k] || k} accuracy</span>
                  <strong className="num">
                    {pct(v.accuracy)} <span className="muted small">({v.correct}/{v.attempts})</span>
                  </strong>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Section>

      <Section id="subjects" kicker="Subject-wise analysis" title="Subjects, units, topics and concepts">
        <p className="rv-note">
          A subject is assessed after {r.thresholds.subject_answers} graded answers; trends compare the last{" "}
          {r.thresholds.trend_window} answers with the {r.thresholds.trend_window} before them. Open a subject to see
          every unit, topic and concept.
        </p>
        <div className="rv-subject-head" aria-hidden="true">
          <span>Subject</span>
          <span>Mastery</span>
          <span>Recent accuracy</span>
          <span>Answers</span>
          <span>Trend</span>
          <span>Status</span>
        </div>
        <ul className="rv-subjects">
          {r.subjects.map((s) => (
            <SubjectDrill key={s.id} s={s} />
          ))}
        </ul>
      </Section>

      <Section id="progress" kicker="Progress over time" title="How the record has changed">
        {r.progress.weeks.some((w) => w.graded_answers) ? (
          <>
            <TrendChart weeks={r.progress.weeks} />
            <div className="trend-legend muted small">
              <span>
                <i className="lg-bar" /> Graded answers per week
              </span>
              <span>
                <i className="lg-line" /> Mean estimated mastery of practised concepts
              </span>
            </div>
          </>
        ) : (
          <Empty>No weekly activity recorded yet.</Empty>
        )}
        <div className="rv-grid-2">
          <div>
            <h3 className="rv-h3">Meaningful improvements</h3>
            {r.progress.improvements.length ? (
              <ul className="rv-list">
                {r.progress.improvements.map((c) => (
                  <li key={c.concept + c.topic}>
                    <span className="strong">{c.concept}</span> <span className="muted small">· {c.topic}</span>
                    <div>
                      <Trajectory points={c.trajectory} />{" "}
                      <span className="rv-up num">+{Math.round(c.change * 100)} percentage points</span>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty>Improvements are shown after at least three answers on a concept.</Empty>
            )}
          </div>
          <div>
            <h3 className="rv-h3">Declines</h3>
            {r.progress.declines.length ? (
              <ul className="rv-list">
                {r.progress.declines.map((c) => (
                  <li key={c.concept + c.topic}>
                    <span className="strong">{c.concept}</span> <span className="muted small">· {c.topic}</span>
                    <div>
                      <Trajectory points={c.trajectory} />{" "}
                      <span className="rv-down num">{Math.round(c.change * 100)} percentage points</span>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty>No concept has declined across three or more answers.</Empty>
            )}
          </div>
        </div>
      </Section>

      <Section id="strengths" kicker="Strengths and areas for improvement" basis="interpretation" title="What is secure, and what needs attention">
        <div className="rv-grid-2">
          <div>
            <h3 className="rv-h3 ok">Strengths</h3>
            {r.strengths.length ? (
              <ul className="rv-cards">
                {r.strengths.map((s) => (
                  <li key={s.concept + s.topic} className="rv-card rv-card-ok">
                    <div className="strong">{s.concept}</div>
                    <div className="muted small">
                      {s.subject} · {s.topic}
                    </div>
                    <div className="rv-card-facts num">
                      {pct(s.p_known)} estimated mastery · {s.recent} recent correct · {s.highest_level} demonstrated
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty>
                No strength yet. A strength needs several correct answers on a concept, including one at
                Intermediate or harder.
              </Empty>
            )}
          </div>
          <div>
            <h3 className="rv-h3 bad">Areas for improvement</h3>
            {r.improvement_areas.length ? (
              <ul className="rv-cards">
                {r.improvement_areas.map((g) => (
                  <li key={g.concept + g.topic} className="rv-card rv-card-bad">
                    <div className="strong">{g.concept}</div>
                    <div className="muted small">
                      {g.subject} · {g.topic}
                    </div>
                    <div className="rv-card-facts num">
                      {pct(g.p_known)} estimated mastery · {g.recent} recent correct
                      {g.consecutive_incorrect >= 2 ? ` · ${g.consecutive_incorrect} misses in a row` : ""}
                    </div>
                    <button
                      className="link-btn small"
                      onClick={() => startTopic(g.cta.topic_id, { focus_concept: g.cta.concept, target_difficulty: 1 })}
                    >
                      Suggested: {g.suggestion}
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty>No concept currently shows repeated mistakes.</Empty>
            )}
          </div>
        </div>
      </Section>

      <Section id="behaviour" kicker="Learning patterns" title="How the student has been learning">
        <div className="ledger-strip rv-ledger">
          <Fig k="Active days" v={b.active_days} sub={b.first_active ? `since ${b.first_active}` : "none yet"} />
          <Fig k="Sessions" v={`${b.sessions_completed}/${b.sessions_started}`} sub="completed / started" />
          <Fig
            k="Typical session"
            v={b.median_session_minutes != null ? `${b.median_session_minutes} min` : "—"}
            sub={b.median_session_minutes != null ? "median of completed sessions" : "needs 2+ completed sessions"}
          />
          <Fig k="Practice frequency" v={b.days_per_week != null ? `${b.days_per_week}/wk` : "—"} sub={b.enough ? "active days per week" : `needs ${r.thresholds.active_days}+ active days`} />
          <Fig k="Revision answers" v={b.revision_answers} sub="answers on concepts seen before" />
          <Fig k="Flashcards" v={b.flashcards.reviewed} sub={`${b.flashcards.known} known · ${b.flashcards.review} to review`} />
          <Fig k="Rapid Rounds" v={b.rapid_rounds} />
          <Fig
            k="Consistency"
            v={b.longest_streak ? `${b.longest_streak}-day streak` : "—"}
            sub={b.longest_gap_days != null ? `longest gap ${b.longest_gap_days} days` : "gaps need 3+ active days"}
          />
        </div>
        <p className="rv-note">
          {b.median_response_ms ? `Typical answer time ${(b.median_response_ms / 1000).toFixed(1)} s. ` : ""}
          {b.note}
        </p>
      </Section>

      <Section id="profile" kicker="Question types and difficulty" title="Kinds of thinking, and levels reached">
        <div className="rv-grid-2">
          <div>
            <h3 className="rv-h3">By question type</h3>
            <ul className="rv-bars">
              {r.cognitive.rows.map((c) => (
                <li key={c.type} className={c.enough ? "" : "dim"}>
                  <span className="rv-bar-k">{c.label}</span>
                  <span className="rv-bar">
                    <span style={{ width: c.enough ? `${Math.round(c.accuracy * 100)}%` : 0 }} />
                  </span>
                  <span className="rv-bar-v num">
                    {c.enough ? pct(c.accuracy) : "too early"} <span className="muted small">({c.attempts})</span>
                  </span>
                </li>
              ))}
            </ul>
            <p className="rv-note">
              {r.cognitive.summary || `Shown once a type has ${r.cognitive.min_answers} or more graded answers.`}
            </p>
          </div>
          <div>
            <h3 className="rv-h3">By difficulty</h3>
            <ol className="rv-levels">
              {r.difficulty.rows.map((d) => (
                <li key={d.level} className={d.demonstrated ? "on" : ""}>
                  <span className="rv-level-name">{d.label}</span>
                  <span className="num">
                    {d.attempts ? `${d.correct}/${d.attempts} (${pct(d.accuracy)})` : "no answers"}
                  </span>
                  <span className="rv-level-state">
                    {d.demonstrated ? "Demonstrated" : d.enough ? "Not yet reliable" : "Too early"}
                  </span>
                </li>
              ))}
            </ol>
            <p className="rv-note">{r.difficulty.rule}</p>
          </div>
        </div>
      </Section>

      <Section id="swot" kicker="Findings" basis="interpretation" title="Secure, needs work, within reach, at risk">
        <p className="rv-note">Each finding is derived from the evidence above by fixed rules; nothing is added by hand.</p>
        <div className="swot-matrix">
          <div className="swot-grid">
            {[
              ["Secure", "s", r.swot.strengths, "Needs several correct answers on a concept, including harder ones."],
              ["Needs work", "w", r.swot.weaknesses, "No concept currently shows repeated mistakes."],
              ["Within reach", "o", r.swot.opportunities, "Improvements appear after three or more answers on a concept."],
              ["At risk", "t", r.swot.threats, "No neglected concepts or at-risk upcoming classes."],
            ].map(([title, tone, items, empty]) => (
              <section key={title} className={`swot swot-${tone}`}>
                <h3 className="swot-title">{title}</h3>
                {items.length ? (
                  <ul>
                    {items.map((i, n) => (
                      <li key={n}>{i.text}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted small">{empty}</p>
                )}
              </section>
            ))}
          </div>
        </div>
      </Section>

      <Section id="plan" kicker="Suggested next steps" basis="plan" title="Recommended next steps">
        {r.action_plan.length ? (
          <ol className="rv-plan">
            {r.action_plan.map((rec) => (
              <li key={rec.id}>
                <RecCard rec={rec} />
              </li>
            ))}
          </ol>
        ) : (
          <Empty>No recommendations yet.</Empty>
        )}
        <p className="rv-note">{r.evidence_note}</p>
      </Section>
    </div>
  );
}
