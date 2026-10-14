import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { RecCard } from "../components/learning.jsx";
import { ErrorState, Icon, Loading, StatusPill } from "../components/ui.jsx";
import { startTopic } from "../lib/actions.js";
import { STATUS_LABELS, navigate, pct, roman } from "../lib/router.js";
import { useLoad } from "../lib/useLoad.js";
import { AREAS, ROADMAP, areaOf, placeOf } from "../lib/catalog.js";
import { KnowledgeWorld, Motif } from "../components/world.jsx";
import { withViewTransition } from "../components/motion.jsx";

// ============================================================================
// SKILLFORGE LEARNING UNIVERSE & CURRICULUM EXPLORER
// First-Class Learning Areas: Core CS, AI/ML, Modern AI, AI Engineering, DSA
// Visual Motifs: Subject-specific animated SVG graphics and branching pathways
// NO SUBJECT CODES: Only clean human-readable domain names.
// ============================================================================

function ConceptNodes({ concepts }) {
  if (!concepts?.length) return null;
  return (
    <div className="concept-branch">
      <div className="concept-branch-header">
        <span className="concept-branch-title">Knowledge nodes</span>
        <span className="muted small">Estimates calibrated from your graded answers</span>
      </div>
      <ul className="concepts-landscape">
        {concepts.map((c, i) => (
          <li key={c.id || i} className={`concept-node st-${c.status || "not_started"}`}>
            <div className="concept-node-indicator" />
            <div className="concept-node-body">
              <span className="concept-node-name">{c.name}</span>
              <span className="concept-node-ev muted small">
                {c.attempts ? `${c.correct}/${c.attempts} correct` : "Unassessed"}
              </span>
            </div>
            <div className="concept-node-score">
              <span className="concept-p num">{c.p_known == null || !c.attempts ? "—" : pct(c.p_known)}</span>
              <StatusPill
                status={c.status === "learning" ? "in_progress" : c.status || "not_started"}
                label={STATUS_LABELS[c.status] || (c.status === "learning" ? "Learning" : "Unassessed")}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function TopicPath({ t, index, concepts, focus }) {
  const [open, setOpen] = useState(focus);
  const ref = useRef(null);

  useEffect(() => {
    if (focus) ref.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [focus]);

  const status = t.progress?.status;
  const sessionId = t.active_session_id;

  let action;
  if (!t.assessable) {
    action = <span className="topic-unavailable">Curriculum Roadmap</span>;
  } else if (sessionId) {
    action = (
      <button className="btn btn-primary btn-sm" onClick={() => navigate("session", sessionId)}>
        Continue <Icon name="arrowRight" size={14} />
      </button>
    );
  } else {
    const label = status === "needs_review" ? "Review" : t.progress?.sessions ? "Practise again" : "Start";
    action = (
      <button
        className={`btn btn-sm ${status === "needs_review" || !t.progress?.sessions ? "btn-primary" : "btn-secondary"}`}
        onClick={() => startTopic(t.id)}
      >
        {label} <Icon name="arrowRight" size={14} />
      </button>
    );
  }

  const assessed = t.progress?.concepts_assessed ?? 0;

  return (
    <li ref={ref} className={`topic-branch ${t.assessable ? "" : "is-muted"} ${open ? "open" : ""} ${focus ? "focus" : ""}`}>
      <div className="topic-branch-row">
        <div className="topic-branch-stem" aria-hidden="true">
          <span className="topic-node-dot" />
          <span className="topic-num num">{index}</span>
        </div>

        <div className="topic-main">
          {t.assessable ? (
            <button className="topic-title-btn" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
              <span className="topic-title">{t.title}</span>
              <Icon name="plus" size={13} className="topic-toggle-icon" />
            </button>
          ) : (
            <span className="topic-title static">{t.title}</span>
          )}
          <div className="topic-sub muted small">
            {t.assessable
              ? `${t.level || "Standard"} · ${t.concepts?.length || 0} concepts · ${assessed} assessed`
              : t.summary || "Syllabus topic roadmap"}
          </div>
          {status === "needs_review" && t.progress.needs_review.length > 0 && (
            <div className="topic-flag small">
              <Icon name="flag" size={12} /> Review: {t.progress.needs_review.join(", ")}
            </div>
          )}
        </div>

        <div className="topic-state">
          {t.assessable &&
            (sessionId ? (
              <span className="pill pill-live">
                <span className="live-dot" /> In session
              </span>
            ) : (
              <StatusPill status={status} />
            ))}
          {t.progress?.mastery != null && <span className="num topic-pct">{pct(t.progress.mastery)}</span>}
        </div>

        <div className="topic-action">{action}</div>
      </div>

      {open && (
        <div className="topic-expanded">
          <ConceptNodes concepts={concepts || t.concepts} />
        </div>
      )}
    </li>
  );
}

export default function Topics({ query }) {
  const { data, error, loading, reload } = useLoad(async () => {
    const [topics, state, recs] = await Promise.all([api.topics(), api.learnerState(), api.recommendations()]);
    return { topics, state, recs };
  });

  if (loading) return <Loading label="Unfolding your knowledge map…" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const summary = Object.fromEntries(data.state.subjects.map((s) => [s.id, s]));
  const conceptsByTopic = Object.fromEntries(
    data.state.subjects.flatMap((s) => s.topics.map((t) => [t.id, t.concepts]))
  );
  // Real subjects take their place on the map by id; roadmap entries have no content.
  const live = data.topics.subjects.map((s) => ({ ...s, ...placeOf(s), isLive: true }));
  const all = [...live, ...ROADMAP];
  const recs = data.recs.recommendations;
  const heading = recs.find((r) => r.subject_id)?.subject_id;
  const selected =
    all.find((s) => s.id === query?.subject) ||
    (query?.area && all.find((s) => s.area === query.area)) ||
    live.find((s) => s.id === heading) ||
    live[0];
  const sum = summary[selected.id];
  const rec = recs.find((r) => r.subject_id === selected.id);
  const area = areaOf(selected.area);
  const areaSubjects = all.filter((s) => s.area === selected.area);
  const places = all.map((s) => {
    const ss = summary[s.id];
    return {
      id: s.id,
      name: s.name,
      short: s.short || s.short_name || s.name,
      area: s.area,
      motif: s.motif,
      roadmap: !!s.roadmap,
      estimate: ss?.assessed ? ss.estimate : null,
      status: ss?.needs_review ? "needs_attention" : undefined,
    };
  });
  const open = (id) => withViewTransition(() => navigate("learn", null, { subject: id }));

  return (
    <div className="learn-landscape">
      <header className="landscape-hero rise">
        <div className="eyebrow">Learn</div>
        <h1 className="display landscape-headline">Your knowledge world</h1>
        <p className="landscape-sub">
          <span className="map-only">
            Areas are territories and subjects are places. Rings fill as your estimated mastery grows; the orange route
            leads to what the recommendation engine suggests next. Dashed places are roadmap only.
          </span>
          <span className="list-only">Choose an area, then a subject. Roadmap subjects have no practice yet.</span>
        </p>
      </header>

      <KnowledgeWorld
        places={places}
        here={heading}
        selected={selected.id}
        focusArea={selected.area}
        onSelect={open}
        caption="Select a place to open it. Dashed places have no lessons or questions yet."
      />

      <nav className="area-tabs-nav rise" aria-label="Learning areas">
        {AREAS.map((a) => (
          <button
            key={a.id}
            className={`area-tab-chip tone-${a.tone} ${selected.area === a.id ? "active" : ""}`}
            onClick={() => open((all.find((s) => s.area === a.id && s.isLive) || all.find((s) => s.area === a.id)).id)}
          >
            <span className="area-dot" />
            <span>{a.name}</span>
          </button>
        ))}
      </nav>

      <div className="landscape-layout">
        <aside className="landscape-nav" aria-label={`${area.name} subjects`}>
          <div className="landscape-area-group">
            <div className="landscape-area-tag">
              <span className="landscape-area-dot" />
              {area.name}
            </div>
            <ul className="landscape-subject-list">
              {areaSubjects.map((s) => {
                const ss = summary[s.id];
                const on = s.id === selected.id;
                return (
                  <li key={s.id}>
                    <button
                      className={`landscape-subject-btn ${on ? "active" : ""} ${s.roadmap ? "is-roadmap" : ""}`}
                      aria-current={on ? "true" : undefined}
                      onClick={() => open(s.id)}
                    >
                      <div className="subject-btn-left">
                        <span className="landscape-subject-name">{s.name}</span>
                        <span className="landscape-subject-sub muted small">
                          {s.roadmap ? "Roadmap · coming soon" : `${s.units?.length || 0} units · practice available${s.note ? ` · ${s.note}` : ""}`}
                        </span>
                      </div>
                      <span className="landscape-subject-meta num">{ss?.assessed ? pct(ss.estimate) : "—"}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        </aside>

        <article className="landscape-domain" key={selected.id}>
          <header className="domain-header">
            <div className="domain-top-motif">
              <svg viewBox="-24 -24 48 48" width="54" height="54" className={`tone-${area.tone}`} aria-hidden="true">
                <circle r="22" className="domain-motif-disc" />
                <Motif type={selected.motif} s={1.25} />
              </svg>
              <div className="domain-badge-group">
                <span className="domain-area-badge">{area.name}</span>
                <span className={`domain-kind-badge ${selected.roadmap ? "roadmap" : ""}`}>
                  {selected.roadmap ? "Roadmap · coming soon" : "Practice available"}
                </span>
              </div>
            </div>
            <h2 className="display domain-title">{selected.name}</h2>
            <p className="domain-desc">{selected.description || selected.summary}</p>

            {!selected.roadmap && (
              <div className="domain-overview-bar">
                <div className="domain-stat">
                  <span className="domain-stat-label">Estimated mastery</span>
                  <span className="domain-stat-value num">{sum?.assessed ? pct(sum.estimate) : "—"}</span>
                </div>
                <div className="domain-coverage">
                  <div className="coverage-bar" role="img" aria-label={`${sum?.assessed ?? 0} of ${sum?.total ?? 0} concepts assessed`}>
                    <span style={{ width: `${sum?.total ? (100 * sum.assessed) / sum.total : 0}%` }} />
                  </div>
                  <span className="muted small">
                    Coverage: {sum?.assessed ?? 0} of {sum?.total ?? 0} concepts assessed
                    {sum?.total ? "" : " (no question bank in this subject yet)"}
                  </span>
                </div>
              </div>
            )}
          </header>

          {selected.roadmap ? (
            <div className="roadmap-note">
              <p>
                <strong>This subject is on the roadmap.</strong> It has no lessons, questions or progress yet, so there
                is nothing to practise here today. It will open once a reviewed question bank is added.
              </p>
              {areaSubjects.some((s) => s.isLive) && (
                <p className="muted small">
                  Practice available in {area.name} today:{" "}
                  {areaSubjects.filter((s) => s.isLive).map((s, i, arr) => (
                    <span key={s.id}>
                      <button className="link-btn" onClick={() => open(s.id)}>{s.name}</button>
                      {i < arr.length - 1 ? ", " : ""}
                    </span>
                  ))}
                </p>
              )}
            </div>
          ) : (
            <>
              {rec && (
                <div className="domain-rec-callout">
                  <div className="kicker">Recommended next step in this subject</div>
                  <RecCard rec={rec} />
                </div>
              )}
              <div className="domain-units">
                {selected.units?.map((u) => (
                  <section key={u.number} className="unit-sector">
                    <header className="unit-sector-header">
                      <div className="unit-mark-row">
                        <span className="unit-mark">{selected.unit_label || "Unit"} {roman(u.number)}</span>
                        <span className="unit-topics-count muted small">{u.topics?.length || 0} topics</span>
                      </div>
                      <h3 className="display unit-title">{u.title}</h3>
                    </header>
                    <ol className="unit-topics-branch">
                      {u.topics?.map((t, tIdx) => (
                        <TopicPath
                          key={t.id}
                          t={t}
                          index={`${u.number}.${tIdx + 1}`}
                          concepts={conceptsByTopic[t.id]}
                          focus={query?.topic === t.id}
                        />
                      ))}
                    </ol>
                  </section>
                ))}
              </div>
            </>
          )}
        </article>
      </div>
    </div>
  );
}
