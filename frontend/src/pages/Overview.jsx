import { useEffect, useState } from "react";
import { api } from "../api.js";
import Header from "../components/Header.jsx";
import MetricCard from "../components/MetricCard.jsx";
import ProgressBar from "../components/ProgressBar.jsx";
import { StatusBadge } from "../components/DifficultyBadge.jsx";

export default function Overview({ onMenuClick, onNavigate }) {
  const [progress, setProgress] = useState(null);

  useEffect(() => {
    api.progress().then(setProgress);
  }, []);

  const riskAwareness =
    progress && progress.cases_completed > 0 ? 1 - progress.critical_errors / progress.cases_completed : null;

  return (
    <div className="page">
      <Header
        title="Customer Support Training"
        subtitle="Build decision-making and tool-use skills through realistic refund cases."
        onMenuClick={onMenuClick}
        right={
          <button className="primary-button" onClick={() => onNavigate("practice")}>
            Continue Practice
          </button>
        }
      />

      <div className="card">
        <h2>Training progress</h2>
        <div className="metric-grid">
          <MetricCard label="Cases completed" value={progress?.cases_completed ?? 0} />
          <MetricCard
            label="Accuracy"
            value={progress?.accuracy != null ? `${Math.round(progress.accuracy * 100)}%` : "—"}
          />
          <MetricCard label="Current streak" value={progress?.current_streak ?? 0} />
          <MetricCard label="Level" value={progress?.level ?? "Beginner"} />
        </div>
      </div>

      <div className="card">
        <h2>Skill areas</h2>
        <ProgressBar label="Policy interpretation" value={progress?.skills?.["Policy Understanding"]} />
        <ProgressBar label="Evidence gathering" value={progress?.skills?.["Evidence Gathering"]} />
        <ProgressBar label="Tool selection" value={progress?.skills?.["Tool Selection"]} />
        <ProgressBar label="Decision accuracy" value={progress?.skills?.["Decision Accuracy"]} />
        <ProgressBar label="Risk awareness" value={riskAwareness} />
      </div>

      <div className="card">
        <h2>Recent activity</h2>
        {!progress || progress.recent.length === 0 ? (
          <p className="muted">No cases completed yet. Start practicing to build your history.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Case</th>
                <th>Result</th>
                <th>Score</th>
                <th>Difficulty</th>
              </tr>
            </thead>
            <tbody>
              {progress.recent.map((r) => (
                <tr key={r.case_id}>
                  <td>Case #{r.case_id}</td>
                  <td>
                    <StatusBadge status={r.result} />
                  </td>
                  <td>{r.score}%</td>
                  <td>{r.difficulty}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
