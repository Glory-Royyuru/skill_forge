function Rows({ obj, omit = [] }) {
  return Object.entries(obj)
    .filter(([k]) => !omit.includes(k))
    .map(([k, v]) => (
      <div className="evidence-row" key={k}>
        <span className="evidence-key">{k.replace(/_/g, " ")}</span>
        <span className="evidence-value">{String(v)}</span>
      </div>
    ));
}

export default function EvidencePanel({ evidence }) {
  const { order, customer, history, policySections } = evidence;
  return (
    <div className="evidence-panel">
      <div className="evidence-block">
        <h4>Order</h4>
        {order ? <Rows obj={order} /> : <p className="muted">Not yet retrieved</p>}
      </div>
      <div className="evidence-block">
        <h4>Customer</h4>
        {customer ? <Rows obj={customer} /> : <p className="muted">Not yet retrieved</p>}
      </div>
      <div className="evidence-block">
        <h4>Refund History</h4>
        {history ? (
          <p>{history.entries.length} prior refund(s) on file</p>
        ) : (
          <p className="muted">Not yet retrieved</p>
        )}
      </div>
      {policySections?.length > 0 && (
        <div className="evidence-block">
          <h4>Policy consulted</h4>
          {policySections.map((p, i) => (
            <p key={i} className="policy-snippet">
              {p}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
