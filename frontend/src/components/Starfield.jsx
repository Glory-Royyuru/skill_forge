import { useEffect, useRef } from "react";
import { getEffectiveTheme, subscribeTheme } from "../lib/theme.js";

// App-wide night sky. Mounted once by the app shell, behind everything,
// never interactive (pointer-events: none) and hidden from assistive tech.
//
// How it stays cheap and calm:
//  - Stars are drawn once into two static canvases (far, near). Pointer
//    parallax moves those canvases with CSS transforms, so moving the mouse
//    never redraws a star.
//  - A third canvas holds the only things that change: a handful of slowly
//    twinkling stars (repainted in small rectangles a few times a second) and,
//    now and then, one shooting star.
//  - Nothing runs while the tab is hidden. Reduced motion: a still sky, no
//    parallax, no shooting stars. No canvas support: the CSS atmosphere only.
//  - Star positions come from a fixed seed, so the sky is the same on every
//    visit and on every page; resizing only changes how many are drawn.

const MAX_STARS = 1400;
const NEAR_SHARE = 0.18; // the rest are distant
const SHIFT = { far: 4, near: 12 }; // max parallax in CSS px
const MARGIN = 16; // layers overhang the viewport so parallax never shows an edge

const PALETTE = {
  dark: {
    density: 1 / 2300, // stars per CSS px²
    alpha: [0.2, 0.95],
    colors: [[236, 242, 255], [196, 214, 255], [255, 230, 200]],
    glow: 0.22,
    meteor: [232, 240, 255],
    meteorAlpha: 0.85,
    meteorEvery: [14, 34], // seconds between shooting stars
  },
  light: {
    density: 1 / 4200,
    alpha: [0.16, 0.52],
    colors: [[58, 86, 168], [24, 104, 184], [150, 112, 56]], // indigo, cobalt, a few warm
    glow: 0,
    meteor: [36, 70, 140],
    meteorAlpha: 0.38,
    meteorEvery: [26, 60],
  },
};

function mulberry32(seed) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Positions are normalised (0..1). About a quarter of the distant stars
// gather loosely along a faint diagonal band, like a far-off Milky Way.
function makeStars() {
  const rnd = mulberry32(20261013);
  const gauss = () => (rnd() + rnd() + rnd() - 1.5) / 1.5;
  const stars = [];
  for (let i = 0; i < MAX_STARS; i++) {
    const near = rnd() < NEAR_SHARE;
    let x = rnd();
    let y = rnd();
    if (!near && rnd() < 0.27) {
      const t = rnd();
      x = t;
      y = 0.88 - 0.72 * t + gauss() * 0.09;
      if (y < 0 || y > 1) y = rnd();
    }
    const m = Math.pow(rnd(), 2.6); // many faint stars, few bright ones
    const tone = rnd();
    stars.push({
      x, y, near, m,
      r: near ? 0.55 + 0.95 * m : 0.32 + 0.55 * m,
      color: tone < 0.84 ? 0 : tone < 0.94 ? 1 : 2,
      // Twinklers are mid-brightness and never carry a glow, so each one can be
      // repainted inside a small rectangle without leaving halo residue.
      twinkle: !near && m > 0.12 && m < 0.5 && rnd() < 0.05,
      period: 3 + rnd() * 6,
      phase: rnd() * Math.PI * 2,
    });
  }
  return stars;
}

function glowSprite() {
  const c = document.createElement("canvas");
  c.width = c.height = 32;
  const g = c.getContext("2d");
  const grad = g.createRadialGradient(16, 16, 0, 16, 16, 16);
  grad.addColorStop(0, "rgba(255,255,255,0.9)");
  grad.addColorStop(0.25, "rgba(255,255,255,0.25)");
  grad.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, 32, 32);
  return c;
}

const reducedMotion = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
const skyMode = () => document.documentElement.dataset.sky || "calm";

export default function Starfield() {
  const host = useRef(null);

  useEffect(() => {
    const el = host.current;
    const canvases = [...el.querySelectorAll("canvas")];
    const ctxs = canvases.map((c) => c.getContext?.("2d"));
    if (ctxs.some((c) => !c)) return undefined; // no canvas: CSS atmosphere only
    const [farC, nearC, fxC] = canvases;
    const [far, near, fx] = ctxs;
    const stars = makeStars();
    const sprite = glowSprite();
    const s = {
      w: 0, h: 0, dpr: 1, n: 0, pal: PALETTE.light, twinklers: [],
      off: { x: 0, y: 0 }, target: { x: 0, y: 0 },
      meteor: null, prevBox: null, raf: 0, twinkleTimer: 0, meteorTimer: 0, resizeTimer: 0,
      last: 0, dead: false,
    };

    const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${a.toFixed(3)})`;
    const starAlpha = (st) => s.pal.alpha[0] + (s.pal.alpha[1] - s.pal.alpha[0]) * st.m;
    const px = (st) => [st.x * s.w + MARGIN, st.y * s.h + MARGIN];

    const GLOW_FROM = 0.55;
    const glowRadius = (st) => 3 + st.r * 4;
    const drawStar = (g, st, a) => {
      const [x, y] = px(st);
      const col = s.pal.colors[st.color];
      if (s.pal.glow && st.m > GLOW_FROM) {
        const gr = glowRadius(st);
        g.globalAlpha = s.pal.glow * st.m;
        g.drawImage(sprite, x - gr, y - gr, gr * 2, gr * 2);
        g.globalAlpha = 1;
      }
      g.fillStyle = rgba(col, a);
      if (st.r < 0.6) {
        // Sub-pixel stars as tiny squares: crisper than anti-aliased circles.
        const d = Math.max(0.7, st.r * 1.6);
        g.fillRect(x - d / 2, y - d / 2, d, d);
      } else {
        g.beginPath();
        g.arc(x, y, st.r, 0, Math.PI * 2);
        g.fill();
      }
    };

    const sizeCanvas = (c, g) => {
      c.width = Math.round((s.w + MARGIN * 2) * s.dpr);
      c.height = Math.round((s.h + MARGIN * 2) * s.dpr);
      g.setTransform(s.dpr, 0, 0, s.dpr, 0, 0);
    };

    const paintStatic = () => {
      s.pal = PALETTE[getEffectiveTheme() === "dark" ? "dark" : "light"];
      s.n = Math.min(MAX_STARS, Math.round(s.w * s.h * s.pal.density));
      far.clearRect(0, 0, s.w + MARGIN * 2, s.h + MARGIN * 2);
      near.clearRect(0, 0, s.w + MARGIN * 2, s.h + MARGIN * 2);
      s.twinklers = [];
      for (let i = 0; i < s.n; i++) {
        const st = stars[i];
        if (st.twinkle) s.twinklers.push(st);
        else drawStar(st.near ? near : far, st, starAlpha(st));
      }
      paintFx(performance.now(), true);
    };

    // The changing layer: twinklers, then the shooting star on top.
    const twinkleRect = (st) => {
      const [x, y] = px(st);
      const r = (st.m > GLOW_FROM ? glowRadius(st) : st.r) + 2;
      return [x - r, y - r, r * 2, r * 2];
    };
    const paintFx = (now, full = false) => {
      if (full) fx.clearRect(0, 0, s.w + MARGIN * 2, s.h + MARGIN * 2);
      else if (s.prevBox) fx.clearRect(...s.prevBox);
      s.prevBox = null;
      const still = reducedMotion();
      for (const st of s.twinklers) {
        if (!full) fx.clearRect(...twinkleRect(st));
        const k = still ? 1 : 0.72 + 0.28 * Math.sin(now / 1000 / st.period * Math.PI * 2 + st.phase);
        drawStar(fx, st, starAlpha(st) * k);
      }
      if (s.meteor) drawMeteor(now);
    };

    const drawMeteor = (now) => {
      const m = s.meteor;
      const t = (now - m.start) / m.dur;
      if (t >= 1) {
        s.meteor = null;
        scheduleMeteor();
        return;
      }
      const ease = 1 - Math.pow(1 - t, 1.6); // decelerates slightly as it burns out
      const hx = m.x + m.dx * m.dist * ease;
      const hy = m.y + m.dy * m.dist * ease;
      const len = m.len * Math.min(1, t * 4); // the trail grows, then travels
      const tx = hx - m.dx * len;
      const ty = hy - m.dy * len;
      const a = s.pal.meteorAlpha * Math.min(1, t * 6) * Math.pow(1 - t, 1.2);
      // Tapered trail: a thin wedge from tail (nothing) to head (width w).
      const w = 1.3;
      const nx = -m.dy * w;
      const ny = m.dx * w;
      const grad = fx.createLinearGradient(tx, ty, hx, hy);
      grad.addColorStop(0, rgba(s.pal.meteor, 0));
      grad.addColorStop(1, rgba(s.pal.meteor, a));
      fx.fillStyle = grad;
      fx.beginPath();
      fx.moveTo(tx, ty);
      fx.lineTo(hx + nx / 2, hy + ny / 2);
      fx.lineTo(hx - nx / 2, hy - ny / 2);
      fx.closePath();
      fx.fill();
      if (s.pal.glow) {
        fx.globalAlpha = a * 0.7;
        fx.drawImage(sprite, hx - 5, hy - 5, 10, 10);
        fx.globalAlpha = 1;
      } else {
        fx.fillStyle = rgba(s.pal.meteor, a);
        fx.fillRect(hx - 1, hy - 1, 2, 2);
      }
      s.prevBox = [Math.min(tx, hx) - 8, Math.min(ty, hy) - 8, Math.abs(hx - tx) + 16, Math.abs(hy - ty) + 16];
    };

    const spawnMeteor = () => {
      s.meteorTimer = 0;
      if (s.dead || document.hidden || reducedMotion() || skyMode() === "focus") return scheduleMeteor();
      const rnd = Math.random;
      const leftToRight = rnd() < 0.5;
      const angle = ((18 + rnd() * 22) * Math.PI) / 180; // 18–40° below horizontal
      const dx = Math.cos(angle) * (leftToRight ? 1 : -1);
      const dy = Math.sin(angle);
      const dist = Math.min(s.w * 0.45, 180 + rnd() * 220);
      s.meteor = {
        x: MARGIN + s.w * (leftToRight ? 0.05 + rnd() * 0.6 : 0.35 + rnd() * 0.6),
        y: MARGIN + s.h * (0.04 + rnd() * 0.4),
        dx, dy, dist,
        len: 70 + rnd() * 110,
        dur: 650 + rnd() * 600,
        start: performance.now(),
      };
      loop();
    };
    function scheduleMeteor() {
      clearTimeout(s.meteorTimer);
      if (s.dead) return;
      const [lo, hi] = s.pal.meteorEvery;
      s.meteorTimer = setTimeout(spawnMeteor, (lo + Math.random() * (hi - lo)) * 1000);
    }

    // One rAF loop while something moves (parallax easing or a shooting star).
    const applyOffsets = () => {
      farC.style.transform = `translate3d(${(s.off.x * SHIFT.far).toFixed(2)}px, ${(s.off.y * SHIFT.far).toFixed(2)}px, 0)`;
      nearC.style.transform = `translate3d(${(s.off.x * SHIFT.near).toFixed(2)}px, ${(s.off.y * SHIFT.near).toFixed(2)}px, 0)`;
      fxC.style.transform = farC.style.transform;
    };
    const tick = (now) => {
      s.raf = 0;
      if (s.dead || document.hidden) return;
      const dt = Math.min(0.05, (now - (s.last || now)) / 1000);
      s.last = now;
      const ex = s.target.x - s.off.x;
      const ey = s.target.y - s.off.y;
      const moving = Math.abs(ex) > 0.002 || Math.abs(ey) > 0.002;
      if (moving) {
        const k = 1 - Math.exp(-dt * 2.2); // slow, smooth follow
        s.off.x += ex * k;
        s.off.y += ey * k;
        applyOffsets();
      }
      if (s.meteor) paintFx(now);
      if (moving || s.meteor) loop();
      else s.last = 0;
    };
    function loop() {
      if (!s.raf && !s.dead && !document.hidden) s.raf = requestAnimationFrame(tick);
    }

    const stopTwinkle = () => {
      clearInterval(s.twinkleTimer);
      s.twinkleTimer = 0;
    };
    const startTwinkle = () => {
      stopTwinkle();
      if (reducedMotion() || document.hidden) return;
      s.twinkleTimer = setInterval(() => {
        if (!s.meteor) paintFx(performance.now());
      }, 140);
    };

    // Pointer: mouse and pen only, so touch scrolling is never involved.
    const onMove = (e) => {
      if (e.pointerType === "touch" || reducedMotion()) return;
      const scale = skyMode() === "focus" ? 0.5 : 1;
      s.target.x = -((e.clientX / s.w) * 2 - 1) * scale;
      s.target.y = -((e.clientY / s.h) * 2 - 1) * scale;
      loop();
    };
    const onLeave = (e) => {
      if (!e.relatedTarget) {
        s.target.x = s.target.y = 0;
        loop();
      }
    };

    const measure = () => {
      s.w = el.clientWidth;
      s.h = el.clientHeight;
      const big = s.w * s.h > 2.4e6;
      s.dpr = Math.min(window.devicePixelRatio || 1, big ? 1 : 1.5);
      canvases.forEach((c, i) => sizeCanvas(c, ctxs[i]));
      paintStatic();
    };
    // Mobile browser bars change the height while scrolling; only rebuild on
    // a width change or a large height change.
    const onResize = () => {
      clearTimeout(s.resizeTimer);
      s.resizeTimer = setTimeout(() => {
        if (el.clientWidth !== s.w || Math.abs(el.clientHeight - s.h) > 140) measure();
      }, 180);
    };
    const onVisibility = () => {
      if (document.hidden) {
        cancelAnimationFrame(s.raf);
        s.raf = 0;
        stopTwinkle();
      } else {
        s.last = 0;
        startTwinkle();
        loop();
      }
    };
    const motionQuery = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    const onMotionChange = () => {
      s.off.x = s.off.y = s.target.x = s.target.y = 0;
      s.meteor = null;
      applyOffsets();
      paintFx(performance.now(), true);
      startTwinkle();
    };

    measure();
    startTwinkle();
    // The first shooting star waits a while; the sky starts quiet.
    s.meteorTimer = setTimeout(spawnMeteor, (8 + Math.random() * 10) * 1000);
    window.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerout", onLeave, { passive: true });
    window.addEventListener("resize", onResize);
    document.addEventListener("visibilitychange", onVisibility);
    motionQuery?.addEventListener?.("change", onMotionChange);
    const unTheme = subscribeTheme(() => paintStatic());
    el.dataset.ready = "true";

    // Test hook: lets the browser harness trigger one shooting star on demand.
    el.__sky = { spawn: () => { clearTimeout(s.meteorTimer); spawnMeteor(); }, state: s };

    return () => {
      s.dead = true;
      cancelAnimationFrame(s.raf);
      clearInterval(s.twinkleTimer);
      clearTimeout(s.meteorTimer);
      clearTimeout(s.resizeTimer);
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerout", onLeave);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", onVisibility);
      motionQuery?.removeEventListener?.("change", onMotionChange);
      unTheme();
      delete el.__sky;
      delete el.dataset.ready;
    };
  }, []);

  return (
    <div className="sky" ref={host} aria-hidden="true">
      <div className="sky-atmos" />
      <canvas className="sky-layer sky-far" />
      <canvas className="sky-layer sky-near" />
      <canvas className="sky-layer sky-fx" />
    </div>
  );
}
