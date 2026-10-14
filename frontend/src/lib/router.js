import { useEffect, useState } from "react";

// Minimal hash router: "#/session/12" -> { name: "session", id: "12", query: {} }
// and "#/verify-email?token=abc" -> { name: "verify-email", query: { token: "abc" } }.
// Hash routes survive a refresh without any server configuration.
function parse(hash) {
  const raw = hash.replace(/^#\/?/, "");
  const [path, search = ""] = raw.split("?");
  const parts = path.split("/").filter(Boolean);
  return {
    name: parts[0] || "dashboard",
    id: parts[1] || null,
    query: Object.fromEntries(new URLSearchParams(search)),
  };
}

export function useRoute() {
  const [route, setRoute] = useState(() => parse(window.location.hash));
  useEffect(() => {
    const onChange = () => {
      setRoute(parse(window.location.hash));
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export function navigate(name, id, query) {
  const qs = query ? `?${new URLSearchParams(query)}` : "";
  window.location.hash = (id != null ? `/${name}/${id}` : `/${name}`) + qs;
}

export function pct(value) {
  return value == null ? "—" : `${Math.round(value * 100)}%`;
}

export function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const days = Math.floor((Date.now() - d.getTime()) / 86400000);
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

const ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"];
export function roman(n) {
  return ROMAN[n] || String(n);
}

export const STATUS_LABELS = {
  strong: "Strong",
  developing: "Developing",
  weak: "Needs review",
  needs_review: "Needs review",
  not_covered: "Not yet covered",
  mastered: "Mastered",
  in_progress: "In progress",
  not_started: "Not started",
};
