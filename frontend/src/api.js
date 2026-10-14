import { MESSAGES, describeFailure } from "./lib/errors.js";

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

// Minutes behind UTC, as the backend expects (IST = -330).
const tz = () => new Date().getTimezoneOffset();

// Called when an authenticated request comes back 401 (session expired or
// signed out elsewhere), so the app can return to the sign-in screen.
let onUnauthorized = null;
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

export class ApiError extends Error {
  constructor(message, status, code, data) {
    super(message);
    this.status = status;
    this.code = code;
    this.data = data;
  }
}

// The API generation this frontend needs (see backend `api/health.py`).
const REQUIRED_API_VERSION = 4;

// A route that should exist came back as the framework's bare 404. Ask the
// server which generation it is, to tell a stale backend process apart from
// a feature that is genuinely unavailable.
async function staleServer() {
  try {
    const res = await fetch(`${API_BASE}/health`, { credentials: "same-origin" });
    const h = await res.json();
    return !(h.api_version >= REQUIRED_API_VERSION);
  } catch {
    return false;
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new ApiError(MESSAGES.network, 0, "network");
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const failure = describeFailure(res.status, data.detail);
    if (res.status === 401 && !path.startsWith("/auth/") && onUnauthorized) onUnauthorized();
    if (failure.code === "endpoint_missing" && (await staleServer())) {
      throw new ApiError(MESSAGES.stale, res.status, "stale_server", data);
    }
    throw new ApiError(failure.message, res.status, failure.code, data);
  }
  return data;
}

const post = (path, body) => request(path, { method: "POST", body: JSON.stringify(body ?? {}) });

export const api = {
  health: () => request("/health"),
  curriculum: () => request("/curriculum"),

  // Accounts
  me: () => request("/auth/me"),
  register: (body) => post("/auth/register", body),
  login: (email, password) => post("/auth/login", { email, password }),
  logout: () => post("/auth/logout"),
  verifyEmail: (token) => post("/auth/verify-email", { token }),
  resendVerification: (email) => post("/auth/resend-verification", { email }),
  forgotPassword: (email) => post("/auth/forgot-password", { email }),
  resetPassword: (token, password, confirm_password) =>
    post("/auth/reset-password", { token, password, confirm_password }),
  // Development only (console email backend): unsent emails for an address.
  devOutbox: (email) => request(`/dev/outbox?email=${encodeURIComponent(email)}`),

  // Teacher Agent
  topics: () => request("/teacher/topics"),
  teacherProgress: () => request("/teacher/progress"),
  startSession: (topic_id, opts = {}) => post("/teacher/session/start", { topic_id, ...opts }),
  getSession: (id) => request(`/teacher/session/${id}`),
  answer: (id, question_id, choice, response_ms) =>
    post(`/teacher/session/${id}/answer`, { question_id, choice, response_ms }),
  report: (id) => request(`/teacher/session/${id}/report`),

  // Learner intelligence (tz = browser offset, so "today" and classes are local)
  overview: () => request(`/learner/overview?tz_offset=${tz()}`),
  learnerState: () => request("/learner/state"),
  recommendations: () => request(`/learner/recommendations?tz_offset=${tz()}`),
  trends: (weeks = 8) => request(`/learner/trends?weeks=${weeks}&tz_offset=${tz()}`),
  activity: (start, end) => request(`/learner/activity?start=${start}&end=${end}&tz_offset=${tz()}`),
  ptm: () => request(`/learner/ptm?tz_offset=${tz()}`),
  review: () => request(`/learner/review?tz_offset=${tz()}`),
  diagnostic: () => request("/learner/diagnostic"),
  startDiagnostic: () => post("/learner/diagnostic/start"),
  answerDiagnostic: (question_id, choice, response_ms) =>
    post("/learner/diagnostic/answer", { question_id, choice, response_ms }),
  skipDiagnostic: () => post("/learner/diagnostic/skip"),

  // Practice
  flashcards: () => request(`/study/flashcards?tz_offset=${tz()}`),
  revealCard: (card_id) => post("/study/flashcards/reveal", { card_id }),
  reviewCard: (card_id, rating) => post("/study/flashcards/review", { card_id, rating }),
  startRapid: () => post("/study/rapid/start"),
  rapid: (id) => request(`/study/rapid/${id}`),
  answerRapid: (id, question_id, choice, response_ms) =>
    post(`/study/rapid/${id}/answer`, { question_id, choice, response_ms }),
  finishRapid: (id) => post(`/study/rapid/${id}/finish`),

  // Profile
  profile: () => request("/profile"),
  updatePreferences: (prefs) => request("/profile/preferences", { method: "PUT", body: JSON.stringify(prefs) }),

  // Timetable
  timetable: () => request("/timetable"),
  createEntry: (entry) => post("/timetable", entry),
  updateEntry: (id, entry) => request(`/timetable/${id}`, { method: "PUT", body: JSON.stringify(entry) }),
  deleteEntry: (id) => request(`/timetable/${id}`, { method: "DELETE" }),

  // Legacy e-commerce practice endpoints (kept for the original SkillForge pages).
  policy: () => request("/policy"),
  cases: (limit = 50) => request(`/cases?limit=${limit}`),
  progress: () => request("/progress"),
  startCase: (mode) => post("/practice/start", { mode }),
  callTool: (case_id, tool, args) => post("/practice/tool", { case_id, tool, args }),
  decide: (case_id, action, args, hints_used) => post("/practice/decision", { case_id, action, args, hints_used }),
  result: (attemptId) => request(`/practice/result/${attemptId}`),
};
