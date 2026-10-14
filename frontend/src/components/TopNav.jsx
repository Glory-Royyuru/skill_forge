import { useEffect, useRef, useState } from "react";
import { Icon } from "./ui.jsx";
import { navigate } from "../lib/router.js";
import { withViewTransition } from "./motion.jsx";
import { cycleTheme, getThemePreference, subscribeTheme } from "../lib/theme.js";

// Primary areas at the top of every page (Profile lives in the account menu). Everything else (Teacher
// sessions, reports, diagnostic, flashcards, Rapid Round, timetable, the
// Performance Review) lives inside one of them.
export const NAV_ITEMS = [
  { id: "dashboard", label: "Home", icon: "home" },
  { id: "learn", label: "Learn", icon: "layers", also: ["topics", "session", "report", "diagnostic"] },
  { id: "practice", label: "Practice", icon: "target" },
  { id: "progress", label: "Progress", icon: "chart" },
  { id: "calendar", label: "Calendar", icon: "calendar", also: ["timetable"] },
  { id: "review", label: "PTM", icon: "report" },
  { id: "profile", label: "Profile", icon: "teacher", also: ["about"], top: false },
];

export function currentArea(route) {
  return NAV_ITEMS.find((i) => i.id === route || i.also?.includes(route))?.id;
}

function initials(name) {
  if (!name) return "SF";
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] || "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

// Closes a popover on outside click or Escape.
function useDismiss(open, setOpen, ref) {
  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false);
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, setOpen, ref]);
}

export default function TopNav({ active, activeSessionId, user, mode, onSignOut }) {
  const [menu, setMenu] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [themeMode, setThemeMode] = useState(getThemePreference());
  const menuRef = useRef(null);
  const drawerRef = useRef(null);

  useDismiss(menu, setMenu, menuRef);
  useDismiss(drawer, setDrawer, drawerRef);

  useEffect(() => {
    return subscribeTheme(({ preference }) => setThemeMode(preference));
  }, []);

  useEffect(() => {
    setMenu(false);
    setDrawer(false);
  }, [active]);

  const current = currentArea(active);

  const go = (id, q) => {
    withViewTransition(() => navigate(id, null, q));
    setMenu(false);
    setDrawer(false);
  };

  const handleToggleTheme = () => {
    const next = cycleTheme();
    setThemeMode(next);
  };

  const themeIcon = themeMode === "dark" ? "moon" : themeMode === "light" ? "sun" : "laptop";
  const themeName = themeMode === "dark" ? "Dark" : themeMode === "light" ? "Light" : "System";
  const themeLabel = themeMode === "dark" ? "Dark theme (click for Light)" : themeMode === "light" ? "Light theme (click for System)" : "System theme (click for Dark)";

  const account = (
    <>
      <div className="acct-id">
        <div className="acct-name">{user?.name || "Student"}</div>
        <div className="acct-sub">{user?.student_id || user?.email || ""}</div>
      </div>
      <button className="acct-item" onClick={() => go("profile")}>
        <Icon name="teacher" size={15} /> Profile &amp; settings
      </button>
      <button className="acct-item" onClick={() => go("review")}>
        <Icon name="report" size={15} /> Performance Review
      </button>
      <button className="acct-item" onClick={() => go("about")}>
        <Icon name="info" size={15} /> How it works
      </button>
      <button className="acct-item" onClick={handleToggleTheme}>
        <Icon name={themeIcon} size={15} /> Theme: {themeName}
      </button>
      <button className="acct-item signout" onClick={onSignOut}>
        <Icon name="logout" size={15} /> Sign out
      </button>
    </>
  );

  return (
    <header className="topnav">
      <div className="topnav-inner">
        <button className="topnav-brand" onClick={() => go("dashboard")} aria-label="SkillForge home">
          <span className="lbrand-mark" aria-hidden="true">
            SF
          </span>
          <span className="topnav-name">SkillForge</span>
        </button>

        <nav className="topnav-links" aria-label="Main navigation">
          {NAV_ITEMS.filter((item) => item.top !== false).map((item) => (
            <button
              key={item.id}
              className={`nav-link ${current === item.id ? "active" : ""}`}
              aria-current={current === item.id ? "page" : undefined}
              onClick={() => go(item.id)}
            >
              <span>{item.label}</span>
              {item.id === "learn" && activeSessionId && <span className="nav-dot" title="Session in progress" />}
            </button>
          ))}
        </nav>

        <div className="topnav-right">
          {mode === "ptm" && (
            <button className="mode-badge" onClick={() => go("review")} title="Open the Performance Review">
              PTM mode
            </button>
          )}

          {activeSessionId && (
            <button
              className="resume-link"
              onClick={() => (navigate("session", activeSessionId), setDrawer(false))}
              title="Resume your active learning session"
            >
              <span className="live-dot" />
              <span className="resume-text">Resume session</span>
            </button>
          )}

          <button
            className="theme-toggle-btn"
            onClick={handleToggleTheme}
            title={themeLabel}
            aria-label={`Theme: ${themeName}. Click to change.`}
          >
            <Icon name={themeIcon} size={16} />
          </button>

          <div className="acct" ref={menuRef}>
            <button
              className="avatar-btn"
              aria-haspopup="true"
              aria-expanded={menu}
              aria-label={`Account menu for ${user?.name || "user"}`}
              onClick={() => setMenu((m) => !m)}
            >
              <span className="avatar">{initials(user?.name)}</span>
            </button>
            {menu && <div className="acct-menu">{account}</div>}
          </div>

          <div className="drawer-wrap" ref={drawerRef}>
            <button
              className="menu-btn"
              aria-label="Open navigation menu"
              aria-expanded={drawer}
              onClick={() => setDrawer((d) => !d)}
            >
              <Icon name={drawer ? "x" : "menu"} size={20} />
            </button>
            {drawer && (
              <div className="drawer" role="dialog" aria-label="Mobile Navigation">
                <nav aria-label="Main (mobile)">
                  {NAV_ITEMS.map((item) => (
                    <button
                      key={item.id}
                      className={`drawer-link ${current === item.id ? "active" : ""}`}
                      aria-current={current === item.id ? "page" : undefined}
                      onClick={() => go(item.id)}
                    >
                      <Icon name={item.icon} size={18} /> {item.label}
                    </button>
                  ))}
                </nav>
                <div className="drawer-acct">{account}</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
