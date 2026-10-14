// Theme management: True Light / Dark / Auto modes with system preference detection,
// localStorage persistence, and seasonal presentation layers.

export const SEASONS = {
  christmas: { label: "Christmas" },
  diwali: { label: "Diwali" },
  halloween: { label: "Halloween" },
  newyear: { label: "New Year" },
};

// Diwali follows the lunar calendar; dates (Lakshmi Puja) for the coming years.
const DIWALI = { 2025: "10-20", 2026: "11-08", 2027: "10-29", 2028: "10-17", 2029: "11-05", 2030: "10-26" };

function within(date, month, day, before, after) {
  const target = new Date(date.getFullYear(), month - 1, day);
  const diff = (date - target) / 86400000;
  return diff >= -before && diff <= after;
}

export function seasonFor(date = new Date()) {
  const m = date.getMonth() + 1;
  const d = date.getDate();
  const diwali = DIWALI[date.getFullYear()];
  if (diwali) {
    const [dm, dd] = diwali.split("-").map(Number);
    if (within(date, dm, dd, 3, 2)) return "diwali";
  }
  if ((m === 12 && d >= 30) || (m === 1 && d <= 2)) return "newyear";
  if (m === 12 && d >= 15 && d <= 28) return "christmas";
  if ((m === 10 && d >= 24) || (m === 11 && d === 1)) return "halloween";
  return null;
}

export function resolveTheme(preference, date = new Date()) {
  if (!preference || preference === "none") return null;
  if (preference === "auto") return seasonFor(date);
  return SEASONS[preference] ? preference : null;
}

// Color mode (light / dark / auto)
const THEME_STORAGE_KEY = "sf_theme_mode";
const THEME_LISTENERS = new Set();

export function getSystemTheme() {
  if (typeof window === "undefined" || !window.matchMedia) return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function getThemePreference() {
  if (typeof window === "undefined") return "auto";
  try {
    const v = localStorage.getItem(THEME_STORAGE_KEY);
    return v === "light" || v === "dark" ? v : "auto";
  } catch {
    return "auto";
  }
}

export function getEffectiveTheme() {
  const pref = getThemePreference();
  if (pref === "dark") return "dark";
  if (pref === "light") return "light";
  return getSystemTheme();
}

export function applyTheme(mode) {
  const requested = mode || getThemePreference();
  // Unknown or corrupted stored values fall back to following the system.
  const target = requested === "light" || requested === "dark" ? requested : "auto";
  const effective = target === "auto" ? getSystemTheme() : target;
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-theme", effective);
    document.documentElement.setAttribute("data-theme-pref", target);
    document.documentElement.style.colorScheme = effective;
  }
  THEME_LISTENERS.forEach((cb) => cb({ preference: target, effective }));
}

export function setThemePreference(mode) {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, mode);
  } catch {
    // ignore
  }
  applyTheme(mode);
}

export function cycleTheme() {
  const current = getThemePreference();
  const next = current === "auto" ? "dark" : current === "dark" ? "light" : "auto";
  setThemePreference(next);
  return next;
}

export function subscribeTheme(callback) {
  THEME_LISTENERS.add(callback);
  return () => THEME_LISTENERS.delete(callback);
}

// Initial setup on module load
if (typeof window !== "undefined") {
  applyTheme();
  if (window.matchMedia) {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      if (getThemePreference() === "auto") applyTheme("auto");
    };
    if (media.addEventListener) {
      media.addEventListener("change", handler);
    } else if (media.addListener) {
      media.addListener(handler);
    }
  }
}
