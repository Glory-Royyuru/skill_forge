import { useCallback, useEffect, useState } from "react";
import TopNav from "./components/TopNav.jsx";
import SeasonalLayer from "./components/SeasonalLayer.jsx";
import Starfield from "./components/Starfield.jsx";
import { Loading } from "./components/ui.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Topics from "./pages/Topics.jsx";
import Session from "./pages/Session.jsx";
import Report from "./pages/Report.jsx";
import LearningProgress from "./pages/LearningProgress.jsx";
import PracticeHub from "./pages/PracticeHub.jsx";
import Diagnostic from "./pages/Diagnostic.jsx";
import Calendar from "./pages/Calendar.jsx";
import Profile from "./pages/Profile.jsx";
import Landing from "./pages/Landing.jsx";
import About from "./pages/About.jsx";
import Review from "./pages/Review.jsx";
import {
  AUTH_ROUTES,
  AuthShell,
  CheckEmail,
  ForgotPassword,
  Login,
  ResetPassword,
  Signup,
  VerifyEmail,
} from "./pages/Auth.jsx";
import { withViewTransition } from "./components/motion.jsx";
import { usePauseWhenHidden } from "./components/world.jsx";
import { api, setUnauthorizedHandler } from "./api.js";
import { resolveTheme } from "./lib/theme.js";
import { navigate, useRoute } from "./lib/router.js";

// Pages reachable without signing in. Verification and reset links work
// whether or not someone is signed in on this browser.
const PUBLIC = new Set(["welcome", "login", "signup", "check-email", "verify-email", "forgot-password", "reset-password"]);
const SIGNED_OUT_ONLY = new Set(["welcome", "login", "signup", "check-email", "forgot-password"]);

// How present the night sky is on each page (see styles/sky.css): fully on the
// landing and sign-in pages, quieter on working pages, and quietest (no
// shooting stars) while answering questions.
function skyMode(route, signedIn) {
  if (!signedIn || PUBLIC.has(route.name)) return "open";
  if (["session", "diagnostic", "report"].includes(route.name)) return "focus";
  if (route.name === "practice" && ["flashcards", "rapid"].includes(route.query?.tab)) return "focus";
  return "calm";
}

// The sky is mounted once, at the same place in every branch below, so it
// survives sign-in, sign-out and every route change without restarting.
function WithSky({ children }) {
  return (
    <>
      <Starfield />
      {children}
    </>
  );
}

export default function App() {
  const route = useRoute();
  usePauseWhenHidden();
  const [user, setUser] = useState(undefined); // undefined = checking, null = signed out
  const [prefs, setPrefs] = useState({ mode: "student", theme: "auto" });
  const [active, setActive] = useState(null);

  useEffect(() => {
    api
      .me()
      .then((r) => setUser(r.user))
      .catch(() => setUser(null));
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));
    return () => setUnauthorizedHandler(null);
  }, []);

  useEffect(() => {
    if (!user) return;
    api.profile().then((p) => setPrefs(p.preferences)).catch(() => {});
  }, [user]);

  // Keep the "session in progress" indicator current.
  useEffect(() => {
    if (!user) return;
    api
      .teacherProgress()
      .then((p) => setActive(p.active_session ?? null))
      .catch(() => {});
  }, [user, route.name, route.id]);

  // Route guards. Read the live hash: a navigation that has just been
  // requested (e.g. sign-out → sign-in) must not be overridden by a stale route.
  useEffect(() => {
    const live = window.location.hash.replace(/^#\/?/, "").split(/[/?]/)[0] || "dashboard";
    if (user === null && !PUBLIC.has(live)) navigate("welcome");
    if (user && SIGNED_OUT_ONLY.has(route.name)) navigate("dashboard");
    if (user && route.name === "timetable") navigate("profile", null, { tab: "timetable" });
  }, [user, route.name]);

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
      setActive(null);
      navigate("login");
    }
  }, []);

  const season = resolveTheme(user ? prefs.theme : "auto");
  const sky = skyMode(route, !!user);
  useEffect(() => {
    document.documentElement.dataset.sky = sky;
  }, [sky]);

  if (user === undefined) return <WithSky><Loading label="Loading SkillForge…" /></WithSky>;

  if (!user || PUBLIC.has(route.name)) {
    let page;
    switch (route.name) {
      case "signup":
        page = <Signup />;
        break;
      case "check-email":
        page = <CheckEmail query={route.query} />;
        break;
      case "verify-email":
        page = <VerifyEmail query={route.query} />;
        break;
      case "forgot-password":
        page = <ForgotPassword />;
        break;
      case "reset-password":
        page = <ResetPassword query={route.query} />;
        break;
      case "login":
        page = (
          <Login
            query={route.query}
            onSignedIn={(u) =>
              withViewTransition(() => {
                setUser(u);
                navigate("dashboard");
              })
            }
          />
        );
        break;
      default:
        page = <Landing />;
    }
    return (
      <WithSky>
        <SeasonalLayer season={season} />
        {AUTH_ROUTES.has(route.name) ? <AuthShell route={route.name}>{page}</AuthShell> : page}
      </WithSky>
    );
  }

  let page;
  switch (route.name) {
    case "learn":
    case "topics":
      page = <Topics active={active} query={route.query} />;
      break;
    case "session":
      page = route.id ? <Session key={route.id} id={route.id} /> : <Topics active={active} query={route.query} />;
      break;
    case "report":
      page = <Report key={route.id} id={route.id} />;
      break;
    case "practice":
      page = <PracticeHub query={route.query} />;
      break;
    case "diagnostic":
      page = <Diagnostic />;
      break;
    case "progress":
      page = <LearningProgress query={route.query} mode={prefs.mode} />;
      break;
    case "calendar":
      page = <Calendar />;
      break;
    case "profile":
      page = <Profile user={user} query={route.query} onPrefs={setPrefs} />;
      break;
    case "about":
      page = <About />;
      break;
    case "review":
      page = <Review />;
      break;
    default:
      page = <Dashboard user={user} />;
  }

  return (
    <WithSky>
      <div className={`shell ${prefs.mode === "ptm" ? "mode-ptm" : ""}`}>
        <SeasonalLayer season={season} />
        <TopNav
          active={route.name}
          activeSessionId={active?.id ?? null}
          user={user}
          mode={prefs.mode}
          onSignOut={signOut}
        />
        <div className="main">
          <main className="content" id="main">
            <div className="page" key={`${route.name}/${route.id ?? ""}`}>
              {page}
            </div>
          </main>
        </div>
      </div>
    </WithSky>
  );
}
