import { useRef, useState } from "react";
import { pct } from "../lib/router.js";

// The dashboard's focal visual: the curriculum drawn as a small knowledge
// graph. Every node is a real topic and its ring is the student's real
// latest mastery; nodes drift gently and the layers parallax with the
// pointer. Clicking a node starts that topic.

const W = 560;
const H = 380;
const ANCHORS = {
  ml: { x: 140, y: 135 },
  python: { x: 425, y: 125 },
  dsa: { x: 282, y: 262 },
};
const SHORT = { ml: "ML", python: "Python", dsa: "DSA" };
const ANGLES = [-150, -30, 90];

function layout(subjects) {
  const nodes = [];
  subjects.forEach((s) => {
    const a = ANCHORS[s.id] || { x: W / 2, y: H / 2 };
    s.topics.forEach((t, i) => {
      const ang = ((ANGLES[i % 3] + (s.id === "dsa" ? 180 : 0)) * Math.PI) / 180;
      nodes.push({ ...t, subject: s.id, x: a.x + Math.cos(ang) * 92, y: a.y + Math.sin(ang) * 78 });
    });
  });
  return nodes;
}

export default function KnowledgeMap({ subjects, onSelect }) {
  const ref = useRef(null);
  const [hover, setHover] = useState(null);
  const nodes = layout(subjects);

  const onMove = (e) => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty("--px", ((e.clientX - r.left) / r.width - 0.5).toFixed(3));
    el.style.setProperty("--py", ((e.clientY - r.top) / r.height - 0.5).toFixed(3));
  };
  const onLeave = () => {
    ref.current?.style.setProperty("--px", 0);
    ref.current?.style.setProperty("--py", 0);
    setHover(null);
  };

  const hovered = nodes.find((n) => n.id === hover);

  return (
    <div className="kmap" ref={ref} onPointerMove={onMove} onPointerLeave={onLeave}>
      <div className="kmap-grid" />
      <svg viewBox={`0 0 ${W} ${H}`} className="kmap-svg" role="img" aria-label="Curriculum knowledge map">
        <g className="kmap-layer kmap-back">
          {Object.entries(ANCHORS).map(([a, p], i, arr) => {
            const [, q] = arr[(i + 1) % arr.length];
            return <line key={a} x1={p.x} y1={p.y} x2={q.x} y2={q.y} className="kmap-bridge" />;
          })}
          {nodes.map((n) => {
            const a = ANCHORS[n.subject];
            return <line key={n.id} x1={a.x} y1={a.y} x2={n.x} y2={n.y} className="kmap-edge" />;
          })}
        </g>
        <g className="kmap-layer kmap-mid">
          {subjects.map((s) => {
            const a = ANCHORS[s.id];
            return (
              <g key={s.id}>
                <circle cx={a.x} cy={a.y} r="25" className="kmap-hub-halo" />
                <circle cx={a.x} cy={a.y} r="21" className="kmap-hub" />
                <text x={a.x} y={a.y + 4} className="kmap-subject" textAnchor="middle">
                  {SHORT[s.id] || s.name}
                </text>
              </g>
            );
          })}
        </g>
        <g className="kmap-layer kmap-front">
          {nodes.map((n, i) => {
            const r = 20;
            const c = 2 * Math.PI * (r + 5);
            const m = n.mastery ?? 0;
            return (
              <g
                key={n.id}
                className={`kmap-node st-${n.status} ${hover === n.id ? "is-hover" : ""}`}
                style={{ animationDelay: `${(i % 5) * -1.3}s`, transformOrigin: `${n.x}px ${n.y}px` }}
                onPointerEnter={() => setHover(n.id)}
                onClick={() => onSelect?.(n.id)}
                tabIndex={0}
                role="button"
                aria-label={`${n.title}: ${n.mastery == null ? "not started" : pct(n.mastery)}`}
                onKeyDown={(e) => e.key === "Enter" && onSelect?.(n.id)}
              >
                <circle cx={n.x} cy={n.y} r={r + 5} className="kmap-track" />
                {n.mastery != null && (
                  <circle
                    cx={n.x}
                    cy={n.y}
                    r={r + 5}
                    className="kmap-arc"
                    strokeDasharray={c}
                    strokeDashoffset={c * (1 - m)}
                    transform={`rotate(-90 ${n.x} ${n.y})`}
                  />
                )}
                <circle cx={n.x} cy={n.y} r={r} className="kmap-dot" />
                <text x={n.x} y={n.y + 4} className="kmap-pct" textAnchor="middle">
                  {n.mastery == null ? "·" : Math.round(m * 100)}
                </text>
                <text x={n.x} y={n.y + r + 20} className="kmap-label" textAnchor="middle">
                  {n.title.replace("Object-Oriented Programming", "OOP")}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
      <div className={`kmap-tip ${hovered ? "show" : ""}`}>
        {hovered && (
          <>
            <strong>{hovered.title}</strong>
            <span>
              {hovered.mastery == null ? "Not started" : `${pct(hovered.mastery)} mastery`} · click to start
            </span>
          </>
        )}
      </div>
      <div className="kmap-legend">
        <span>
          <i className="lg lg-mastered" /> Mastered
        </span>
        <span>
          <i className="lg lg-in_progress" /> In progress
        </span>
        <span>
          <i className="lg lg-not_started" /> Not started
        </span>
      </div>
    </div>
  );
}
