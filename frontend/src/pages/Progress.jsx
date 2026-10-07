import { useEffect, useState } from "react";
import { api } from "../api.js";
import Header from "../components/Header.jsx";
import MetricCard from "../components/MetricCard.jsx";
import ProgressBar from "../components/ProgressBar.jsx";

export default function ProgressPage({ onMenuClick }) {
  const [progress, setProgress] = useState(null);

  useEffect(() => {
    api.progress().then(setProgress);
  }, []);

  if (!progress) {
    return (
      <div className="page">
        <Header title="Progress" subtitle="Your learning analytics." onMenuClick={onMenuClick} />
        <p className="muted">Loading…</p>
      </div>
    );
  }

  return (
    <div className="page">
      <Header title="Progress" subtitle="Your learning analytics, built from your own attempt history." onMenuClick={onMenuClick} />

      <div className="card">
        <div className="metric-grid">
          <MetricCard label="Overall accuracy" value={progress.accuracy != null ? `${Math.round(progress.accuracy * 100)}%` : "—"} />
          <MetricCard label="Average score" value={progress.average_score != null ? `${Math.round(progress.average_score * 100)}` : "—"} />
          <MetricCard label="Cases completed" value={progress.cases_completed} />
          <MetricCard label="Average steps" value={progress.average_steps?.toFixed(1) ?? "—"} />
          <MetricCard label="Critical errors" value={progress.critical_errors} />
          <MetricCard label="Best streak" value={progress.best_streak} />
        </div>
      </div>

      <div className="card">
        <h2>Skill development</h2>
        {Object.entries(progress.skills).map(([name, value]) => (
          <ProgressBar key={name} label={name} value={value} />
        ))}
      </div>

      <div className="card">
        <h2>Areas to improve</h2>
        {progress.areas_to_improve.length === 0 ? (
          <p className="muted">No specific weak areas identified yet — keep practicing.</p>
        ) : (
          <ul className="check-list">
            {progress.areas_to_improve.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
