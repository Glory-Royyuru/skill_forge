// Decorative, non-interactive seasonal layer. Rendered once by the app shell
// when a season is active; it sits behind nothing important (pointer-events:
// none), is hidden from assistive technology, keeps to the page edges, and
// stops animating for users who prefer reduced motion.

const DOTS = Array.from({ length: 14 }, (_, i) => ({
  left: (i * 37 + 11) % 100,
  delay: (i * 1.7) % 12,
  duration: 14 + (i % 5) * 3,
  size: 3 + (i % 3),
}));

function Diya({ x }) {
  return (
    <svg className="diya" style={{ left: `${x}%` }} width="34" height="26" viewBox="0 0 34 26">
      <path className="diya-flame" d="M17 2c3 4 3 7 0 9-3-2-3-5 0-9z" />
      <path className="diya-bowl" d="M3 14h28c-2 6-7 9-14 9S5 20 3 14z" />
    </svg>
  );
}

export default function SeasonalLayer({ season }) {
  if (!season) return null;
  return (
    <div className={`season season-${season}`} aria-hidden="true">
      {(season === "christmas" || season === "newyear") && (
        <div className="season-particles">
          {DOTS.map((d, i) => (
            <span
              key={i}
              className="particle"
              style={{
                left: `${d.left}%`,
                width: d.size,
                height: d.size,
                animationDelay: `${-d.delay}s`,
                animationDuration: `${d.duration}s`,
              }}
            />
          ))}
        </div>
      )}
      {season === "christmas" && (
        <svg className="season-corner" width="56" height="56" viewBox="0 0 56 56">
          <path d="M28 6l4.5 9.5L43 17l-7.5 7.2L37.5 35 28 30l-9.5 5 2-10.8L13 17l10.5-1.5z" />
        </svg>
      )}
      {season === "diwali" && (
        <div className="diyas">
          {[6, 22, 78, 94].map((x) => (
            <Diya key={x} x={x} />
          ))}
        </div>
      )}
      {season === "halloween" && (
        <svg className="season-corner moon" width="60" height="60" viewBox="0 0 60 60">
          <path d="M40 8a22 22 0 1 0 12 30A18 18 0 1 1 40 8z" />
        </svg>
      )}
    </div>
  );
}
