export default function Timeline({ steps }) {
  if (!steps.length) {
    return <p className="muted">No actions taken yet.</p>;
  }
  return (
    <ol className="timeline">
      {steps.map((s, i) => (
        <li key={i} className={s.ok ? "ok" : "err"}>
          <span className="timeline-icon">{s.ok ? "✓" : "✕"}</span>
          <span className="timeline-label">{s.label}</span>
        </li>
      ))}
    </ol>
  );
}
