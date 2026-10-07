import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import Header from "../components/Header.jsx";
import DifficultyBadge, { StatusBadge } from "../components/DifficultyBadge.jsx";

const FILTERS = ["All", "Beginner", "Intermediate", "Advanced", "Completed", "Needs Review"];

export default function Cases({ onMenuClick }) {
  const [cases, setCases] = useState(null);
  const [filter, setFilter] = useState("All");

  useEffect(() => {
    api.cases(50).then(setCases);
  }, []);

  const filtered = useMemo(() => {
    if (!cases) return [];
    if (filter === "All") return cases;
    if (filter === "Completed") return cases.filter((c) => c.status === "Resolved");
    if (filter === "Needs Review") return cases.filter((c) => c.status === "Needs review");
    return cases.filter((c) => c.difficulty === filter);
  }, [cases, filter]);

  return (
    <div className="page">
      <Header title="Cases" subtitle="Browse the case library." onMenuClick={onMenuClick} />

      <div className="card">
        <div className="filter-row">
          {FILTERS.map((f) => (
            <button key={f} className={`filter-chip ${filter === f ? "active" : ""}`} onClick={() => setFilter(f)}>
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        {!cases ? (
          <p className="muted">Loading cases…</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Case ID</th>
                <th>Difficulty</th>
                <th>Tags</th>
                <th>Status</th>
                <th>Score</th>
                <th>Last attempt</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.case_id}>
                  <td>#{c.case_id}</td>
                  <td>
                    <DifficultyBadge level={c.difficulty} />
                  </td>
                  <td className="tags-cell">{c.tags.join(", ") || "—"}</td>
                  <td>
                    <StatusBadge status={c.status} />
                  </td>
                  <td>{c.score != null ? `${c.score}%` : "—"}</td>
                  <td>{c.last_attempt ? new Date(c.last_attempt).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
