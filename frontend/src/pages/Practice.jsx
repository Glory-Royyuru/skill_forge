import { useEffect, useState } from "react";
import { api } from "../api.js";
import Header from "../components/Header.jsx";
import DifficultyBadge from "../components/DifficultyBadge.jsx";
import ToolButton from "../components/ToolButton.jsx";
import EvidencePanel from "../components/EvidencePanel.jsx";
import Timeline from "../components/Timeline.jsx";
import DecisionPanel from "../components/DecisionPanel.jsx";
import FeedbackPanel from "../components/FeedbackPanel.jsx";

const MODES = [
  { id: "guided", label: "Guided" },
  { id: "practice", label: "Practice" },
  { id: "challenge", label: "Challenge" },
];

const HINTS = [
  "What information would confirm when the order was delivered?",
  "Check the order information.",
  "Return-window eligibility depends on the delivery date, item condition, and customer status together.",
];

function extractOrderId(request) {
  const m = request?.match(/order (\S+)\)/);
  return m ? m[1] : null;
}

export default function Practice({ onMenuClick, onProgressChange }) {
  const [mode, setMode] = useState("practice");
  const [caseData, setCaseData] = useState(null);
  const [evidence, setEvidence] = useState({});
  const [timeline, setTimeline] = useState([]);
  const [toolsUsed, setToolsUsed] = useState(new Set());
  const [hintsRevealed, setHintsRevealed] = useState(0);
  const [feedback, setFeedback] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  function startNewCase(nextMode = mode) {
    setLoading(true);
    setError(null);
    setFeedback(null);
    setEvidence({});
    setTimeline([]);
    setToolsUsed(new Set());
    setHintsRevealed(0);
    api
      .startCase(nextMode)
      .then(setCaseData)
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    startNewCase(mode);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function changeMode(m) {
    setMode(m);
    startNewCase(m);
  }

  const orderId = extractOrderId(caseData?.request);

  function argsFor(toolName) {
    if (toolName === "search_orders") return {};
    if (toolName === "view_order") return orderId ? { order_id: orderId } : null;
    if (toolName === "view_policy") return { section: "full" };
    if (toolName === "view_customer") return evidence.order ? { customer_id: evidence.order.customer_id } : null;
    if (toolName === "view_order_history") return evidence.order ? { customer_id: evidence.order.customer_id } : null;
    return null;
  }

  async function handleTool(tool) {
    const args = argsFor(tool.name) ?? {};
    const res = await api.callTool(caseData.case_id, tool.name, args);
    setTimeline((t) => [...t, { label: `${tool.display_name}: ${res.ok ? "retrieved" : res.error}`, ok: res.ok }]);
    if (res.ok) {
      setToolsUsed((s) => new Set(s).add(tool.name));
      setEvidence((prev) => {
        const next = { ...prev };
        if (tool.name === "view_order") next.order = res.output;
        if (tool.name === "view_customer") next.customer = res.output;
        if (tool.name === "view_order_history") next.history = res.output;
        if (tool.name === "view_policy") next.policySections = [...(prev.policySections || []), res.output.text];
        return next;
      });
    }
  }

  async function handleDecision(action, args) {
    setSubmitting(true);
    setError(null);
    try {
      const fullArgs = { order_id: orderId, ...args };
      const result = await api.decide(caseData.case_id, action, fullArgs, hintsRevealed);
      setFeedback(result);
      onProgressChange?.();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading || !caseData) {
    return (
      <div className="page">
        <Header title="Practice" subtitle="Investigate and resolve a realistic refund case." onMenuClick={onMenuClick} />
        <p className="muted">{error || "Loading a case…"}</p>
      </div>
    );
  }

  return (
    <div className="page">
      <Header
        title="Practice"
        subtitle="Investigate and resolve a realistic refund case."
        onMenuClick={onMenuClick}
        right={
          <div className="mode-switch">
            {MODES.map((m) => (
              <button
                key={m.id}
                className={`mode-chip ${mode === m.id ? "active" : ""}`}
                onClick={() => changeMode(m.id)}
              >
                {m.label}
              </button>
            ))}
          </div>
        }
      />

      {error && <p className="error">{error}</p>}

      {feedback ? (
        <FeedbackPanel feedback={feedback} onNext={() => startNewCase(mode)} />
      ) : (
        <div className="practice-layout">
          <div className="practice-main">
            <div className="card">
              <div className="case-meta">
                <span>Case #{caseData.case_number}</span>
                <DifficultyBadge level={caseData.difficulty} />
                <span className="muted">Evidence collected: {toolsUsed.size}</span>
              </div>
              <p className="customer-message">&ldquo;{caseData.request}&rdquo;</p>
              <p className="muted">Investigate the case using the available tools before resolving it.</p>
            </div>

            <div className="card">
              <h4>Investigation timeline</h4>
              <Timeline steps={timeline} />
            </div>

            <div className="card">
              <h4>Available tools</h4>
              <div className="tool-grid">
                {caseData.tools.map((t) => (
                  <ToolButton key={t.name} tool={t} onClick={handleTool} used={toolsUsed.has(t.name)} />
                ))}
              </div>
              {mode !== "challenge" && (
                <div className="hint-row">
                  <button
                    className="link-button"
                    disabled={hintsRevealed >= HINTS.length}
                    onClick={() => setHintsRevealed((h) => Math.min(h + 1, HINTS.length))}
                  >
                    Need a hint?
                  </button>
                  {Array.from({ length: hintsRevealed }).map((_, i) => (
                    <p key={i} className="hint-text">
                      Hint {i + 1}: {HINTS[i]}
                    </p>
                  ))}
                </div>
              )}
            </div>

            <div className="card">
              <DecisionPanel terminalActions={caseData.terminal_actions} onSubmit={handleDecision} submitting={submitting} />
            </div>
          </div>

          <aside className="practice-side">
            <div className="card">
              <h4>Case information</h4>
              <EvidencePanel evidence={evidence} />
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
