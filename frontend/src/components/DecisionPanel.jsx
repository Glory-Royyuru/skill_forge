import { useState } from "react";

const REASON_CODES = ["window_expired", "already_refunded", "final_sale_non_refundable", "policy_violation"];
const METHODS = ["original_payment", "store_credit"];

export default function DecisionPanel({ terminalActions, onSubmit, submitting }) {
  const [action, setAction] = useState(null);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState(METHODS[0]);
  const [reasonCode, setReasonCode] = useState(REASON_CODES[0]);

  function submit() {
    if (!action) return;
    const args =
      action === "process_refund"
        ? { amount: Number(amount) || 0, method }
        : { reason_code: reasonCode };
    onSubmit(action, args);
  }

  return (
    <div className="decision-panel">
      <h4>Decision</h4>
      <div className="decision-actions">
        {terminalActions.map((a) => (
          <button
            key={a.name}
            className={`decision-button ${action === a.name ? "selected" : ""}`}
            onClick={() => setAction(a.name)}
          >
            {a.display_name}
          </button>
        ))}
      </div>

      {action === "process_refund" && (
        <div className="decision-form">
          <label>
            Amount ($)
            <input type="number" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </label>
          <label>
            Method
            <select value={method} onChange={(e) => setMethod(e.target.value)}>
              {METHODS.map((m) => (
                <option key={m} value={m}>
                  {m.replace("_", " ")}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
      {(action === "reject_refund" || action === "escalate") && (
        <div className="decision-form">
          <label>
            Reason code
            <select value={reasonCode} onChange={(e) => setReasonCode(e.target.value)}>
              {REASON_CODES.map((r) => (
                <option key={r} value={r}>
                  {r.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      {action && (
        <button className="primary-button" onClick={submit} disabled={submitting}>
          {submitting ? "Submitting…" : "Resolve Case"}
        </button>
      )}
    </div>
  );
}
