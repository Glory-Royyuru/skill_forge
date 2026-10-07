import { useState } from "react";

function actionLabel(action) {
  return { process_refund: "Process Refund", reject_refund: "Reject Request", escalate: "Escalate" }[action] || action;
}

export default function FeedbackPanel({ feedback, onNext, onReview }) {
  const [showTrajectory, setShowTrajectory] = useState(false);

  return (
    <div className="card feedback-panel">
      <div className={`feedback-headline ${feedback.success ? "ok" : "warn"}`}>
        {feedback.success ? "✓ Correct resolution" : feedback.critical ? "✕ Critical error" : "△ Incorrect resolution"}
      </div>

      <div className="feedback-score-row">
        <div>
          <div className="metric-value">{feedback.score} / 100</div>
          <div className="metric-label">Score{feedback.hints_used ? ` (after ${feedback.hints_used} hint penalty)` : ""}</div>
        </div>
        <div>
          <div className="metric-value">{actionLabel(feedback.decision)}</div>
          <div className="metric-label">Your decision</div>
        </div>
      </div>

      {feedback.did_well.length > 0 && (
        <section>
          <h4>What you did well</h4>
          <ul className="check-list">
            {feedback.did_well.map((d, i) => (
              <li key={i}>✓ {d}</li>
            ))}
          </ul>
        </section>
      )}

      {feedback.missed.length > 0 && (
        <section>
          <h4>Missed opportunity</h4>
          <ul className="miss-list">
            {feedback.missed.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <h4>Decision explanation</h4>
        <p>{feedback.explanation}</p>
      </section>

      <section>
        <button className="link-button" onClick={() => setShowTrajectory((v) => !v)}>
          {showTrajectory ? "Hide" : "Show"} your trajectory
        </button>
        {showTrajectory && (
          <ol className="timeline">
            {(feedback.trajectory?.tool_log || []).map((step, i) => (
              <li key={i} className={step.ok ? "ok" : "err"}>
                <details>
                  <summary>
                    {step.tool}({JSON.stringify(step.args)})
                  </summary>
                  <pre>{JSON.stringify(step.ok ? step.output : step.error, null, 2)}</pre>
                </details>
              </li>
            ))}
            <li className="ok">
              <strong>
                {actionLabel(feedback.trajectory?.decision?.action)}({JSON.stringify(feedback.trajectory?.decision?.args)})
              </strong>
            </li>
          </ol>
        )}
      </section>

      <div className="feedback-actions">
        <button className="primary-button" onClick={onNext}>
          Try Another Case
        </button>
        {onReview && (
          <button className="secondary-button" onClick={onReview}>
            Review This Case
          </button>
        )}
      </div>
    </div>
  );
}
