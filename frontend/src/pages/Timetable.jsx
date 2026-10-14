import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Card, ErrorState, Icon, Loading, PageHeader } from "../components/ui.jsx";
import { useLoad } from "../lib/useLoad.js";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const EMPTY = { day_of_week: 0, start_time: "09:00", end_time: "09:50", subject_id: "", faculty: "", room: "" };

function EntryForm({ subjects, editing, onSaved, onCancel }) {
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setError(null);
    setForm(
      editing
        ? {
            day_of_week: editing.day_of_week,
            start_time: editing.start_time,
            end_time: editing.end_time,
            subject_id: editing.subject_id,
            faculty: editing.faculty || "",
            room: editing.room || "",
          }
        : { ...EMPTY, subject_id: subjects[0]?.id || "" }
    );
  }, [editing, subjects]);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: k === "day_of_week" ? Number(e.target.value) : e.target.value }));
  const invalidTime = form.end_time <= form.start_time;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const body = { ...form, faculty: form.faculty || null, room: form.room || null };
    try {
      if (editing) await api.updateEntry(editing.id, body);
      else await api.createEntry(body);
      onSaved();
      if (!editing) setForm((f) => ({ ...f, faculty: "", room: "" }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="form" onSubmit={submit}>
      {error && <div className="alert alert-error">{error}</div>}
      <label className="field">
        <span className="field-label">Day</span>
        <select className="input" value={form.day_of_week} onChange={set("day_of_week")}>
          {DAYS.map((d, i) => (
            <option key={d} value={i}>
              {d}
            </option>
          ))}
        </select>
      </label>
      <div className="field-pair">
        <label className="field">
          <span className="field-label">Starts</span>
          <input className="input" type="time" required value={form.start_time} onChange={set("start_time")} />
        </label>
        <label className="field">
          <span className="field-label">Ends</span>
          <input className="input" type="time" required value={form.end_time} onChange={set("end_time")} />
        </label>
      </div>
      {invalidTime && <span className="field-hint field-error">End time must be after the start time.</span>}
      <label className="field">
        <span className="field-label">Subject</span>
        <select className="input" required value={form.subject_id} onChange={set("subject_id")}>
          {subjects.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span className="field-label">Faculty</span>
        <input className="input" maxLength={120} placeholder="Optional" value={form.faculty} onChange={set("faculty")} />
      </label>
      <label className="field">
        <span className="field-label">Room</span>
        <input className="input" maxLength={60} placeholder="Optional" value={form.room} onChange={set("room")} />
      </label>
      <div className="form-actions">
        <button className="btn btn-primary" disabled={busy || invalidTime || !form.subject_id}>
          {editing ? "Save changes" : "Add class"}
        </button>
        {editing && (
          <button type="button" className="btn btn-ghost" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}

export default function Timetable({ embedded = false }) {
  const entries = useLoad(() => api.timetable());
  const topics = useLoad(() => api.topics());
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState(null);

  if (entries.loading || topics.loading) return <Loading />;
  if (entries.error || topics.error) {
    return <ErrorState error={entries.error || topics.error} onRetry={() => (entries.reload(), topics.reload())} />;
  }

  const subjects = topics.data.subjects.map((s) => ({ id: s.id, name: s.name, short: s.short_name }));
  const list = entries.data.entries;
  const days = DAYS.map((name, i) => ({ name, i, items: list.filter((e) => e.day_of_week === i) })).filter(
    (d) => d.i < 6 || d.items.length
  );

  const remove = async (entry) => {
    setError(null);
    try {
      await api.deleteEntry(entry.id);
      if (editing?.id === entry.id) setEditing(null);
      entries.reload();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <>
      {!embedded && (
        <PageHeader
          eyebrow="Timetable"
          title="Your weekly classes"
          subtitle="Add your weekly classes. Entries are private to your account."
        />
      )}
      {embedded && <p className="muted small tt-note">Your classes power preparation recommendations before each class. Entries are private to your account.</p>}
      {error && <div className="alert alert-error">{error}</div>}
      <div className="grid grid-2-1 timetable-grid">
        <Card title="Week" padded={false} className="rise">
          {list.length === 0 ? (
            <div className="card-body empty">
              <p>Your timetable is empty.</p>
              <p className="muted small">Add each class with the form; it will appear here, ordered by day and time.</p>
            </div>
          ) : (
            <div className="week">
              {days.map((d) => (
                <div key={d.name} className="week-day">
                  <div className="week-day-name">{d.name}</div>
                  {d.items.length === 0 ? (
                    <div className="week-free muted small">No classes</div>
                  ) : (
                    <ul className="slots">
                      {d.items.map((e) => (
                        <li key={e.id} className={`slot ${editing?.id === e.id ? "is-editing" : ""}`}>
                          <span className="slot-time num">
                            {e.start_time}–{e.end_time}
                          </span>
                          <span className="slot-body">
                            <span className="slot-subject">{e.subject_name}</span>
                            <span className="muted small">{[e.faculty, e.room].filter(Boolean).join(" · ")}</span>
                          </span>
                          <span className="slot-actions">
                            <button className="icon-btn" aria-label={`Edit ${e.subject_name} on ${e.day_name}`} onClick={() => setEditing(e)}>
                              <Icon name="edit" size={15} />
                            </button>
                            <button className="icon-btn" aria-label={`Delete ${e.subject_name} on ${e.day_name}`} onClick={() => remove(e)}>
                              <Icon name="x" size={15} />
                            </button>
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
        <Card title={editing ? "Edit class" : "Add a class"} className="rise" style={{ animationDelay: "80ms" }}>
          <EntryForm
            subjects={subjects}
            editing={editing}
            onSaved={() => {
              setEditing(null);
              entries.reload();
            }}
            onCancel={() => setEditing(null)}
          />
        </Card>
      </div>
    </>
  );
}
