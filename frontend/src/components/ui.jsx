import { useEffect, useRef, useState } from "react";
import { STATUS_LABELS, pct } from "../lib/router.js";

const ICON_PATHS = {
  home: "M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z",
  book: "M4 4.5A1.5 1.5 0 0 1 5.5 3H20v15H5.5A1.5 1.5 0 0 0 4 19.5zM4 19.5A1.5 1.5 0 0 0 5.5 21H20v-3",
  teacher: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-7 9a7 7 0 0 1 14 0",
  report: "M7 3h7l5 5v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zm7 0v5h5M9 13h6M9 17h6",
  chart: "M4 20V10m6 10V4m6 16v-7m4 7H3",
  info: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zm0-5v-4m0-4h.01",
  arrowRight: "M5 12h14m-6-6 6 6-6 6",
  arrowUp: "M12 19V5m-6 6 6-6 6 6",
  arrowDown: "M12 5v14m6-6-6 6-6-6",
  check: "M5 12.5 10 17l9-10",
  x: "M6 6l12 12M18 6 6 18",
  refresh: "M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7",
  flag: "M5 21V4m0 0h11l-2 4 2 4H5",
  menu: "M4 6h16M4 12h16M4 18h16",
  target: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zm0-4a5 5 0 1 0 0-10 5 5 0 0 0 0 10zm0-4a1 1 0 1 0 0-2 1 1 0 0 0 0 2z",
  layers: "M12 3 2 8l10 5 10-5zM2 13l10 5 10-5M2 17.5l10 5 10-5",
  pulse: "M3 12h4l3-8 4 16 3-8h4",
};

export function Icon({ name, size = 18, className = "" }) {
  return (
    <svg
      className={`icon ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={ICON_PATHS[name]} />
    </svg>
  );
}

const reducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// Animate a number toward `target` (eased), for mastery counters and rings.
export function useCountUp(target, duration = 900) {
  const [value, setValue] = useState(reducedMotion() ? target ?? 0 : 0);
  const from = useRef(0);
  useEffect(() => {
    if (target == null) return undefined;
    if (reducedMotion()) {
      setValue(target);
      return undefined;
    }
    const start = performance.now();
    const begin = from.current;
    let raf;
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const v = begin + (target - begin) * eased;
      setValue(v);
      from.current = v;
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);
  return value;
}

export function PageHeader({ eyebrow, title, subtitle, actions }) {
  return (
    <header className="page-header rise">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1 className="display">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

export function Card({ title, action, children, className = "", padded = true, style }) {
  return (
    <section className={`card ${className}`} style={style}>
      {(title || action) && (
        <div className="card-head">
          {title && <h2 className="card-title">{title}</h2>}
          {action}
        </div>
      )}
      <div className={padded ? "card-body" : "card-flush"}>{children}</div>
    </section>
  );
}

export function Metric({ label, value, sub, delay = 0 }) {
  return (
    <div className="metric rise" style={{ animationDelay: `${delay}ms` }}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value ?? "—"}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}

export function Bar({ value, tone = "accent", size = "md", delay = 0 }) {
  const width = value == null ? 0 : Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div className={`bar bar-${size}`}>
      <div className={`bar-fill tone-${tone}`} style={{ width: `${width}%`, animationDelay: `${delay}ms` }} />
    </div>
  );
}

export function StatusPill({ status, label }) {
  return <span className={`pill pill-${status}`}>{label || STATUS_LABELS[status] || status}</span>;
}

export function MasteryRing({ value, size = 112, stroke = 9, label = "Mastery" }) {
  const animated = useCountUp(value ?? 0, 1100);
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const v = Math.max(0, Math.min(1, animated));
  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} className="ring-track" strokeWidth={stroke} fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          className="ring-fill"
          strokeWidth={stroke}
          fill="none"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - v)}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <div className="ring-center">
        <div className="ring-value num">{value == null ? "—" : `${Math.round(v * 100)}%`}</div>
        <div className="ring-label">{label}</div>
      </div>
    </div>
  );
}

const LEVELS = ["Foundational", "Intermediate", "Advanced"];

export function LevelMeter({ level }) {
  return (
    <div className="level-meter">
      <div className="level-steps">
        {LEVELS.map((name, i) => (
          <div key={name} className={`level-step ${i < level ? "on" : ""}`} />
        ))}
      </div>
      <div className="level-name" key={level}>
        {LEVELS[level - 1]}
      </div>
    </div>
  );
}

export function Loading({ label = "Loading…" }) {
  return (
    <div className="state-msg">
      <span className="loader" />
      {label}
    </div>
  );
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="card error-card">
      <div className="card-body">
        <h2 className="card-title">Something went wrong</h2>
        <p className="muted">{String(error?.message || error)}</p>
        <p className="muted small">
          Start the backend with <code>uvicorn skillforge.api.app:app --port 8000</code> from the{" "}
          <code>backend</code> folder.
        </p>
        {onRetry && (
          <button className="btn btn-secondary" onClick={onRetry}>
            Try again
          </button>
        )}
      </div>
    </div>
  );
}

export { pct };
