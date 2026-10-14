import { useRef, useState } from "react";
import { pct } from "../lib/router.js";

// The dashboard's focal visual: the student's subjects drawn as an interactive
// knowledge constellation. Each node's arc represents real calibrated mastery.
// Clicking a node explores that subject in the curriculum.

const W = 580;
const H = 400;
const CX = W / 2;
const CY = H / 2 + 4;
const RX = 210;
const RY = 140;

function layout(subjects) {
  if (!subjects?.length) return [];
  return subjects.map((s, i) => {
    const ang = ((-90 + (360 / subjects.length) * i) * Math.PI) / 180;
    return { ...s, x: CX + Math.cos(ang) * RX, y: CY + Math.sin(ang) * RY };
  });
}

function status(s) {
  if (!s.topics_started) return "not_started";
  return s.mastery >= 0.8 ? "mastered" : "in_progress";
}

export default function KnowledgeMap({ subjects = [], onSelect }) {
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
    ref.current?.style.setProperty("--px", "0");
    ref.current?.style.setProperty("--py", "0");
    setHover(null);
  };

  const hovered = nodes.find((n) => n.id === hover);

  return (
    <div className="kmap" ref={ref} onPointerMove={onMove} onPointerLeave={onLeave}>
      <div className="kmap-grid" />
      <svg viewBox={`0 0 ${W} ${H}`} className="kmap-svg" role="img" aria-label="Your subjects and your mastery constellation">
        <defs>
          <linearGradient id="hubGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--navy)" />
            <stop offset="100%" stopColor="var(--blue)" />
          </linearGradient>
          <linearGradient id="masteryGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--green)" />
            <stop offset="100%" stopColor="#2ecc71" />
          </linearGradient>
          <linearGradient id="progressGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--navy)" />
            <stop offset="100%" stopColor="var(--blue)" />
          </linearGradient>
          <radialGradient id="hubGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--blue)" stopOpacity="0.3" />
            <stop offset="100%" stopColor="var(--blue)" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Back Layer: Orbits & Connecting Constellation Beams */}
        <g className="kmap-layer kmap-back">
          <ellipse cx={CX} cy={CY} rx={RX} ry={RY} className="kmap-orbit" />
          {nodes.map((n) => (
            <line
              key={n.id}
              x1={CX}
              y1={CY}
              x2={n.x}
              y2={n.y}
              className={`kmap-edge ${hover === n.id ? "kmap-edge-active" : ""}`}
              strokeDasharray={hover === n.id ? "4 4" : "none"}
            />
          ))}
        </g>

        {/* Mid Layer: Central Knowledge Core Hub */}
        <g className="kmap-layer kmap-mid">
          <circle cx={CX} cy={CY} r="46" fill="url(#hubGlow)" />
          <circle cx={CX} cy={CY} r="34" className="kmap-hub-halo" />
          <circle cx={CX} cy={CY} r="28" fill="url(#hubGrad)" filter="drop-shadow(0 4px 8px rgba(0,0,0,0.2))" />
          <text x={CX} y={CY - 2} className="kmap-subject" textAnchor="middle">
            Your
          </text>
          <text x={CX} y={CY + 11} className="kmap-hub-sub" textAnchor="middle">
            LANDSCAPE
          </text>
        </g>

        {/* Front Layer: Orbiting Subject Knowledge Nodes */}
        <g className="kmap-layer kmap-front">
          {nodes.map((n, i) => {
            const r = 22;
            const c = 2 * Math.PI * (r + 5);
            const isHovered = hover === n.id;
            const st = status(n);
            const arcGrad = st === "mastered" ? "url(#masteryGrad)" : "url(#progressGrad)";

            return (
              <g
                key={n.id}
                className={`kmap-node st-${st} ${isHovered ? "is-hover" : ""}`}
                style={{
                  animationDelay: `${(i % 5) * -1.2}s`,
                  transformOrigin: `${n.x}px ${n.y}px`,
                }}
                onPointerEnter={() => setHover(n.id)}
                onClick={() => onSelect?.(n.id)}
                tabIndex={0}
                role="button"
                aria-label={`${n.name}: ${n.topics_started ? pct(n.mastery) : "not started"}`}
                onKeyDown={(e) => e.key === "Enter" && onSelect?.(n.id)}
              >
                {/* Outer Glow Halo on hover */}
                {isHovered && <circle cx={n.x} cy={n.y} r={r + 12} fill="var(--blue-soft)" opacity="0.6" />}

                {/* Progress track */}
                <circle cx={n.x} cy={n.y} r={r + 5} className="kmap-track" />

                {/* Calibrated Mastery Progress Arc */}
                {n.topics_started > 0 && (
                  <circle
                    cx={n.x}
                    cy={n.y}
                    r={r + 5}
                    className="kmap-arc"
                    stroke={arcGrad}
                    strokeDasharray={c}
                    strokeDashoffset={c * (1 - n.mastery)}
                    transform={`rotate(-90 ${n.x} ${n.y})`}
                  />
                )}

                {/* Node Center Dot */}
                <circle cx={n.x} cy={n.y} r={r} className="kmap-dot" />

                {/* Percentage / Status Indicator */}
                <text x={n.x} y={n.y + 4} className="kmap-pct" textAnchor="middle">
                  {n.topics_started ? Math.round(n.mastery * 100) : "·"}
                </text>

                {/* Subject Short Name Label */}
                <text x={n.x} y={n.y + r + 18} className="kmap-label" textAnchor="middle">
                  {n.short_name || n.name}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Interactive Tooltip Card */}
      <div className={`kmap-tip ${hovered ? "show" : ""}`}>
        {hovered && (
          <>
            <strong>{hovered.name}</strong>
            <span>
              {hovered.topics_started
                ? `${pct(hovered.mastery)} estimated · ${hovered.topics_started} of ${hovered.topics_total} concepts assessed`
                : "Not started yet"}{" "}
              · click to open in curriculum
            </span>
          </>
        )}
      </div>

      {/* Legend */}
      <div className="kmap-legend">
        <span>
          <i className="lg lg-mastered" /> Mastered (80%+)
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
