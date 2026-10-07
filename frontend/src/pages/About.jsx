import { Card, Icon, PageHeader } from "../components/ui.jsx";
import { navigate } from "../lib/router.js";

const STAGES = [
  {
    name: "Diagnose",
    text: "Checks your record on the topic. New learners start at Foundational; 80%+ previous mastery starts at Intermediate. The learner model restores your concept estimates, and the first question is a baseline probe.",
  },
  {
    name: "Teach",
    text: "A short lesson with key points opens every session. Miss the same concept twice and the teacher re-teaches it with a focused explanation.",
  },
  {
    name: "Assess",
    text: "Each answer is graded on the server against the answer key and recorded per concept. Common wrong answers get misconception-specific feedback.",
  },
  {
    name: "Adapt",
    text: "Correct answers step difficulty up; mistakes step it down and target the missed concept. The learner model picks the least-known concept to practise next.",
  },
  {
    name: "Report",
    text: "Score, mastery, a concept breakdown, a written assessment, and a recommendation for what to study next.",
  },
];

const FLOW = [
  { k: "Student", v: "Answers a question", icon: "teacher" },
  { k: "Teacher Agent", v: "Grades it, updates mastery, applies difficulty rules", icon: "book" },
  { k: "Learner Model", v: "Bayesian Knowledge Tracing updates P(known) per concept", icon: "layers" },
  { k: "Adaptive Decision", v: "Rules choose difficulty; model chooses which concept to target", icon: "target" },
  { k: "Next Learning Action", v: "Teach, reinforce, or raise the challenge", icon: "arrowRight" },
];

const RULES = [
  ["Correct answer", "Mastery +15/20/25 (by difficulty) · difficulty steps up"],
  ["Incorrect answer", "Mastery −5 · difficulty steps down · next question targets the missed concept"],
  ["Second miss on a concept", "Needs review · concept is re-taught"],
  ["Correct, but model still doubts the concept (< 50%)", "Treated as a possible guess · stays on the concept at a harder level"],
  ["Choosing the next concept", "Least-known concept according to the learner model"],
  ["Mastery ≥ 80%, no weak concepts", "Recommend advancing to the next topic"],
  ["Otherwise", "Recommend a review, or revisiting the topic"],
];

export default function About() {
  return (
    <>
      <PageHeader
        eyebrow="How it works"
        title="A teacher that diagnoses, teaches, assesses, and adapts"
        subtitle="SkillForge combines deterministic teaching rules with an offline probabilistic learner model. Everything runs locally; no external AI service is called."
        actions={
          <button className="btn btn-primary" onClick={() => navigate("topics")}>
            Start a session <Icon name="arrowRight" size={16} />
          </button>
        }
      />

      <ol className="stages">
        {STAGES.map((s, i) => (
          <li key={s.name} className="stage rise" style={{ animationDelay: `${i * 70}ms` }}>
            <div className="stage-n display">{String(i + 1).padStart(2, "0")}</div>
            <h3 className="display">{s.name}</h3>
            <p>{s.text}</p>
          </li>
        ))}
      </ol>

      <div className="grid grid-2-1 about-grid">
        <Card title="Hybrid architecture" className="rise" style={{ animationDelay: "200ms" }}>
          <ol className="flow">
            {FLOW.map((f, i) => (
              <li key={f.k} className="flow-step" style={{ animationDelay: `${300 + i * 110}ms` }}>
                <span className="flow-icon">
                  <Icon name={f.icon} size={16} />
                </span>
                <span>
                  <span className="flow-k">{f.k}</span>
                  <span className="flow-v">{f.v}</span>
                </span>
              </li>
            ))}
          </ol>
          <p className="muted small flow-note">
            The learner model is a supporting signal. Grading, difficulty steps, mastery, and the report come from
            the deterministic engine, which works the same with the model switched off
            (<code>TEACHER_LEARNER_MODEL=none</code>).
          </p>
        </Card>
        <Card title="About the learner model" className="rise" style={{ animationDelay: "260ms" }}>
          <div className="principles">
            <p>
              <strong>Bayesian Knowledge Tracing</strong> treats each concept as a hidden “known / not yet known”
              state. After every answer it updates the probability with Bayes' rule, allowing for lucky guesses
              and careless slips, then adds a chance of learning.
            </p>
            <p>
              Slip and guess rates vary with question difficulty. Parameters are standard defaults rather than
              fitted to data. The model is pure Python and fully deterministic, and its estimates carry over
              between sessions.
            </p>
          </div>
        </Card>
      </div>

      <Card title="Adaptation rules" className="rise" style={{ animationDelay: "320ms" }}>
        <table className="table">
          <tbody>
            {RULES.map(([event, response]) => (
              <tr key={event}>
                <td className="strong rule-k">{event}</td>
                <td className="muted">{response}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}
