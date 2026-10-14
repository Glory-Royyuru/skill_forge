// Shared presentation for learner-intelligence data: recommendations,
// concept estimates with evidence, and simple honest charts.
import { Icon, StatusPill } from "./ui.jsx";
import { actOn } from "../lib/actions.js";
import { pct } from "../lib/router.js";

const ACTION_LABELS = {
  take_diagnostic: "Start diagnostic",
  continue_session: "Continue",
  remediate_misconception: "Fix it now",
  prepare_for_class: "Prepare",
  review_concept: "Review",
  revisit_neglected: "Revisit",
  challenge_up: "Try harder",
  start_new_topic: "Start",
  flashcards: "Open flashcards",
  rapid_round: "Start Rapid Round",
};

const ACTION_KIND = {
  take_diagnostic: "Starting point",
  continue_session: "In progress",
  remediate_misconception: "Misconception",
  prepare_for_class: "Class prep",
  review_concept: "Needs review",
  revisit_neglected: "Keep it fresh",
  challenge_up: "Stretch",
  start_new_topic: "New topic",
  flashcards: "Practice",
  rapid_round: "Practice",
};

export function RecCard({ rec, featured = false }) {
  const where = [rec.subject_name, rec.topic_title].filter(Boolean).join(" → ");
  return (
    <article className={`rec ${featured ? "rec-featured" : ""} rec-${rec.action}`}>
      <div className="rec-top">
        <span className="rec-kind">{ACTION_KIND[rec.action] || rec.action}</span>
        <span className="rec-meta muted small">
          {rec.estimated_minutes} min
          {rec.target_difficulty_label ? ` · ${rec.target_difficulty_label}` : ""}
        </span>
      </div>
      <h3 className="rec-title">{rec.title}</h3>
      {where && <div className="rec-where muted small">{where}</div>}
      <p className="rec-reason">{rec.reason}</p>
      {rec.evidence?.length > 0 && (
        <details className="rec-why" open={featured}>
          <summary>Why this?</summary>
          <ul>
            {rec.evidence.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        </details>
      )}
      <div className="rec-foot">
        <button className={`btn btn-sm ${featured ? "btn-primary" : "btn-secondary"}`} onClick={() => actOn(rec)}>
          {ACTION_LABELS[rec.action] || "Open"} <Icon name="arrowRight" size={14} />
        </button>
      </div>
    </article>
  );
}

export function RecList({ recs, empty = "No recommendations yet." }) {
  if (!recs?.length) return <p className="muted">{empty}</p>;
  return (
    <div className="rec-list">
      {recs.map((r) => (
        <RecCard key={r.id} rec={r} />
      ))}
    </div>
  );
}

// An estimate is always shown with how much evidence stands behind it.
export function Estimate({ value, assessed, total, label = "Estimated knowledge" }) {
  if (value == null) {
    return (
      <div className="estimate">
        <div className="estimate-row">
          <span className="muted small">{label}</span>
          <span className="muted small">No evidence yet</span>
        </div>
        <div className="bar bar-sm" />
      </div>
    );
  }
  return (
    <div className="estimate">
      <div className="estimate-row">
        <span className="muted small">{label}</span>
        <span className="num strong">{pct(value)}</span>
      </div>
      <div className="bar bar-sm">
        <div className="bar-fill tone-accent" style={{ width: `${Math.round(value * 100)}%` }} />
      </div>
      {total != null && (
        <div className="estimate-cov muted small">
          {assessed} of {total} concept{total === 1 ? "" : "s"} assessed
        </div>
      )}
    </div>
  );
}

export function ConceptRow({ c, as: Tag = "li" }) {
  return (
    <Tag className={`concept-row st-${c.status}`}>
      <div className="concept-row-main">
        <div className="concept-row-name">{c.name}</div>
        <div className="muted small">{c.topic_title}</div>
        {c.evidence?.length > 0 && <div className="concept-row-ev small">{c.evidence.join(" · ")}</div>}
      </div>
      <div className="concept-row-side">
        <StatusPill status={c.status === "learning" ? "in_progress" : c.status} />
        <span className="num small">{c.p_known == null ? "—" : pct(c.p_known)}</span>
      </div>
    </Tag>
  );
}

// Weekly trend: bars = graded answers, line = mean estimated knowledge.
export function TrendChart({ weeks }) {
  const W = 560;
  const H = 180;
  const pad = { l: 34, r: 12, t: 12, b: 28 };
  const iw = W - pad.l - pad.r;
  const ih = H - pad.t - pad.b;
  const maxN = Math.max(1, ...weeks.map((w) => w.graded_answers));
  const step = iw / weeks.length;
  const pts = weeks
    .map((w, i) => (w.estimate == null ? null : [pad.l + step * i + step / 2, pad.t + ih * (1 - w.estimate)]))
    .filter(Boolean);
  return (
    <svg className="trend" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Weekly answers and estimated knowledge">
      {[0, 0.5, 1].map((g) => (
        <g key={g}>
          <line x1={pad.l} x2={W - pad.r} y1={pad.t + ih * (1 - g)} y2={pad.t + ih * (1 - g)} className="trend-grid" />
          <text x={pad.l - 6} y={pad.t + ih * (1 - g) + 4} textAnchor="end" className="trend-axis">
            {Math.round(g * 100)}%
          </text>
        </g>
      ))}
      {weeks.map((w, i) => {
        const h = (w.graded_answers / maxN) * ih * 0.9;
        return (
          <g key={w.week_start}>
            <rect
              x={pad.l + step * i + step * 0.22}
              y={pad.t + ih - h}
              width={step * 0.56}
              height={h}
              rx="3"
              className="trend-bar"
            >
              <title>
                Week of {w.week_start}: {w.graded_answers} graded answers
                {w.accuracy != null ? `, ${Math.round(w.accuracy * 100)}% correct` : ""}
              </title>
            </rect>
            <text x={pad.l + step * i + step / 2} y={H - 8} textAnchor="middle" className="trend-axis">
              {w.week_start.slice(5)}
            </text>
          </g>
        );
      })}
      {pts.length > 1 && <polyline points={pts.map((p) => p.join(",")).join(" ")} className="trend-line" />}
      {pts.map((p, i) => (
        <circle key={i} cx={p[0]} cy={p[1]} r="3.5" className="trend-dot" />
      ))}
    </svg>
  );
}
