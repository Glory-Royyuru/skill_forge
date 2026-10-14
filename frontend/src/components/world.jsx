// The SkillForge "knowledge world": one small scene system reused by every
// page. Learning is a landscape — areas are territories, subjects are places,
// connections are paths, recommendations are routes.
//
// Motion layers (see styles/world.css):
//   (calm by design: no ambient drift or parallax; travellers are opt-in via `ambient`)
//   scroll   — useScrollProgress writes 0..1 into --p for scroll scenes
//   state    — paths draw to the learner's real position; nodes fill with mastery
//   transition — scenes morph between states with CSS transitions
// Reduced motion: travellers are not rendered, paths appear fully drawn,
// parallax is off. Hidden tabs pause ambient CSS animation (html.is-hidden).

import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "./motion.jsx";
import { AREAS } from "../lib/catalog.js";

// --- Hooks -----------------------------------------------------------------------------

// Pauses ambient CSS animation while the tab is hidden. Install once (App).
export function usePauseWhenHidden() {
  useEffect(() => {
    const on = () => document.documentElement.classList.toggle("is-hidden", document.hidden);
    document.addEventListener("visibilitychange", on);
    return () => document.removeEventListener("visibilitychange", on);
  }, []);
}

// Progress (0..1) of an element scrolling through the viewport: 0 when its
// top reaches the viewport top, 1 when its bottom reaches the viewport bottom.
export function useScrollProgress(ref) {
  const [p, setP] = useState(0);
  useEffect(() => {
    let raf = 0;
    const measure = () => {
      raf = 0;
      const el = ref.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const span = Math.max(1, r.height - window.innerHeight);
      const v = Math.min(1, Math.max(0, -r.top / span));
      el.style.setProperty("--p", v.toFixed(4));
      setP((old) => (Math.abs(old - v) > 0.002 ? v : old));
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(measure);
    };
    measure();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      cancelAnimationFrame(raf);
    };
  }, [ref]);
  return p;
}

// --- Geometry ---------------------------------------------------------------------------

// A soft, hand-cut territory outline around (cx, cy). Deterministic per seed.
export function blob(cx, cy, rx, ry, seed = 1, points = 9) {
  const pts = [];
  for (let i = 0; i < points; i++) {
    const a = (i / points) * Math.PI * 2;
    const wobble = 0.82 + 0.18 * Math.sin(seed * 12.9898 + i * 78.233) * Math.sin(seed + i * 1.7);
    pts.push([cx + Math.cos(a) * rx * wobble, cy + Math.sin(a) * ry * wobble]);
  }
  const mid = (p, q) => [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2];
  let d = `M ${mid(pts[pts.length - 1], pts[0]).join(" ")}`;
  pts.forEach((p, i) => {
    const m = mid(p, pts[(i + 1) % pts.length]);
    d += ` Q ${p[0].toFixed(1)} ${p[1].toFixed(1)} ${m[0].toFixed(1)} ${m[1].toFixed(1)}`;
  });
  return `${d} Z`;
}

// A gently curved path between two points (bend > 0 bows to one side).
export function curve([x1, y1], [x2, y2], bend = 0.18) {
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const dx = x2 - x1;
  const dy = y2 - y1;
  return `M ${x1} ${y1} Q ${(mx - dy * bend).toFixed(1)} ${(my + dx * bend).toFixed(1)} ${x2} ${y2}`;
}

// --- Primitives ---------------------------------------------------------------------------

let uid = 0;
const nextId = (p) => `${p}-${++uid}`;

// A path that draws itself and carries travelling particles (SMIL motion).
// Travellers are opt-in (`ambient`): the interface stays still unless motion carries meaning.
export function PathTrail({ d, tone = "blue", travellers = 2, duration = 7, drawn = 1, className = "", dashed = false, ambient = false }) {
  const reduced = useReducedMotion();
  const [id] = useState(() => nextId("trail"));
  return (
    <g className={`trail tone-${tone} ${className}`}>
      <path id={id} d={d} className={`trail-base ${dashed ? "dashed" : ""}`} />
      <path d={d} className="trail-draw" pathLength="1" style={{ "--drawn": drawn }} />
      {!reduced && ambient &&
        Array.from({ length: travellers }, (_, i) => (
          <circle key={i} r="3.2" className="trail-traveller">
            <animateMotion
              dur={`${duration}s`}
              begin={`${(-i * duration) / travellers}s`}
              repeatCount="indefinite"
              rotate="auto"
            >
              <mpath href={`#${id}`} />
            </animateMotion>
          </circle>
        ))}
    </g>
  );
}

// Small SVG motif per subject kind (used inside nodes and headers).
export function Motif({ type, x = 0, y = 0, s = 1 }) {
  const t = `translate(${x} ${y}) scale(${s})`;
  switch (type) {
    case "network":
      return (
        <g transform={t} className="motif motif-network">
          <path d="M-9 6 L0 -8 L9 6 Z" className="motif-line" />
          <circle cx="-9" cy="6" r="2.4" /><circle cx="0" cy="-8" r="2.4" /><circle cx="9" cy="6" r="2.4" />
          
        </g>
      );
    case "os":
      return (
        <g transform={t} className="motif motif-os">
          <rect x="-10" y="-9" width="20" height="5" rx="1.5" /><rect x="-10" y="-2" width="20" height="5" rx="1.5" />
          <rect x="-10" y="5" width="20" height="5" rx="1.5" />
          
        </g>
      );
    case "ml":
      return (
        <g transform={t} className="motif motif-ml">
          <path d="M-11 9 Q -2 6 2 -1 T 11 -9" className="motif-line" />
          <circle cx="-7" cy="-4" r="1.8" className="m-a" /><circle cx="-3" cy="-8" r="1.8" className="m-a" />
          <circle cx="4" cy="6" r="1.8" className="m-b" /><circle cx="8" cy="2" r="1.8" className="m-b" />
        </g>
      );
    case "dsa":
      return (
        <g transform={t} className="motif motif-dsa">
          <path d="M0 -8 L-7 1 M0 -8 L7 1 M-7 1 L-10 9 M-7 1 L-4 9 M7 1 L4 9 M7 1 L10 9" className="motif-line" />
          <circle cy="-8" r="2.4" /><circle cx="-7" cy="1" r="2.1" /><circle cx="7" cy="1" r="2.1" />
          
        </g>
      );
    case "agent":
      return (
        <g transform={t} className="motif motif-agent">
          <circle r="8" className="motif-line" />
          <circle cy="-8" r="2.2" /><circle cx="8" r="2.2" /><circle cy="8" r="2.2" /><circle cx="-8" r="2.2" />
          
        </g>
      );
    case "mlops":
      return (
        <g transform={t} className="motif motif-mlops">
          <path d="M-10 0 L10 0 M10 0 C 14 -10, -14 -10, -10 0" className="motif-line" />
          <circle cx="-10" r="2.4" /><circle r="2.4" /><circle cx="10" r="2.4" />
        </g>
      );
    case "ai":
      return (
        <g transform={t} className="motif motif-ai">
          <path d="M-9 -6 C -2 -6 -2 0 2 0 M-9 6 C -2 6 -2 0 2 0 M2 0 C 6 0 6 -7 10 -7 M2 0 C 6 0 6 7 10 7" className="motif-line" />
          <circle cx="-9" cy="-6" r="2" /><circle cx="-9" cy="6" r="2" /><circle cx="2" r="2.4" />
        </g>
      );
    default:
      return (
        <g transform={t} className="motif motif-paper">
          <path d="M-8 -10 H5 L9 -6 V10 H-8 Z" className="motif-line" />
          <path d="M-5 -4 H5 M-5 0 H5 M-5 4 H2" className="motif-line thin" />
        </g>
      );
  }
}

// --- The knowledge world -------------------------------------------------------------------

const W = 1000;
const H = 560;
// Territory centres and sizes on the map (paper-map layout).
export const TERRITORY = {
  "core-cs": { cx: 210, cy: 170, rx: 170, ry: 118 },
  "ai-ml": { cx: 505, cy: 150, rx: 165, ry: 112 },
  "modern-ai": { cx: 800, cy: 190, rx: 160, ry: 118 },
  "ai-eng": { cx: 735, cy: 425, rx: 175, ry: 104 },
  dsa: { cx: 300, cy: 420, rx: 180, ry: 108 },
};
const ROUTES = [
  ["dsa", "core-cs"],
  ["dsa", "ai-ml"],
  ["core-cs", "ai-ml"],
  ["ai-ml", "modern-ai"],
  ["modern-ai", "ai-eng"],
  ["ai-ml", "ai-eng"],
];

// Lay places out inside their territory (deterministic spiral).
function layout(places) {
  const byArea = {};
  places.forEach((p) => (byArea[p.area] = [...(byArea[p.area] || []), p]));
  const out = [];
  Object.entries(byArea).forEach(([area, list]) => {
    const t = TERRITORY[area];
    // Live subjects first, then roadmap; spread on a staggered grid inside the land.
    const sorted = [...list].sort((a, b) => Number(!!a.roadmap) - Number(!!b.roadmap));
    const n = sorted.length;
    const cols = n <= 1 ? 1 : n <= 4 ? 2 : n <= 9 ? 3 : 4;
    const rows = Math.ceil(n / cols);
    const w = t.rx * 1.25;
    const h = t.ry * 1.05;
    sorted.forEach((p, i) => {
      const r = Math.floor(i / cols);
      const c = i % cols;
      const inRow = Math.min(cols, n - r * cols);
      const x = t.cx + (inRow === 1 ? 0 : (c / (inRow - 1) - 0.5) * w) + (r % 2 ? 14 : -14) * (cols > 1);
      const y = t.cy + 16 + (rows === 1 ? 0 : (r / (rows - 1) - 0.5) * h);
      out.push({ ...p, x, y });
    });
  });
  return out;
}

/**
 * places: [{ id, name, area, motif, roadmap?, estimate?, coverage?, status? }]
 * here:   id of the place the learner is heading to (recommended destination)
 * selected: id highlighted; onSelect(id) makes places clickable.
 */
export function KnowledgeWorld({ places, here, selected, onSelect, focusArea, caption, compact = false }) {
  const ref = useRef(null);
  const nodes = layout(places);
  const youAt = nodes.find((n) => n.id === here);
  const start = [TERRITORY.dsa.cx - 150, TERRITORY.dsa.cy + 70];

  return (
    <div ref={ref} className={`kworld ${compact ? "compact" : ""} ${focusArea ? "has-focus" : ""}`}>
      <svg viewBox={`0 0 ${W} ${H}`} className="kworld-svg" role="img"
        aria-label={caption || "Map of learning areas and subjects"}>
        <defs>
          <pattern id="kw-hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">
            <line x1="0" y1="0" x2="0" y2="7" className="kw-hatch-line" />
          </pattern>
        </defs>
        <g className="kw-layer kw-back">
          {AREAS.map((a, i) => {
            const t = TERRITORY[a.id];
            return (
              <g key={a.id} className={`kw-territory tone-${a.tone} ${focusArea === a.id ? "focus" : ""}`}
                style={{ "--i": i }}>
                <path d={blob(t.cx, t.cy, t.rx, t.ry, i + 2)} className="kw-land" />
                <path d={blob(t.cx, t.cy, t.rx * 0.92, t.ry * 0.9, i + 7)} className="kw-hatch" />
                <text x={t.cx} y={t.cy - t.ry + 30} className="kw-area-label" textAnchor="middle">
                  {a.name.toUpperCase()}
                </text>
              </g>
            );
          })}
        </g>
        <g className="kw-layer kw-mid">
          {ROUTES.map(([a, b], i) => {
            const A = TERRITORY[a];
            const B = TERRITORY[b];
            return (
              <PathTrail key={i} d={curve([A.cx, A.cy + 8], [B.cx, B.cy + 8], i % 2 ? 0.14 : -0.14)}
                tone="ink" travellers={1} duration={9 + i} dashed />
            );
          })}
          {youAt && (
            <PathTrail d={curve(start, [youAt.x, youAt.y], -0.22)} tone="blue" travellers={2} duration={5}
              className="kw-route" />
          )}
        </g>
        <g className="kw-layer kw-front">
          {youAt && (
            <g className="kw-you" transform={`translate(${start[0]} ${start[1]})`}>
              <circle r="11" className="kw-you-dot" />
              <text y="4" textAnchor="middle" className="kw-you-text">YOU</text>
            </g>
          )}
          {nodes.map((n, i) => {
            const est = n.estimate ?? 0;
            const C = 2 * Math.PI * 17;
            const click = onSelect ? () => onSelect(n.id) : undefined;
            return (
              <g key={n.id}
                className={`kw-node ${n.roadmap ? "roadmap" : "live"} ${selected === n.id ? "selected" : ""} ${here === n.id ? "here" : ""} st-${n.status || "none"}`}
                transform={`translate(${n.x.toFixed(1)} ${n.y.toFixed(1)})`}
                style={{ "--i": i }}
                onClick={click}
                onKeyDown={click ? (e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), click()) : undefined}
                tabIndex={click ? 0 : undefined}
                role={click ? "button" : undefined}
                aria-label={`${n.name}${n.roadmap ? " (roadmap, no content yet)" : n.estimate != null ? `, ${Math.round(est * 100)}% estimated` : ""}`}>
                <g className="kw-node-body">
                  <circle r="17" className="kw-node-disc" />
                  {!n.roadmap && n.estimate != null && (
                    <circle r="17" className="kw-node-arc" strokeDasharray={C} strokeDashoffset={C * (1 - est)}
                      transform="rotate(-90)" />
                  )}
                  <Motif type={n.motif} s={0.72} />
                </g>
                <text y="31" textAnchor="middle" className="kw-node-label">{n.short || n.name}</text>
              </g>
            );
          })}
        </g>
      </svg>
      {caption && <p className="kworld-caption">{caption}</p>}
    </div>
  );
}

// --- Route: YOU → area → subject → destination ----------------------------------------------

export function RouteMap({ stops }) {
  // stops: [{ label, sub }] from the learner's position to the destination.
  const pts = stops.map((_, i) => [70 + (i * 860) / Math.max(1, stops.length - 1), i % 2 ? 150 : 90]);
  const d = pts.reduce((acc, p, i) => (i ? `${acc} ${curve(pts[i - 1], p, i % 2 ? 0.2 : -0.2).replace(/^M [^Q]+/, "")}` : `M ${p[0]} ${p[1]}`), "");
  return (
    <div className="route">
      <svg viewBox="0 0 1000 230" className="route-svg" aria-hidden="true">
        <g className="route-layer">
        <PathTrail d={d} tone="blue" travellers={3} duration={6} className="route-trail" />
        {pts.map(([x, y], i) => (
          <g key={i} transform={`translate(${x} ${y})`}>
          <g className={`route-stop ${i === 0 ? "start" : i === pts.length - 1 ? "end" : ""}`} style={{ "--i": i }}>
            <circle r={i === pts.length - 1 ? 13 : 8} className="route-dot" />
            {i === pts.length - 1 && <circle r="22" className="route-halo" />}
            <text y={i % 2 ? 40 : -24} textAnchor="middle" className="route-label">{stops[i].label}</text>
            {stops[i].sub && (
              <text y={i % 2 ? 56 : -40} textAnchor="middle" className="route-sub">{stops[i].sub}</text>
            )}
          </g>
          </g>
        ))}
        </g>
      </svg>
    </div>
  );
}

// --- Teaching loop as a travelled path ---------------------------------------------------------

export function LoopPath({ stages, current }) {
  const idx = Math.max(0, stages.indexOf(current));
  const xs = stages.map((_, i) => 40 + (i * 520) / (stages.length - 1));
  const d = `M ${xs[0]} 34 ${xs.slice(1).map((x, i) => `Q ${(xs[i] + x) / 2} ${i % 2 ? 10 : 58} ${x} 34`).join(" ")}`;
  return (
    <div className="looppath" role="list" aria-label="Teaching loop">
      <svg viewBox="0 0 600 70" className="looppath-svg" aria-hidden="true">
        <path d={d} className="lp-base" />
        <path d={d} className="lp-done" pathLength="1" style={{ "--drawn": idx / (stages.length - 1) }} />
        {xs.map((x, i) => (
          <circle key={i} cx={x} cy="34" r={i === idx ? 9 : 6}
            className={`lp-stop ${i < idx ? "done" : i === idx ? "now" : ""}`} />
        ))}
      </svg>
      <div className="looppath-labels">
        {stages.map((s, i) => (
          <span key={s} role="listitem" className={i < idx ? "done" : i === idx ? "now" : ""}
            aria-current={i === idx ? "step" : undefined}>
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}
