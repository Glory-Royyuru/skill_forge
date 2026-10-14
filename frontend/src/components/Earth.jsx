import { useEffect, useRef, useState } from "react";
import { subscribeTheme, getEffectiveTheme } from "../lib/theme.js";
import { prefersReducedMotion } from "./motion.jsx";

// SkillForge's Earth: a WebGL globe rendered from NASA Blue Marble imagery
// (see public/earth/ATTRIBUTION.txt). It is a symbol — "knowledge has no
// borders" — never a data visualisation: nothing on it encodes a learner's
// progress or any geographic statistic.
//
// Behaviour:
//  - Three.js is loaded lazily; a static CSS globe (real imagery) shows first
//    and remains if WebGL or the textures are unavailable.
//  - Drag to rotate (with inertia); vertical touch scrolling still scrolls the
//    page (touch-action: pan-y). Zoom only via buttons or pinch / ctrl+wheel,
//    within limits. Arrow keys rotate; Reset restores the view.
//  - Frames render only while something moves and the globe is on screen.
//    Idle rotation is almost imperceptible and off for reduced motion.

const TEX = "/earth/";
const TILT = (23.4 * Math.PI) / 180;
const START_YAW = -1.45; // opens on Africa, Europe and the Atlantic (no meaning attached)
const START_PITCH = 0.18;
const IDLE_SPEED = 0.0035; // rad/s — one turn every ~30 minutes
const DIST = { min: 3.7, start: 4.6, max: 5.6 };

// Symbolic connections (unlabelled great-circle arcs). Not data.
const ARCS = [
  [[17.4, 78.5], [51.5, -0.1]],
  [[17.4, 78.5], [1.35, 103.8]],
  [[40.7, -74.0], [-23.5, -46.6]],
  [[35.7, 139.7], [-33.9, 151.2]],
  [[6.5, 3.4], [52.5, 13.4]],
];

// Probe for WebGL, then release the probe's context straight away so it does
// not count against the browser's limit on live contexts.
function webglAvailable() {
  try {
    const c = document.createElement("canvas");
    const gl = c.getContext("webgl2") || c.getContext("webgl");
    if (!gl) return false;
    gl.getExtension("WEBGL_lose_context")?.loseContext();
    return true;
  } catch {
    return false;
  }
}

// Idle drift is slow enough that a frame every ~80 ms moves the globe by a
// fraction of a pixel. Render only when the surface has moved about half a
// pixel, so an idle globe costs a few frames a second, not twelve.
function idleInterval(radiusPx) {
  const ms = (0.5 / Math.max(1, radiusPx * IDLE_SPEED)) * 1000;
  return Math.max(80, Math.min(1000, ms));
}

const VERT = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vNormal;
  varying vec3 vView;
  void main() {
    vUv = uv;
    vNormal = normalize(normalMatrix * normal);
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vView = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }
`;

const EARTH_FRAG = /* glsl */ `
  uniform sampler2D dayMap;
  uniform sampler2D nightMap;
  uniform vec3 sunDir;
  uniform float ambient;
  uniform float nightStrength;
  uniform vec3 atmo;
  varying vec2 vUv;
  varying vec3 vNormal;
  varying vec3 vView;
  void main() {
    vec3 n = normalize(vNormal);
    float l = dot(n, sunDir);
    float lit = smoothstep(-0.12, 0.35, l);
    vec3 day = texture2D(dayMap, vUv).rgb;
    vec3 col = day * (ambient + (1.0 - ambient) * max(l, 0.0) * 1.15);
    // City lights on the night side (dark theme).
    col += texture2D(nightMap, vUv).rgb * vec3(1.0, 0.82, 0.55) * (1.0 - lit) * nightStrength;
    // Thin atmospheric scattering at the limb.
    float fres = pow(1.0 - max(dot(n, vView), 0.0), 3.0);
    col += atmo * fres * (0.1 + 0.32 * lit);
    gl_FragColor = vec4(col, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

const CLOUD_FRAG = /* glsl */ `
  uniform sampler2D cloudMap;
  uniform vec3 sunDir;
  uniform float ambient;
  varying vec2 vUv;
  varying vec3 vNormal;
  varying vec3 vView;
  void main() {
    float c = texture2D(cloudMap, vUv).r;
    float l = max(dot(normalize(vNormal), sunDir), 0.0);
    float a = smoothstep(0.18, 0.85, c) * 0.85;
    gl_FragColor = vec4(vec3(ambient * 0.6 + l), a * (0.25 + 0.75 * smoothstep(-0.1, 0.3, l)));
    #include <colorspace_fragment>
  }
`;

const ATMO_FRAG = /* glsl */ `
  uniform vec3 atmo;
  uniform float strength;
  varying vec3 vNormal;
  varying vec3 vView;
  void main() {
    float i = pow(max(0.0, 0.7 - dot(normalize(vNormal), normalize(vView))), 4.0);
    gl_FragColor = vec4(atmo, 1.0) * i * strength;
    #include <colorspace_fragment>
  }
`;

const LIGHTING = {
  light: { sun: [-0.55, 0.35, 0.76], ambient: 0.32, night: 0.0, exposure: 1.05, atmo: [0.42, 0.72, 0.95], atmoStrength: 0.75 },
  dark: { sun: [-0.85, 0.25, 0.46], ambient: 0.1, night: 1.6, exposure: 1.15, atmo: [0.38, 0.75, 0.98], atmoStrength: 0.9 },
};

export default function Earth({ className = "", label = "The Earth, a symbol of knowledge without borders", arcs = true, compact = false }) {
  const host = useRef(null);
  const [state, setState] = useState("loading"); // loading | ready | fallback
  const api = useRef({});

  useEffect(() => {
    const el = host.current;
    if (!el) return undefined;
    if (!webglAvailable()) {
      setState("fallback");
      return undefined;
    }
    let disposed = false;
    let cleanup = () => {};

    (async () => {
      let THREE;
      try {
        THREE = await import("./three-lite.js");
      } catch {
        if (!disposed) setState("fallback");
        return;
      }
      if (disposed) return;

      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      const canvas = renderer.domElement;
      canvas.className = "earth-canvas";
      canvas.setAttribute("aria-hidden", "true");

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 50);
      camera.position.set(0, 0, DIST.start);

      const loader = new THREE.TextureLoader();
      const load = (name, srgb = true) =>
        new Promise((res, rej) =>
          loader.load(TEX + name, (t) => {
            if (srgb) t.colorSpace = THREE.SRGBColorSpace;
            t.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy());
            res(t);
          }, undefined, rej)
        );
      const release = () => {
        renderer.dispose();
        renderer.forceContextLoss();
      };
      let day, clouds;
      try {
        [day, clouds] = await Promise.all([load("earth-day-2k.jpg"), load("earth-clouds-2k.jpg", false)]);
      } catch {
        release();
        if (!disposed) setState("fallback");
        return;
      }
      if (disposed) {
        [day, clouds].forEach((t) => t.dispose());
        release();
        return;
      }
      // City lights only show in the dark theme, so that texture is fetched
      // the first time the dark theme is in effect, not on every visit.
      const black = new THREE.DataTexture(new Uint8Array([0, 0, 0, 255]), 1, 1);
      black.needsUpdate = true;
      let night = null;
      let nightLoading = false;
      const ensureNight = () => {
        if (night || nightLoading) return;
        nightLoading = true;
        load("earth-night-2k.jpg")
          .then((t) => {
            if (disposed) return t.dispose();
            night = t;
            earthMat.uniforms.nightMap.value = t;
            request();
          })
          .catch(() => {}) // without the texture the night side simply stays dark
          .finally(() => (nightLoading = false));
      };

      const sunDir = new THREE.Vector3();
      const atmo = new THREE.Color();
      const earthMat = new THREE.ShaderMaterial({
        uniforms: {
          dayMap: { value: day }, nightMap: { value: black },
          sunDir: { value: sunDir }, ambient: { value: 0.3 }, nightStrength: { value: 0 }, atmo: { value: atmo },
        },
        vertexShader: VERT, fragmentShader: EARTH_FRAG,
      });
      const cloudMat = new THREE.ShaderMaterial({
        uniforms: { cloudMap: { value: clouds }, sunDir: { value: sunDir }, ambient: { value: 0.3 } },
        vertexShader: VERT, fragmentShader: CLOUD_FRAG, transparent: true, depthWrite: false,
      });
      const atmoMat = new THREE.ShaderMaterial({
        uniforms: { atmo: { value: atmo }, strength: { value: 1 } },
        vertexShader: VERT, fragmentShader: ATMO_FRAG, side: THREE.BackSide,
        blending: THREE.AdditiveBlending, transparent: true, depthWrite: false,
      });

      const tilt = new THREE.Group();
      tilt.rotation.z = TILT;
      const spin = new THREE.Group();
      tilt.add(spin);
      const sphere = new THREE.SphereGeometry(1, 96, 64);
      spin.add(new THREE.Mesh(sphere, earthMat));
      const cloudMesh = new THREE.Mesh(new THREE.SphereGeometry(1.008, 96, 64), cloudMat);
      cloudMesh.rotation.y = 0.6;
      spin.add(cloudMesh);
      const atmoMesh = new THREE.Mesh(new THREE.SphereGeometry(1.045, 64, 48), atmoMat);
      scene.add(atmoMesh);
      scene.add(tilt);

      // Symbolic arcs: thin, warm, static.
      const arcObjs = [];
      if (arcs) {
        const v = (lat, lon, r = 1.0) => {
          const phi = ((90 - lat) * Math.PI) / 180;
          const th = ((lon + 180) * Math.PI) / 180;
          return new THREE.Vector3(-r * Math.sin(phi) * Math.cos(th), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(th));
        };
        const lineMat = new THREE.LineBasicMaterial({ color: 0xf2b27a, transparent: true, opacity: 0.55 });
        const dotMat = new THREE.MeshBasicMaterial({ color: 0xffe2bd });
        const dotGeo = new THREE.SphereGeometry(0.009, 8, 8);
        ARCS.forEach(([a, b]) => {
          const A = v(...a);
          const B = v(...b);
          const pts = [];
          for (let i = 0; i <= 48; i++) {
            const t = i / 48;
            const p = new THREE.Vector3().copy(A).lerp(B, t).normalize();
            pts.push(p.multiplyScalar(1.003 + Math.sin(Math.PI * t) * 0.12 * A.distanceTo(B) * 0.5));
          }
          const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), lineMat);
          spin.add(line);
          arcObjs.push(line);
          [A, B].forEach((p) => {
            const d = new THREE.Mesh(dotGeo, dotMat);
            d.position.copy(p).multiplyScalar(1.004);
            spin.add(d);
            arcObjs.push(d);
          });
        });
        arcObjs.push({ geometry: dotGeo, material: dotMat }, { material: lineMat });
      }

      // --- State -------------------------------------------------------------
      const s = { yaw: START_YAW, pitch: START_PITCH, vy: 0, vp: 0, dist: DIST.start, targetDist: DIST.start,
        dragging: false, lastX: 0, lastY: 0, idleHold: 0, visible: true, raf: 0, timer: 0, last: 0, pointers: new Map(), pinch0: 0, pinchDist: 0 };
      const reduced = () => prefersReducedMotion();

      const applyTheme = () => {
        const dark = getEffectiveTheme() === "dark";
        const L = LIGHTING[dark ? "dark" : "light"];
        if (dark) ensureNight();
        sunDir.set(...L.sun).normalize();
        earthMat.uniforms.ambient.value = L.ambient;
        cloudMat.uniforms.ambient.value = L.ambient;
        earthMat.uniforms.nightStrength.value = L.night;
        atmo.setRGB(...L.atmo);
        atmoMat.uniforms.strength.value = L.atmoStrength;
        renderer.toneMappingExposure = L.exposure;
        request();
      };

      const resize = () => {
        const w = el.clientWidth;
        const h = el.clientHeight;
        if (!w || !h) return;
        renderer.setSize(w, h, false);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        request();
      };

      const draw = () => {
        spin.rotation.y = s.yaw;
        tilt.rotation.x = s.pitch;
        camera.position.z = s.dist;
        renderer.render(scene, camera);
        el.dataset.yaw = s.yaw.toFixed(3);
        el.dataset.zoom = s.dist.toFixed(2);
      };

      // Render loop: runs only while something changes.
      const tick = (now) => {
        s.raf = 0;
        if (s.dead) return;
        const elapsed = (now - (s.last || now)) / 1000;
        const dt = Math.min(0.05, elapsed);
        s.last = now;
        let moving = false;
        if (!s.dragging && (Math.abs(s.vy) > 0.0005 || Math.abs(s.vp) > 0.0005)) {
          s.yaw += s.vy * dt * 60;
          s.pitch = Math.max(-1, Math.min(1, s.pitch + s.vp * dt * 60));
          s.vy *= 0.94;
          s.vp *= 0.94;
          moving = true;
        }
        if (Math.abs(s.targetDist - s.dist) > 0.002) {
          s.dist += (s.targetDist - s.dist) * Math.min(1, dt * 10);
          moving = true;
        }
        const idle = !reduced() && !s.dragging && now > s.idleHold;
        // Capped just above the longest idle frame interval (1 s), so the drift keeps
        // its speed while a return from a hidden tab cannot cause a jump.
        if (idle) s.yaw += IDLE_SPEED * Math.min(1.1, elapsed);
        draw();
        if (!s.visible || document.hidden) return;
        if (moving || s.dragging) s.raf = requestAnimationFrame(tick);
        else if (idle) s.timer = setTimeout(() => { s.timer = 0; request(); }, idleInterval((el.clientWidth / 2) * (DIST.start / s.dist)));
        else if (!reduced() && !s.dragging) {
          // Resume the idle drift once the post-interaction hold expires.
          s.timer = setTimeout(() => { s.timer = 0; request(); }, Math.max(80, s.idleHold - now));
        }
      };
      function request() {
        if (s.dead) return;
        if (s.timer) {
          clearTimeout(s.timer);
          s.timer = 0;
        }
        if (!s.raf) s.raf = requestAnimationFrame(tick);
      }
      const hold = () => (s.idleHold = performance.now() + 5000);

      // --- Input ------------------------------------------------------------
      const onDown = (e) => {
        s.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
        if (s.pointers.size === 2) {
          const [p, q] = [...s.pointers.values()];
          s.pinch0 = Math.hypot(p.x - q.x, p.y - q.y);
          s.pinchDist = s.targetDist;
          return;
        }
        s.dragging = true;
        s.lastX = e.clientX;
        s.lastY = e.clientY;
        s.vy = s.vp = 0;
        hold();
        el.classList.add("grabbing");
        canvas.setPointerCapture?.(e.pointerId);
        request();
      };
      const onMove = (e) => {
        if (!s.pointers.has(e.pointerId)) return;
        s.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
        if (s.pointers.size === 2 && s.pinch0) {
          const [p, q] = [...s.pointers.values()];
          const d = Math.hypot(p.x - q.x, p.y - q.y);
          if (d > 0) s.targetDist = Math.max(DIST.min, Math.min(DIST.max, (s.pinchDist * s.pinch0) / d));
          request();
          return;
        }
        if (!s.dragging) return;
        const k = 2.6 / Math.max(240, el.clientWidth);
        const dx = (e.clientX - s.lastX) * k * (s.dist / DIST.start);
        const dy = (e.clientY - s.lastY) * k * (s.dist / DIST.start);
        s.yaw += dx;
        s.pitch = Math.max(-1, Math.min(1, s.pitch + dy));
        s.vy = dx;
        s.vp = dy;
        s.lastX = e.clientX;
        s.lastY = e.clientY;
        hold();
        request();
      };
      const onUp = (e) => {
        s.pointers.delete(e.pointerId);
        if (s.pointers.size < 2) s.pinch0 = 0;
        if (s.pointers.size === 1) {
          // Continue rotating from the remaining finger without a jump.
          const [p] = [...s.pointers.values()];
          s.lastX = p.x;
          s.lastY = p.y;
        }
        if (s.pointers.size === 0) {
          s.dragging = false;
          el.classList.remove("grabbing");
          if (reduced()) s.vy = s.vp = 0;
          hold();
          request();
        }
      };
      const onWheel = (e) => {
        if (!e.ctrlKey) return; // plain wheel scrolls the page
        e.preventDefault();
        s.targetDist = Math.max(DIST.min, Math.min(DIST.max, s.targetDist + e.deltaY * 0.004));
        hold();
        request();
      };
      const onKey = (e) => {
        const step = 0.12;
        const map = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
        if (map[e.key]) {
          e.preventDefault();
          s.yaw += map[e.key][0];
          s.pitch = Math.max(-1, Math.min(1, s.pitch + map[e.key][1]));
          hold();
          request();
        }
      };
      canvas.addEventListener("pointerdown", onDown);
      window.addEventListener("pointermove", onMove);
      window.addEventListener("pointerup", onUp);
      window.addEventListener("pointercancel", onUp);
      canvas.addEventListener("wheel", onWheel, { passive: false });
      el.addEventListener("keydown", onKey);

      api.current = {
        zoom: (dir) => {
          s.targetDist = Math.max(DIST.min, Math.min(DIST.max, s.targetDist - dir * 0.45));
          hold();
          request();
        },
        reset: () => {
          s.yaw = START_YAW;
          s.pitch = START_PITCH;
          s.vy = s.vp = 0;
          s.targetDist = DIST.start;
          hold();
          request();
        },
      };

      const io = new IntersectionObserver(([entry]) => {
        s.visible = entry.isIntersecting;
        if (s.visible) request();
      });
      io.observe(el);
      const onVis = () => !document.hidden && request();
      document.addEventListener("visibilitychange", onVis);
      const ro = new ResizeObserver(resize);
      ro.observe(el);
      const unTheme = subscribeTheme(applyTheme);

      el.appendChild(canvas);
      resize();
      applyTheme();
      draw();
      setState("ready");

      cleanup = () => {
        // Stop every pending frame and idle timer first: a late frame must
        // never draw into a disposed renderer or a released context.
        s.dead = true;
        cancelAnimationFrame(s.raf);
        clearTimeout(s.timer);
        io.disconnect();
        ro.disconnect();
        unTheme();
        document.removeEventListener("visibilitychange", onVis);
        canvas.removeEventListener("pointerdown", onDown);
        window.removeEventListener("pointermove", onMove);
        window.removeEventListener("pointerup", onUp);
        window.removeEventListener("pointercancel", onUp);
        canvas.removeEventListener("wheel", onWheel);
        el.removeEventListener("keydown", onKey);
        [sphere, cloudMesh.geometry, atmoMesh.geometry].forEach((g) => g.dispose());
        [earthMat, cloudMat, atmoMat].forEach((m) => m.dispose());
        [day, night, clouds, black].forEach((t) => t?.dispose());
        arcObjs.forEach((o) => {
          o.geometry?.dispose();
          o.material?.dispose();
        });
        release();
        canvas.remove();
      };
    })();

    return () => {
      disposed = true;
      cleanup();
    };
  }, [arcs]);

  // Interactive globe is a labelled group (so its buttons stay reachable);
  // the static fallback is just an image.
  return (
    <div
      ref={host}
      className={`earth ${compact ? "compact" : ""} ${className}`}
      data-state={state}
      role={state === "fallback" ? "img" : "group"}
      aria-roledescription={state === "ready" ? "interactive globe" : undefined}
      aria-label={state === "ready" ? `${label}. Drag or use the arrow keys to turn it.` : label}
      tabIndex={state === "ready" ? 0 : undefined}
    >
      <div className="earth-fallback" aria-hidden="true">
        <span className="earth-fallback-map" />
      </div>
      {state === "ready" && (
        <div className="earth-controls">
          <button type="button" onClick={() => api.current.zoom?.(1)} aria-label="Zoom in">+</button>
          <button type="button" onClick={() => api.current.zoom?.(-1)} aria-label="Zoom out">−</button>
          <button type="button" onClick={() => api.current.reset?.()} aria-label="Reset view">Reset</button>
        </div>
      )}
    </div>
  );
}
