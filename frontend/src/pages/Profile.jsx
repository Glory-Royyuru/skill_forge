import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Card, ErrorState, Loading, PageHeader } from "../components/ui.jsx";
import { SEASONS, getThemePreference, seasonFor, setThemePreference, subscribeTheme } from "../lib/theme.js";
import { navigate } from "../lib/router.js";
import { useLoad } from "../lib/useLoad.js";
import Timetable from "./Timetable.jsx";
import { LearningIdentity } from "../components/journey.jsx";

const TABS = [
  { id: "account", label: "Account" },
  { id: "settings", label: "Settings" },
  { id: "timetable", label: "Timetable" },
];

function Choice({ name, value, current, title, detail, onPick }) {
  return (
    <label className={`choice ${current === value ? "on" : ""}`}>
      <input type="radio" name={name} value={value} checked={current === value} onChange={() => onPick(value)} />
      <span>
        <span className="choice-title">{title}</span>
        {detail && <span className="choice-detail muted small">{detail}</span>}
      </span>
    </label>
  );
}

// Light, dark or follow the system. Stored in this browser (like the toggle in
// the top bar), so it applies before sign-in too.
function Appearance() {
  const [mode, setMode] = useState(getThemePreference());
  useEffect(() => subscribeTheme(({ preference }) => setMode(preference)), []);
  return (
    <Card title="Appearance">
      <div className="choices" role="radiogroup" aria-label="Colour theme">
        <Choice name="appearance" value="light" current={mode} onPick={setThemePreference} title="Light" detail="Ivory pages, ink text." />
        <Choice name="appearance" value="dark" current={mode} onPick={setThemePreference} title="Dark" detail="Deep ocean pages, light text." />
        <Choice name="appearance" value="auto" current={mode} onPick={setThemePreference} title="System" detail="Follows your device setting and changes with it." />
      </div>
      <p className="muted small">Saved in this browser. The button in the top bar changes the same setting.</p>
    </Card>
  );
}

function Settings({ prefs, onSaved }) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const save = async (patch) => {
    setSaving(true);
    setError(null);
    try {
      const r = await api.updatePreferences(patch);
      onSaved(r.preferences);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };
  const auto = seasonFor();
  return (
    <div className="grid grid-2">
      <Appearance />
      <Card title="Mode">
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        <div className="choices" role="radiogroup" aria-label="Mode" aria-busy={saving}>
          <Choice name="mode" value="student" current={prefs.mode} onPick={(mode) => save({ mode })}
            title="Student mode" detail="Your day-to-day learning views." />
          <Choice name="mode" value="ptm" current={prefs.mode} onPick={(mode) => save({ mode })}
            title="PTM mode" detail="Progress becomes the Student Performance Review: a teacher-style report of your own record for a parent–teacher meeting. It is a view of your account, not a separate login; nobody else can access your data." />
        </div>
        <button className="btn btn-secondary btn-sm" onClick={() => navigate("review")}>
          Open the Student Performance Review
        </button>
      </Card>
      <Card title="Seasonal decoration">
        <div className="choices" role="radiogroup" aria-label="Seasonal decoration">
          <Choice name="theme" value="auto" current={prefs.theme} onPick={(theme) => save({ theme })}
            title="Automatic" detail={auto ? `Currently: ${SEASONS[auto].label}` : "No seasonal decoration right now"} />
          <Choice name="theme" value="none" current={prefs.theme} onPick={(theme) => save({ theme })} title="Off" />
          {Object.entries(SEASONS).map(([k, v]) => (
            <Choice key={k} name="theme" value={k} current={prefs.theme} onPick={(theme) => save({ theme })} title={v.label} />
          ))}
        </div>
        <p className="muted small">Seasonal decorations are subtle, stay at the edges of the page and stop moving if your device asks for reduced motion.</p>
      </Card>
    </div>
  );
}

export default function Profile({ user, query, onPrefs }) {
  const tab = TABS.some((t) => t.id === query?.tab) ? query.tab : "account";
  const { data, error, loading, reload } = useLoad(() => api.profile());
  const [prefs, setPrefs] = useState(null);
  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const current = prefs || data.preferences;
  const saved = (p) => {
    setPrefs(p);
    onPrefs?.(p);
  };
  return (
    <>
      <PageHeader eyebrow="Profile" title={user.name} subtitle={user.student_id ? `Registration ID ${user.student_id}` : user.email} />
      <LearningIdentity />
      <div className="tabs rise" role="tablist">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} className={`tab ${tab === t.id ? "on" : ""}`}
            onClick={() => navigate("profile", null, { tab: t.id })}>{t.label}</button>
        ))}
      </div>
      <div key={tab} className="rise">
        {tab === "account" && (
          <Card title="Account">
            <dl className="acct-facts">
              <div><dt>Name</dt><dd>{user.name}</dd></div>
              <div><dt>Email</dt><dd>{user.email}</dd></div>
              <div><dt>Registration ID</dt><dd>{user.student_id || <span className="muted">Not set</span>}</dd></div>
              <div><dt>Mode</dt><dd>{current.mode === "ptm" ? "PTM" : "Student"}</dd></div>
            </dl>
            <p className="muted small">
              Your learning record is private to this account. To change your password, sign out and use “Forgot
              password?” on the sign-in page; a reset signs this account out on every device.
            </p>
          </Card>
        )}
        {tab === "settings" && <Settings prefs={current} onSaved={saved} />}
        {tab === "timetable" && <Timetable embedded />}
      </div>
    </>
  );
}
