export default function DifficultyBadge({ level }) {
  const cls = (level || "").toLowerCase();
  return <span className={`badge badge-${cls}`}>{level}</span>;
}

export function StatusBadge({ status }) {
  const cls = status === "Resolved" ? "ok" : status === "Needs review" ? "warn" : "neutral";
  return <span className={`status-badge status-${cls}`}>{status}</span>;
}
