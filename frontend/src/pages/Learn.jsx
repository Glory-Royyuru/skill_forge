import { useState } from "react";
import Header from "../components/Header.jsx";

const SECTIONS = [
  {
    n: "01",
    title: "Understand the request",
    body: "Read the customer's message carefully. Note what they're asking for, which order they mean, and anything they claim about dates or condition — but don't take their claims at face value yet.",
  },
  {
    n: "02",
    title: "Gather evidence",
    body: "Use the available tools to retrieve the order and, if useful, search for related orders. The system's own records are always the source of truth, not the customer's description.",
  },
  {
    n: "03",
    title: "Check customer status",
    body: "Look up the customer profile. Some customers receive extended consideration, and a history of frequent refunds can also change how a request should be handled.",
  },
  {
    n: "04",
    title: "Consult policy",
    body: "Check the relevant policy section before deciding. Refund eligibility depends on more than just how long ago the order was delivered.",
  },
  {
    n: "05",
    title: "Determine eligibility",
    body: "Combine what you've learned: delivery timing, item condition, customer status, and order type (gift, final sale, etc.) all interact to determine whether — and how — a refund applies.",
  },
  {
    n: "06",
    title: "Choose the correct action",
    body: "Resolve the case with exactly one action: process the refund with the correct amount and method, reject it with the right reason, or escalate it for manager review when required.",
  },
];

const CHECKPOINT = {
  question: "A customer says their order arrived 40 days ago and was damaged. Which information should you verify first?",
  choices: [
    { id: "a", label: "The order's actual delivery date and item condition in the system", correct: true },
    { id: "b", label: "Nothing — just trust the customer's message and process the refund", correct: false },
    { id: "c", label: "The customer's shipping address", correct: false },
  ],
  explain: {
    a: "Correct. The system record is always authoritative, and item condition changes which return window applies.",
    b: "Not quite — claims should always be verified against the system record before acting.",
    c: "Shipping address isn't relevant to refund eligibility here.",
  },
};

export default function Learn({ onMenuClick }) {
  const [selected, setSelected] = useState(null);

  return (
    <div className="page">
      <Header title="How to Resolve a Refund Case" subtitle="A short walkthrough of the decision process." onMenuClick={onMenuClick} />

      <div className="card">
        <h2>Decision flow</h2>
        <div className="flow-diagram">
          {["Customer Request", "Order Information", "Customer Information", "Policy", "Item / Refund Details", "Decision"].map(
            (step, i, arr) => (
              <span key={step} className="flow-step-wrap">
                <span className="flow-step">{step}</span>
                {i < arr.length - 1 && <span className="flow-arrow">↓</span>}
              </span>
            )
          )}
        </div>
      </div>

      {SECTIONS.map((s) => (
        <div className="card" key={s.n}>
          <div className="learn-section-heading">
            <span className="learn-section-number">{s.n}</span>
            <h3>{s.title}</h3>
          </div>
          <p>{s.body}</p>
        </div>
      ))}

      <div className="card">
        <h2>Try it yourself</h2>
        <p className="checkpoint-question">{CHECKPOINT.question}</p>
        <div className="checkpoint-choices">
          {CHECKPOINT.choices.map((c) => (
            <button
              key={c.id}
              className={`checkpoint-choice ${selected === c.id ? (c.correct ? "correct" : "incorrect") : ""}`}
              onClick={() => setSelected(c.id)}
            >
              {c.label}
            </button>
          ))}
        </div>
        {selected && <p className="checkpoint-explain">{CHECKPOINT.explain[selected]}</p>}
      </div>
    </div>
  );
}
