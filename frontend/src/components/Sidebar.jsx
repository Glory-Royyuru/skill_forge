import { Icon } from "./ui.jsx";
import { navigate } from "../lib/router.js";

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: "home" },
  { id: "topics", label: "Curriculum", icon: "book" },
  { id: "session", label: "Teacher Session", icon: "teacher" },
  { id: "progress", label: "Progress", icon: "chart" },
  { id: "about", label: "How It Works", icon: "info" },
];

export default function Sidebar({ active, open, onClose, activeSessionId }) {
  const go = (id) => {
    if (id === "session") {
      if (activeSessionId) navigate("session", activeSessionId);
      else navigate("topics");
    } else {
      navigate(id);
    }
    onClose?.();
  };
  const current = active === "report" ? "progress" : active;
  return (
    <>
      <div className={`sidebar-scrim ${open ? "open" : ""}`} onClick={onClose} />
      <nav className={`sidebar ${open ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">SF</div>
          <div>
            <div className="brand-name">SkillForge</div>
            <div className="brand-sub">Adaptive Teacher</div>
          </div>
        </div>
        <div className="nav-label">Learn</div>
        <ul className="nav">
          {NAV_ITEMS.map((item) => (
            <li key={item.id}>
              <button className={`nav-link ${current === item.id ? "active" : ""}`} onClick={() => go(item.id)}>
                <Icon name={item.icon} />
                <span>{item.label}</span>
                {item.id === "session" && activeSessionId && <span className="nav-dot" title="Session in progress" />}
              </button>
            </li>
          ))}
        </ul>
        <div className="sidebar-foot">
          <div className="profile">
            <div className="avatar">DS</div>
            <div>
              <div className="profile-name">Demo Student</div>
              <div className="profile-sub">Local profile</div>
            </div>
          </div>
        </div>
      </nav>
    </>
  );
}
