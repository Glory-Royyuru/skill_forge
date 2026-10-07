export default function MetricCard({ label, value, sub }) {
  return (
    <div className="metric-card">
      <div className="metric-value">{value ?? "—"}</div>
      <div className="metric-label">{label}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}
