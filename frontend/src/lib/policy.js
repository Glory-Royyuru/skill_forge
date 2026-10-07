// Splits the backend's markdown policy document into {title, body}
// sections for display. Presentation-only — the policy content itself is
// owned entirely by the backend (policy_docs/v1.md).
export function parsePolicyMarkdown(text) {
  const lines = text.split("\n");
  const sections = [];
  let current = null;
  for (const line of lines) {
    if (line.startsWith("## ")) {
      if (current) sections.push(current);
      current = { title: line.slice(3).trim(), body: "" };
    } else if (line.startsWith("# ") || line.startsWith("---") || line.startsWith("*Policy version")) {
      continue;
    } else if (current) {
      current.body += (current.body ? " " : "") + line.trim();
    }
  }
  if (current) sections.push(current);
  return sections.filter((s) => s.body.trim().length > 0);
}
