import { useState } from "react";
import { api } from "../api.js";
import { Bar, ErrorState, Icon, Loading, PageHeader, StatusPill } from "../components/ui.jsx";
import { startTopic } from "../lib/actions.js";
import { navigate, pct } from "../lib/router.js";
import { useLoad } from "../lib/useLoad.js";

export default function Topics({ active }) {
  const { data, error, loading, reload } = useLoad(() => api.topics());
  const [filter, setFilter] = useState("all");

  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const subjects = data.subjects.filter((s) => filter === "all" || s.id === filter);

  return (
    <>
      <PageHeader
        eyebrow="Curriculum"
        title="What would you like to learn?"
        subtitle="Every session opens with a short lesson, then five questions that adapt to your answers. Your teacher remembers how each concept went last time."
      />

      <div className="tabs rise" role="tablist">
        {[{ id: "all", name: "All subjects" }, ...data.subjects].map((s) => (
          <button
            key={s.id}
            role="tab"
            aria-selected={filter === s.id}
            className={`tab ${filter === s.id ? "on" : ""}`}
            onClick={() => setFilter(s.id)}
          >
            {s.name}
          </button>
        ))}
      </div>

      {subjects.map((s) => {
        const mastery =
          s.topics.reduce((sum, t) => sum + (t.progress.mastery ?? 0), 0) / Math.max(1, s.topics.length);
        return (
          <section key={s.id} className={`subject-section subj-${s.id}`}>
            <div className="subject-section-head rise">
              <div>
                <h2 className="display">{s.name}</h2>
                <p className="muted">{s.description}</p>
              </div>
              <div className="subject-section-meter">
                <span className="muted small">Subject mastery</span>
                <span className="num subject-pct">{pct(mastery)}</span>
              </div>
            </div>
            <div className="grid grid-3">
              {s.topics.map((t, i) => {
                const isActive = active && active.topic_id === t.id;
                return (
                  <article key={t.id} className="card topic-card rise" style={{ animationDelay: `${i * 60}ms` }}>
                    <div className="topic-accent" />
                    <div className="card-body">
                      <div className="topic-card-top">
                        <span className={`level-tag lv-${t.level.toLowerCase()}`}>{t.level}</span>
                        {isActive ? (
                          <span className="pill pill-live">
                            <span className="live-dot" /> In session
                          </span>
                        ) : (
                          <StatusPill status={t.progress.status} />
                        )}
                      </div>
                      <h3 className="display topic-title">{t.title}</h3>
                      <p className="muted topic-summary">{t.summary}</p>
                      <div className="chips">
                        {t.concepts.map((c) => (
                          <span key={c} className="chip">
                            {c}
                          </span>
                        ))}
                      </div>
                      <div className="topic-progress">
                        <div className="labeled-bar-top">
                          <span className="muted small">
                            {t.progress.sessions === 0
                              ? "Not attempted yet"
                              : `Mastery · ${t.progress.sessions} session${t.progress.sessions > 1 ? "s" : ""}`}
                          </span>
                          <span className="num small strong">{pct(t.progress.mastery)}</span>
                        </div>
                        <Bar value={t.progress.mastery} size="sm" delay={150 + i * 60} />
                      </div>
                    </div>
                    <div className="topic-card-foot">
                      <span className="muted small">{t.session_length} adaptive questions</span>
                      {isActive ? (
                        <button className="btn btn-primary btn-sm" onClick={() => navigate("session", active.id)}>
                          Continue <Icon name="arrowRight" size={14} />
                        </button>
                      ) : (
                        <button className="btn btn-primary btn-sm" onClick={() => startTopic(t.id)}>
                          {t.progress.sessions ? "Practice again" : "Start"} <Icon name="arrowRight" size={14} />
                        </button>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        );
      })}
    </>
  );
}
