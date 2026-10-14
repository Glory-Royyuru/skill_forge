// Small self-loading pieces that tie scheduling and identity to learning:
// the upcoming-class timeline (timetable → recommendation engine) and the
// profile's learning identity. Both read /learner/overview; nothing invented.
import { api } from "../api.js";
import { actOn } from "../lib/actions.js";
import { navigate, pct } from "../lib/router.js";
import { useLoad } from "../lib/useLoad.js";
import { Icon } from "./ui.jsx";

// "today at 14:00" → ["Today", "14:00"]; the backend phrases every slot this way.
function splitWhen(when) {
  const [day, time] = when.split(" at ");
  return [day.charAt(0).toUpperCase() + day.slice(1), time || ""];
}

function untilLabel(hours) {
  if (hours < 1) return `in ${Math.max(1, Math.round(hours * 60))} min`;
  return `in about ${Math.round(hours)} h`;
}

export function UpcomingTimeline() {
  const { data, error, loading } = useLoad(() => api.overview());
  if (loading) return <p className="timeline-loading muted small" role="status">Checking your timetable…</p>;
  if (error || !data) return null;
  const classes = data.upcoming_classes || [];
  return (
    <section className="timeline" aria-labelledby="tl-h">
      <div className="timeline-head">
        <h2 className="timeline-title display" id="tl-h">Next 48 hours</h2>
        <button className="link-btn small" onClick={() => navigate("profile", null, { tab: "timetable" })}>
          Edit timetable
        </button>
      </div>
      {classes.length === 0 ? (
        <p className="timeline-empty">
          No classes in the next two days on your timetable. Add your classes and SkillForge will suggest what to
          prepare before each one.
        </p>
      ) : (
        <ol className="tl-list">
          {classes.slice(0, 6).map((c) => {
            const [day, time] = splitWhen(c.when);
            return (
              <li key={`${c.id}-${c.starts_at}`} className="tl-row">
                <div className="tl-when">
                  <span className="tl-day">{day}</span>
                  <span className="tl-time num">{time}</span>
                  <span className="tl-until">{untilLabel(c.hours_until)}</span>
                </div>
                <div className="tl-class">
                  <span className="tl-subject display">{c.subject_name}</span>
                  {(c.room || c.faculty) && <span className="muted small">{[c.room, c.faculty].filter(Boolean).join(" · ")}</span>}
                </div>
                {c.preparation ? (
                  <div className="tl-prep">
                    <span className="tl-prep-k">Prepare · about {c.preparation.estimated_minutes} min</span>
                    <span className="tl-prep-t">{c.preparation.topic_title || c.preparation.title}</span>
                    <span className="tl-prep-why">{c.preparation.reason}</span>
                    <button className="btn btn-primary btn-sm" onClick={() => actOn(c.preparation)}>
                      Prepare <span className="sr-only">for {c.subject_name}</span> <Icon name="arrowRight" size={13} />
                    </button>
                  </div>
                ) : (
                  <p className="tl-prep tl-none">{c.note}</p>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

export function LearningIdentity() {
  const { data: o } = useLoad(() => api.overview());
  if (!o) return null;
  const ov = o.overall;
  const C = 2 * Math.PI * 42;
  const est = ov.assessed ? ov.estimate : 0;
  const focus = o.next_up;
  return (
    <section className="identity rise" aria-label="Your learning identity">
      <div className="identity-ring" aria-hidden="true">
        <svg viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="42" className="id-track" />
          <circle cx="50" cy="50" r="42" className="id-fill" strokeDasharray={C} strokeDashoffset={C * (1 - est)}
            transform="rotate(-90 50 50)" />
          <circle cx="50" cy="50" r="42" className="id-cov" strokeDasharray={`${C * ov.coverage} ${C}`}
            transform="rotate(-90 50 50)" />
        </svg>
        <span className="identity-pct display num">{ov.assessed ? pct(ov.estimate) : "—"}</span>
      </div>
      <dl className="identity-facts">
        <div><dt>Estimated mastery</dt><dd>{ov.assessed ? `${pct(ov.estimate)} over ${ov.assessed} of ${ov.total} concepts` : "No graded answers yet"}</dd></div>
        <div><dt>Activity</dt><dd>Level {o.activity_level.level} · {o.activity_level.xp} XP</dd></div>
        <div><dt>Sessions completed</dt><dd>{o.sessions_completed}</dd></div>
        <div>
          <dt>Current focus</dt>
          <dd>
            {focus ? (
              <button className="link-btn" onClick={() => actOn(focus)}>{focus.title}</button>
            ) : "Nothing recommended yet"}
          </dd>
        </div>
      </dl>
    </section>
  );
}
