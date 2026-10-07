export default function ProgressBar({ label, value }) {
  const pct = value == null ? 0 : Math.round(value * 100);
  return (
    <div className="progress-row">
      <div className="progress-row-top">
        <span>{label}</span>
        <span>{value == null ? "—" : `${pct}%`}</span>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
