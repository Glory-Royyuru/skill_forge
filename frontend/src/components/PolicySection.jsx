const HIGHLIGHTS = ["30 days", "60 days", "15 days", "7 days", "85%", "$500", "3 or more refunds", "90 days"];

function highlight(text) {
  let parts = [text];
  HIGHLIGHTS.forEach((term) => {
    parts = parts.flatMap((part) => {
      if (typeof part !== "string") return [part];
      const idx = part.indexOf(term);
      if (idx === -1) return [part];
      return [
        part.slice(0, idx),
        <mark key={`${term}-${idx}-${Math.random()}`}>{term}</mark>,
        part.slice(idx + term.length),
      ];
    });
  });
  return parts;
}

export default function PolicySection({ title, body }) {
  return (
    <div className="policy-section">
      <h3>{title}</h3>
      <p>{highlight(body)}</p>
    </div>
  );
}
