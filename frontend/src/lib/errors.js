// Turns an HTTP failure into a message a student can act on. Backend messages
// written for people ({code, message} details and our own short strings) are
// kept; framework defaults ("Not Found", "Internal Server Error"), validation
// internals and stack traces never reach the screen.

const FRAMEWORK_DEFAULTS = new Set([
  "Not Found",
  "Method Not Allowed",
  "Internal Server Error",
  "Bad Request",
  "Unauthorized",
  "Forbidden",
]);

// Messages for well-known backend error codes, where our wording is clearer.
const BY_CODE = {
  invalid_credentials: "Email or password is incorrect.",
  email_not_verified: "Please verify your email before signing in.",
  email_taken: "An account with this email already exists.",
  student_id_taken: "An account with this registration ID already exists.",
  too_many_attempts: "Too many failed sign-in attempts. Please wait a few minutes and try again.",
};

export const MESSAGES = {
  network: "Can't reach the SkillForge server. Check that the backend is running, then try again.",
  stale:
    "The SkillForge server running on this computer is out of date and doesn't include this feature yet. Restart the backend, then try again.",
  missing: "This feature isn't available on the SkillForge server right now.",
  server: "Something went wrong. Please try again.",
  session: "Your session has ended. Please sign in again.",
  refused: "The request was refused. Reload the page and try again.",
  invalid: "Some details aren't valid. Check the form and try again.",
};

function validationText(list) {
  // FastAPI 422: [{loc, msg, type}]; show the human part only.
  const parts = list
    .map((d) => {
      const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null;
      const msg = typeof d.msg === "string" ? d.msg.replace(/^Value error, /, "") : "";
      if (!msg) return null;
      if (d.type === "missing" && field) return `${String(field).replace(/_/g, " ")} is required.`;
      return msg.endsWith(".") ? msg : `${msg}.`;
    })
    .filter(Boolean);
  return parts.length ? parts.join(" ") : MESSAGES.invalid;
}

// `detail` is the parsed body's `detail`; returns {message, code, kind}.
export function describeFailure(status, detail) {
  const code = detail && typeof detail === "object" && !Array.isArray(detail) ? detail.code : undefined;
  const own =
    typeof detail === "string" && !FRAMEWORK_DEFAULTS.has(detail) && detail.length < 240 ? detail : undefined;
  const structured = code ? BY_CODE[code] || detail.message : undefined;

  if (status === 404 && (detail == null || detail === "Not Found")) {
    // The route itself does not exist on the running server.
    return { message: MESSAGES.missing, code: "endpoint_missing", kind: "missing" };
  }
  if (status >= 500) return { message: MESSAGES.server, code, kind: "server" };
  if (status === 422 && Array.isArray(detail)) return { message: validationText(detail), code: "invalid", kind: "invalid" };
  if (structured) return { message: structured, code, kind: "app" };
  if (own) return { message: own, code, kind: "app" };
  if (status === 401) return { message: MESSAGES.session, code, kind: "auth" };
  if (status === 403) return { message: MESSAGES.refused, code, kind: "auth" };
  if (status === 400 || status === 422) return { message: MESSAGES.invalid, code, kind: "invalid" };
  if (status === 409) return { message: "That conflicts with existing data. Refresh and try again.", code, kind: "app" };
  return { message: MESSAGES.server, code, kind: "server" };
}
