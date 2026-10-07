import { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import { Icon } from "./components/ui.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Topics from "./pages/Topics.jsx";
import Session from "./pages/Session.jsx";
import Report from "./pages/Report.jsx";
import LearningProgress from "./pages/LearningProgress.jsx";
import About from "./pages/About.jsx";
import { api } from "./api.js";
import { navigate, useRoute } from "./lib/router.js";

export default function App() {
  const route = useRoute();
  const [menuOpen, setMenuOpen] = useState(false);
  const [active, setActive] = useState(null);
  const activeSessionId = active?.id ?? null;

  // Keep the sidebar's "session in progress" indicator current.
  useEffect(() => {
    api
      .teacherProgress()
      .then((p) => setActive(p.active_session ?? null))
      .catch(() => {});
  }, [route.name, route.id]);

  let page;
  switch (route.name) {
    case "topics":
      page = <Topics active={active} />;
      break;
    case "session":
      page = route.id ? <Session key={route.id} id={route.id} /> : <Topics active={active} />;
      break;
    case "report":
      page = <Report key={route.id} id={route.id} />;
      break;
    case "progress":
      page = <LearningProgress />;
      break;
    case "about":
      page = <About />;
      break;
    default:
      page = <Dashboard />;
  }

  return (
    <div className="shell">
      <Sidebar
        active={route.name}
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        activeSessionId={activeSessionId}
      />
      <div className="main">
        <div className="mobile-bar">
          <button className="icon-btn" onClick={() => setMenuOpen(true)} aria-label="Open navigation">
            <Icon name="menu" />
          </button>
          <button className="mobile-brand" onClick={() => navigate("dashboard")}>
            SkillForge
          </button>
        </div>
        <main className="content">
          <div className="page" key={`${route.name}/${route.id ?? ""}`}>
            {page}
          </div>
        </main>
      </div>
    </div>
  );
}
