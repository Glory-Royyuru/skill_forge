// Shared motion primitives. One timing language (see --dur-* / --ease-* in
// index.css): major motion = the book, medium = sections and pages, micro =
// controls. Everything here degrades to static content when the user prefers
// reduced motion, and nothing hides content from assistive technology.
import { Children, cloneElement, isValidElement, useEffect, useRef, useState } from "react";
import { navigate } from "../lib/router.js";

const query = "(prefers-reduced-motion: reduce)";

export function prefersReducedMotion() {
  return typeof window !== "undefined" && !!window.matchMedia?.(query).matches;
}

export function useReducedMotion() {
  const [reduced, setReduced] = useState(prefersReducedMotion);
  useEffect(() => {
    const mq = window.matchMedia?.(query);
    if (!mq) return undefined;
    const on = () => setReduced(mq.matches);
    mq.addEventListener?.("change", on);
    return () => mq.removeEventListener?.("change", on);
  }, []);
  return reduced;
}

// True once the element has scrolled into view (and stays true).
export function useInView(ref, { threshold = 0.18, rootMargin = "0px" } = {}) {
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || seen) return undefined;
    if (!("IntersectionObserver" in window)) {
      setSeen(true);
      return undefined;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setSeen(true);
          io.disconnect();
        }
      },
      { threshold, rootMargin }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [ref, seen, threshold, rootMargin]);
  return seen;
}

// Fades/slides its children in when scrolled into view.
export function Reveal({ as: Tag = "div", className = "", delay = 0, children, ...rest }) {
  const ref = useRef(null);
  const seen = useInView(ref);
  return (
    <Tag ref={ref} className={`reveal ${seen ? "in" : ""} ${className}`} style={{ "--delay": `${delay}ms` }} {...rest}>
      {children}
    </Tag>
  );
}

// Gives each child an index (--i) so CSS can stagger entrances.
export function Stagger({ children, step = 60, start = 0 }) {
  let i = 0;
  return Children.map(children, (child) => {
    if (!isValidElement(child)) return child;
    const n = i++;
    return cloneElement(child, {
      style: { ...(child.props.style || {}), "--stagger": `${start + n * step}ms` },
    });
  });
}

// Pointer-reactive tilt: writes --tx/--ty in [-1, 1] on the element (rAF
// throttled). target "window" follows the pointer anywhere on the page;
// "self" only while over the element. Off for touch-only devices.
export function usePointerTilt(ref, target) {
  useEffect(() => {
    const el = ref.current;
    if (!el || !target || window.matchMedia?.("(hover: none)").matches) return undefined;
    let raf = 0;
    let px = 0;
    let py = 0;
    const apply = () => {
      raf = 0;
      el.style.setProperty("--tx", px.toFixed(3));
      el.style.setProperty("--ty", py.toFixed(3));
    };
    const onMove = (e) => {
      const r = target === "self" ? el.getBoundingClientRect() : { left: 0, top: 0, width: innerWidth, height: innerHeight };
      px = Math.max(-1, Math.min(1, ((e.clientX - r.left) / r.width - 0.5) * 2));
      py = Math.max(-1, Math.min(1, ((e.clientY - r.top) / r.height - 0.5) * 2));
      if (!raf) raf = requestAnimationFrame(apply);
    };
    const onLeave = () => {
      px = 0;
      py = 0;
      if (!raf) raf = requestAnimationFrame(apply);
    };
    const host = target === "self" ? el : window;
    host.addEventListener("pointermove", onMove, { passive: true });
    (target === "self" ? el : document).addEventListener("pointerleave", onLeave);
    return () => {
      host.removeEventListener("pointermove", onMove);
      (target === "self" ? el : document).removeEventListener("pointerleave", onLeave);
      cancelAnimationFrame(raf);
    };
  }, [ref, target]);
}

// Navigate with a cross-document-style View Transition where supported, so
// shared elements (e.g. the book) morph between pages. Falls back to a plain
// navigation, and never animates for reduced-motion users.
export function transitionTo(name, id, query) {
  withViewTransition(() => navigate(name, id, query));
}

// Runs `change` (which ends in a hash navigation) inside a View Transition,
// letting React render the new route before the browser snapshots it.
export function withViewTransition(change) {
  if (!document.startViewTransition || prefersReducedMotion()) {
    change();
    return;
  }
  document.startViewTransition(
    () =>
      new Promise((resolve) => {
        const done = () => requestAnimationFrame(() => requestAnimationFrame(resolve));
        window.addEventListener("hashchange", done, { once: true });
        change();
        setTimeout(resolve, 600); // never hold the page hostage
      })
  );
}
