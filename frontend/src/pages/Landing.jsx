import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import Earth from "../components/Earth.jsx";
import { transitionTo } from "../components/motion.jsx";
import { Icon } from "../components/ui.jsx";
import { PathTrail, curve } from "../components/world.jsx";
import { AREAS, ROADMAP, placeOf } from "../lib/catalog.js";

// Landing: one strong composition (headline + Earth), then a short editorial
// story that scrolls normally. Only the Earth moves; everything else is still.
// Every statement describes the product as it is; counts come from the API.

const STEPS = ["Diagnose", "Teach", "Assess", "Adapt", "Report"];
const GRID_A = "mmlmrlmmllnnmlrlmmll";
const GRID_B = "llnmmmrrlnmmlllmnnrm";

function Section({ id, n, kicker, title, children, figure, flip = false }) {
  return (
    <section className={`lsx${flip ? " lsx-alt" : ""}`} id={id} aria-labelledby={`${id}-h`}>
      <div className="lsx-text">
        <span className="lsx-n">{n}</span>
        <span className="kicker">{kicker}</span>
        <h2 className="display lsx-title" id={`${id}-h`}>{title}</h2>
        {children}
      </div>
      <div className="lsx-figure">{figure}</div>
    </section>
  );
}

function Grid({ who, cells }) {
  return (
    <div className="lgrid">
      <span className="lgrid-who">{who}</span>
      <span className="lgrid-cells">
        {[...cells].map((c, i) => <i key={i} className={`gc gc-${c}`} />)}
      </span>
    </div>
  );
}

export default function Landing() {
  const [catalog, setCatalog] = useState(null);
  useEffect(() => {
    api.curriculum().then(setCatalog).catch(() => setCatalog(null));
  }, []);

  const counts = useMemo(() => {
    const out = {};
    AREAS.forEach((a) => (out[a.id] = { banked: 0, subjects: 0, roadmap: ROADMAP.filter((r) => r.area === a.id).length }));
    (catalog?.subjects || []).forEach((s) => {
      const area = placeOf(s).area;
      out[area].banked += s.assessable_topics;
      out[area].subjects += 1;
    });
    return out;
  }, [catalog]);

  const howItWorks = () => document.getElementById("adapts")?.scrollIntoView({ behavior: "smooth" });

  return (
    <div className="lw">
      <header className="lw-nav">
        <button className="lw-brand" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })} aria-label="SkillForge home">
          <span className="lw-mark" aria-hidden="true">SF</span>
          <span>SkillForge</span>
        </button>
        <nav className="lw-nav-actions" aria-label="Account">
          <button className="btn btn-ghost btn-sm" onClick={() => transitionTo("login")}>Sign in</button>
          <button className="btn btn-accent btn-sm" onClick={() => transitionTo("signup")}>Start learning</button>
        </nav>
      </header>

      {/* 1 — A world connected by knowledge */}
      <section className="lw-hero" aria-labelledby="hero-h">
        <div className="lw-hero-text">
          <span className="kicker">Adaptive learning · SkillForge</span>
          <h1 className="display lw-headline" id="hero-h">Knowledge has no borders.</h1>
          <p className="lw-lede">Build understanding, discover your strengths, and find your next step in learning.</p>
          <div className="lw-cta">
            <button className="btn btn-accent btn-lg" onClick={() => transitionTo("signup")}>
              Start learning <Icon name="arrowRight" size={16} />
            </button>
            <button className="btn btn-secondary btn-lg" onClick={howItWorks}>Explore how it works</button>
          </div>
          <p className="lw-fine">
            Free to use. Deterministic learner intelligence with a Bayesian Knowledge Tracing baseline. No trained model,
            and no invented statistics.
          </p>
        </div>
        <div className="lw-hero-earth">
          <Earth />
          <p className="lw-earth-note">
            <span className="when-live">Drag to turn the Earth. The arcs are symbolic, not data. </span>
            Imagery: NASA Blue Marble.
          </p>
        </div>
      </section>

      {/* 2 — Learning that adapts */}
      <Section id="adapts" n="01" kicker="Adaptive" title="Learning that adapts to you."
        figure={
          <svg viewBox="0 0 520 300" className="lw-diagram" role="img" aria-label="Different routes to the same idea">
            <PathTrail d={curve([40, 250], [250, 170], -0.25)} tone="ink" />
            <PathTrail d={curve([250, 170], [470, 60], -0.2)} tone="blue" />
            <PathTrail d={curve([250, 170], [470, 250], 0.2)} tone="orange" />
            <PathTrail d={curve([250, 170], [150, 60], 0.3)} tone="teal" dashed />
            {[[40, 250, "You"], [250, 170, "A concept"], [150, 60, "Step back"], [470, 60, "Go deeper"], [470, 250, "Practise"]].map(([x, y, l]) => (
              <g key={l} transform={`translate(${x} ${y})`} className="lw-stop"><circle r="8" /><text y="-16" textAnchor="middle">{l}</text></g>
            ))}
          </svg>
        }>
        <p>
          A correct answer leads one level deeper; a wrong one brings an explanation and a simpler question on the same
          idea. Two students on the same topic rarely take the same route, and they don&apos;t have to.
        </p>
      </Section>

      {/* 3 — Discovering what you know */}
      <Section id="discover" n="02" kicker="Starting point" title="Discover what you already know." flip
        figure={
          <div className="lw-grids">
            <Grid who="Student A" cells={GRID_A} />
            <Grid who="Student B" cells={GRID_B} />
            <p className="lw-legend"><em>Illustration.</em> <i className="gc gc-m" /> mastered <i className="gc gc-l" /> learning <i className="gc gc-r" /> needs review <i className="gc gc-n" /> not started</p>
          </div>
        }>
        <p>
          A short diagnostic asks one question from each subject that has a question bank. It sets a starting point for
          every concept separately and can never mark anything as mastered on its own.
        </p>
      </Section>

      {/* 4 — Strengthening weak concepts */}
      <Section id="strengthen" n="03" kicker="Evidence" title="Weak concepts come back until they hold."
        figure={
          <ol className="lw-rules">
            <li><span className="rule-tag learning">Learning</span>Some evidence, not enough to decide either way.</li>
            <li><span className="rule-tag review">Needs review</span>Two misses in a row, two of the last four, or a low estimate backed by several answers.</li>
            <li><span className="rule-tag mastered">Mastered</span>A high estimate, several answers, recent accuracy of two in three, and a correct answer at Intermediate or harder.</li>
          </ol>
        }>
        <p>
          One correct answer is never mastery, and one slip is never a weakness. Concepts that need review return in
          practice and flashcards; secure ones make room for new topics.
        </p>
      </Section>

      {/* 5 — Practising with the Teacher Agent */}
      <Section id="teacher" n="04" kicker="Teacher Agent" title="Practise with a teacher that explains." flip
        figure={
          <div className="lw-teacher">
            <ol className="lw-steps">{STEPS.map((s, i) => <li key={s}><span>{i + 1}</span>{s}</li>)}</ol>
            <div className="lw-note">
              <div><span className="lw-note-k">Your answer</span><s>B · Underfitting</s></div>
              <div><span className="lw-note-k">Correct answer</span>D · Overfitting</div>
              <div><span className="lw-note-k">Why</span>Good on training data, poor on new data is the definition of overfitting.</div>
              <div><span className="lw-note-k">Next</span>A simpler question on the same idea, then a curated reading link.</div>
              <span className="lw-note-tag">An actual question from the Machine Learning bank</span>
            </div>
          </div>
        }>
        <p>
          Each session runs Diagnose → Teach → Assess → Adapt → Report. A wrong answer shows your answer, the correct
          one, why, what to remember, and, where a trustworthy source exists, where to read more.
        </p>
      </Section>

      {/* 6 — Three measures */}
      <Section id="measures" n="05" kicker="Honest progress" title="Activity, assessment and mastery stay separate."
        figure={
          <div className="lw-measures">
            {[["Activity", "How much you practised", "gold"], ["Assessment", "How a sitting went", "orange"], ["Mastery", "What you know, per concept", "blue"]].map(([t, d, tone], i) => (
              <div key={t} className={`lw-measure tone-${tone}`}>
                <strong className="display">{t}</strong>
                <span>{d}</span>
                {i < 2 && <span className="lw-neq" aria-hidden="true">≠</span>}
              </div>
            ))}
          </div>
        }>
        <p>
          Time spent is not a score, and a good score is not mastery. Mastery is an estimate per concept, always shown
          with how much of the subject has been assessed.
        </p>
      </Section>

      {/* 7 — Upcoming classes */}
      <Section id="classes" n="06" kicker="Your timetable" title="Prepare for the class you have next." flip
        figure={
          <div className="lw-class">
            <span className="lw-class-when">Tomorrow · 10:00</span>
            <strong className="display">Computer Networks</strong>
            <span className="lw-class-arrow" aria-hidden="true">↓</span>
            <span className="lw-class-k">Prepare</span>
            <span>The weakest concept you have practised in that subject, about 10 minutes.</span>
            <span className="lw-note-tag">How it works, not your data</span>
          </div>
        }>
        <p>
          Add your weekly classes and SkillForge suggests a short preparation before each one, chosen from your own
          evidence in that subject. If a subject has no question bank yet, it says so instead of guessing.
        </p>
      </Section>

      {/* 8 — Begin */}
      <section className="lw-begin" aria-labelledby="begin-h">
        <h2 className="display" id="begin-h">Begin your own learning journey.</h2>
        <ul className="lw-areas">
          {AREAS.map((a) => {
            const c = counts[a.id];
            return (
              <li key={a.id} className={`tone-${a.tone}`}>
                <span className="lw-area-dot" />
                <strong>{a.name}</strong>
                <span>
                  {!catalog ? "…" : c.banked ? `${c.banked} topics with practice` : `Roadmap · ${c.roadmap} subjects, no practice yet`}
                </span>
              </li>
            );
          })}
        </ul>
        <div className="lw-cta center">
          <button className="btn btn-accent btn-lg" onClick={() => transitionTo("signup")}>
            Start learning <Icon name="arrowRight" size={16} />
          </button>
          <button className="btn btn-secondary btn-lg" onClick={() => transitionTo("login")}>Sign in</button>
        </div>
      </section>

      <footer className="lw-foot">
        <span className="lw-foot-brand">SkillForge</span>
        <span>Practice today: VNR VJIET CSE (AI &amp; ML) R22 courses and DSA foundations. Earth imagery courtesy of NASA Visible Earth.</span>
      </footer>
    </div>
  );
}
