const API_BASE = import.meta.env.VITE_API_BASE || "/api";

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new Error("Can't reach the SkillForge backend. Is it running on port 8000?");
  }
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  health: () => request("/health"),

  // Teacher Agent
  topics: () => request("/teacher/topics"),
  teacherProgress: () => request("/teacher/progress"),
  startSession: (topic_id) =>
    request("/teacher/session/start", { method: "POST", body: JSON.stringify({ topic_id }) }),
  getSession: (id) => request(`/teacher/session/${id}`),
  answer: (id, question_id, choice) =>
    request(`/teacher/session/${id}/answer`, {
      method: "POST",
      body: JSON.stringify({ question_id, choice }),
    }),
  report: (id) => request(`/teacher/session/${id}/report`),

  // Legacy e-commerce practice endpoints (kept for the original SkillForge pages).
  policy: () => request("/policy"),
  cases: (limit = 50) => request(`/cases?limit=${limit}`),
  progress: () => request("/progress"),
  startCase: (mode) => request("/practice/start", { method: "POST", body: JSON.stringify({ mode }) }),
  callTool: (case_id, tool, args) =>
    request("/practice/tool", { method: "POST", body: JSON.stringify({ case_id, tool, args }) }),
  decide: (case_id, action, args, hints_used) =>
    request("/practice/decision", {
      method: "POST",
      body: JSON.stringify({ case_id, action, args, hints_used }),
    }),
  result: (attemptId) => request(`/practice/result/${attemptId}`),
};
