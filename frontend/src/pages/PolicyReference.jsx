import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import Header from "../components/Header.jsx";
import PolicySection from "../components/PolicySection.jsx";
import { parsePolicyMarkdown } from "../lib/policy.js";

export default function PolicyReference({ onMenuClick }) {
  const [text, setText] = useState(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    api.policy().then((r) => setText(r.text));
  }, []);

  const sections = useMemo(() => (text ? parsePolicyMarkdown(text) : []), [text]);
  const filtered = useMemo(() => {
    if (!query.trim()) return sections;
    const q = query.toLowerCase();
    return sections.filter((s) => s.title.toLowerCase().includes(q) || s.body.toLowerCase().includes(q));
  }, [sections, query]);

  return (
    <div className="page">
      <Header
        title="Policy Reference"
        subtitle="The internal refund policy manual used to evaluate every case."
        onMenuClick={onMenuClick}
      />
      <div className="card">
        <input
          className="search-input"
          placeholder="Search the policy manual…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      <div className="card">
        {!text && <p className="muted">Loading policy…</p>}
        {text && filtered.length === 0 && <p className="muted">No sections match "{query}".</p>}
        {filtered.map((s, i) => (
          <PolicySection key={i} title={s.title} body={s.body} />
        ))}
      </div>
    </div>
  );
}
