import { useState } from "react";
import { api } from "../api.js";
import { Card, ErrorState, Icon, Loading, PageHeader } from "../components/ui.jsx";
import { navigate, pct } from "../lib/router.js";
import { useLoad } from "../lib/useLoad.js";
import { UpcomingTimeline } from "../components/journey.jsx";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function iso(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function monthGrid(year, month) {
  const first = new Date(year, month, 1);
  const lead = (first.getDay() + 6) % 7; // Monday-first
  const days = new Date(year, month + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < lead; i++) cells.push(null);
  for (let d = 1; d <= days; d++) cells.push(new Date(year, month, d));
  while (cells.length % 7) cells.push(null);
  return cells;
}

// Longest run of consecutive active days within the loaded month.
function longestRun(days) {
  const active = new Set(days.map((d) => d.date));
  let best = 0;
  let run = 0;
  const sorted = [...active].sort();
  sorted.forEach((d, i) => {
    const prev = i && new Date(`${sorted[i - 1]}T00:00:00`);
    const cur = new Date(`${d}T00:00:00`);
    run = prev && Math.round((cur - prev) / 86400000) === 1 ? run + 1 : 1;
    best = Math.max(best, run);
  });
  return best;
}

function intensity(day) {
  if (!day) return 0;
  const n = day.graded_answers + day.flashcards;
  return n >= 20 ? 4 : n >= 10 ? 3 : n >= 4 ? 2 : 1;
}

export default function Calendar() {
  const today = new Date();
  const [cursor, setCursor] = useState({ y: today.getFullYear(), m: today.getMonth() });
  const [selected, setSelected] = useState(iso(today));
  const start = iso(new Date(cursor.y, cursor.m, 1));
  const end = iso(new Date(cursor.y, cursor.m + 1, 0));
  const { data, error, loading, reload } = useLoad(() => api.activity(start, end), [start, end]);

  const shift = (delta) => {
    const d = new Date(cursor.y, cursor.m + delta, 1);
    setCursor({ y: d.getFullYear(), m: d.getMonth() });
  };

  if (error) return <ErrorState error={error} onRetry={reload} />;
  const byDate = Object.fromEntries((data?.days || []).map((d) => [d.date, d]));
  const day = byDate[selected];
  const selDate = new Date(`${selected}T00:00:00`);
  const weekday = (selDate.getDay() + 6) % 7;
  const classes = (data?.timetable || []).filter((c) => c.day_of_week === weekday)
    .sort((a, b) => a.start_time.localeCompare(b.start_time));
  const monthName = new Date(cursor.y, cursor.m, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });

  return (
    <>
      <PageHeader eyebrow="Calendar" title="What is coming up, and what you did"
        subtitle="Your next classes with what to prepare, then a month of real activity from your account: sessions, graded answers, flashcards and Rapid Rounds." />
      <UpcomingTimeline />
      <div className="grid grid-2-1 cal-grid">
        <Card padded={false} className="rise">
          <div className="cal-head">
            <button className="icon-btn" onClick={() => shift(-1)} aria-label="Previous month"><Icon name="arrowRight" size={16} className="flip" /></button>
            <h2 className="display cal-title">{monthName}</h2>
            <button className="icon-btn" onClick={() => shift(1)} aria-label="Next month"><Icon name="arrowRight" size={16} /></button>
          </div>
          {loading ? <Loading /> : (
            <>
              <div className="cal">
                {WEEKDAYS.map((w) => <div key={w} className="cal-wd">{w}</div>)}
                {monthGrid(cursor.y, cursor.m).map((d, i) => {
                  if (!d) return <div key={i} className="cal-cell empty-cell" />;
                  const key = iso(d);
                  const a = byDate[key];
                  return (
                    <button key={key} className={`cal-cell lvl-${intensity(a)} ${key === selected ? "sel" : ""} ${key === iso(today) ? "today" : ""}`}
                      onClick={() => setSelected(key)} aria-pressed={key === selected} aria-current={key === iso(today) ? "date" : undefined}
                      aria-label={`${d.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}${a ? `: ${a.graded_answers} graded answers` : ": no activity"}`}>
                      <span className="cal-day">{d.getDate()}</span>
                      {a && <span className="cal-dot" />}
                    </button>
                  );
                })}
              </div>
              <div className="cal-foot">
                {data.active_days ? (
                  <>
                    <span><strong className="num">{data.active_days}</strong> active day{data.active_days === 1 ? "" : "s"}</span>
                    <span><strong className="num">{longestRun(data.days)}</strong> longest streak</span>
                    <span><strong className="num">{data.graded_answers}</strong> graded answers</span>
                  </>
                ) : (
                  <span className="muted">No learning activity recorded this month.</span>
                )}
                <span className="cal-legend" aria-hidden="true">
                  Less {[0, 1, 2, 3, 4].map((l) => <i key={l} className={`lvl-${l}`} />)} More
                </span>
              </div>
            </>
          )}
        </Card>

        <div className="stack">
          <Card key={selected} title={selDate.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })} className="day-detail">
            {day ? (
              <ul className="cal-detail">
                <li><span>Teacher sessions completed</span><strong className="num">{day.sessions_completed}</strong></li>
                <li><span>Graded answers</span><strong className="num">{day.graded_answers} <span className="muted small">({pct(day.graded_answers ? day.correct / day.graded_answers : null)} correct)</span></strong></li>
                {day.by_source.diagnostic > 0 && <li><span>Diagnostic answers</span><strong className="num">{day.by_source.diagnostic}</strong></li>}
                <li><span>Rapid Rounds</span><strong className="num">{day.rapid_rounds}</strong></li>
                <li><span>Flashcards reviewed</span><strong className="num">{day.flashcards}</strong></li>
                <li><span>Concepts practised</span><strong className="num">{day.concepts_practised}</strong></li>
                <li><span>Concepts improved</span><strong className="num">{day.concepts_improved}</strong></li>
                <li><span>Active time <span className="muted small">(estimated)</span></span><strong className="num">{day.active_minutes} min</strong></li>
              </ul>
            ) : (
              <p className="muted">No learning activity on this day.</p>
            )}
            {day?.topics.length > 0 && (
              <>
                <h3 className="cal-topics-h">Topics studied</h3>
                <ul className="cal-topic-list">
                  {day.topics.map((t) => <li key={t}>{t}</li>)}
                </ul>
              </>
            )}
          </Card>
          <Card title={`Classes on ${DAY_NAMES[weekday]}s`} className="rise" style={{ animationDelay: "60ms" }}
            action={<button className="link-btn" onClick={() => navigate("profile", null, { tab: "timetable" })}>Edit timetable</button>}>
            {classes.length ? (
              <ul className="slots">
                {classes.map((c) => (
                  <li key={c.id} className="slot">
                    <span className="slot-time num">{c.start_time}–{c.end_time}</span>
                    <span className="slot-body"><span className="slot-subject">{c.subject_name}</span><span className="muted small">{[c.faculty, c.room].filter(Boolean).join(" · ")}</span></span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted small">No classes in your timetable on this weekday.</p>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
