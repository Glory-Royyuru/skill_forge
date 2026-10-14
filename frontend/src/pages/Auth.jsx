import { useEffect, useId, useRef, useState } from "react";
import { api } from "../api.js";
import { transitionTo } from "../components/motion.jsx";
import { Icon } from "../components/ui.jsx";
import { navigate } from "../lib/router.js";

// Client-side hints only; backend enforces authoritative rules.
function passwordProblems(pw, email) {
  const out = [];
  if (pw.length < 8) out.push("at least 8 characters");
  if (!/[A-Za-z]/.test(pw) || !/\d/.test(pw)) out.push("a letter and a number");
  if (email && pw.toLowerCase() === email.trim().toLowerCase()) out.push("different from your email");
  return out;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function emailHint(email) {
  const v = email.trim();
  if (!v) return undefined;
  if (!EMAIL_RE.test(v)) return { error: true, text: "Enter a valid email address." };
  if (v !== v.toLowerCase()) return { text: `We'll store this as ${v.toLowerCase()}.` };
  return undefined;
}

function PasswordRules({ password, email }) {
  const rules = [
    { ok: password.length >= 8, text: "At least 8 characters" },
    { ok: /[A-Za-z]/.test(password) && /\d/.test(password), text: "A letter and a number" },
    { ok: password.length > 0 && password.toLowerCase() !== (email || "").trim().toLowerCase(), text: "Not the same as your email" },
    { ok: new Set(password).size >= 4, text: "Not too repetitive" },
  ];
  const met = rules.filter((r) => r.ok).length;
  const bonus = password.length >= 12 && /[^A-Za-z0-9]/.test(password) ? 1 : 0;
  const score = password ? Math.min(5, met + bonus) : 0;
  const label = ["", "Weak", "Weak", "Fair", "Good", "Strong"][score];
  return (
    <div className="pw-rules" aria-live="polite">
      <div className="pw-meter" aria-hidden="true">
        {[1, 2, 3, 4, 5].map((n) => (
          <span key={n} className={n <= score ? `on s${score}` : ""} />
        ))}
      </div>
      {password && <div className="pw-label small">Strength: {label}</div>}
      <ul>
        {rules.map((r) => (
          <li key={r.text} className={r.ok ? "ok" : ""}>
            <Icon name={r.ok ? "check" : "x"} size={12} /> {r.text}
          </li>
        ))}
      </ul>
    </div>
  );
}

// Labels, hints and errors are tied to the input so screen readers announce them.
function Field({ label, hint, error, children, ...props }) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  return (
    <div className="field">
      <label className="field-label" htmlFor={id}>
        {label}
      </label>
      <div className={children ? "field-control" : undefined}>
        <input
          id={id}
          className={`input ${error ? "input-error" : ""}`}
          aria-invalid={error ? "true" : undefined}
          aria-describedby={hintId}
          {...props}
        />
        {children}
      </div>
      {hint && (
        <span id={hintId} className={`field-hint ${error ? "field-error" : ""}`} role={error ? "alert" : undefined}>
          {hint}
        </span>
      )}
    </div>
  );
}

// A password input with a visibility toggle. The toggle only changes the
// input type; nothing about the submitted value or the request changes.
function PasswordField(props) {
  const [shown, setShown] = useState(false);
  return (
    <Field {...props} type={shown ? "text" : "password"} spellCheck={false} autoCapitalize="off">
      <button
        type="button"
        className="pw-toggle"
        onClick={() => setShown((v) => !v)}
        aria-pressed={shown}
        aria-label={shown ? `Hide ${props.label.toLowerCase()}` : `Show ${props.label.toLowerCase()}`}
      >
        {shown ? "Hide" : "Show"}
      </button>
    </Field>
  );
}

function Alert({ tone = "error", children }) {
  return (
    <div className={`alert alert-${tone}`} role={tone === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}

function DevNote({ result, email }) {
  const [emails, setEmails] = useState(null);
  const [err, setErr] = useState(null);
  if (!result || result.email_delivery !== "disabled") return null;

  const show = () =>
    api
      .devOutbox(email)
      .then((r) => setEmails(r.emails))
      .catch((e) => setErr(e.message));

  return (
    <div className="dev-note">
      <div className="dev-note-title">
        <Icon name="info" size={15} /> Development mode
      </div>
      <p>{result.delivery_note}</p>
      {result.dev_outbox && !emails && (
        <button type="button" className="btn btn-secondary btn-sm" onClick={show}>
          Show development link
        </button>
      )}
      {emails && emails.length === 0 && <p className="muted small">No unsent email for this address.</p>}
      {emails && emails.length > 0 && (
        <a className="dev-link" href={emails[0].link}>
          {emails[0].kind === "reset_password" ? "Open password reset link" : "Open verification link"}
        </a>
      )}
      {err && <p className="muted small">{err}</p>}
    </div>
  );
}

function AuthLayout({ kicker, title, subtitle, children, footer }) {
  return (
    <div className="auth-form">
      {kicker && <div className="kicker">{kicker}</div>}
      <h1 className="display auth-title">{title}</h1>
      {subtitle && <p className="auth-subtitle">{subtitle}</p>}
      {children}
      {footer && <div className="auth-switch">{footer}</div>}
    </div>
  );
}

// The auth stage: a still photograph of the Earth (the same NASA image the
// landing page uses as its fallback) and one honest line about each step.
// Nothing here moves; the form is the focus.
const STEP_COPY = {
  signup: {
    step: "Create account",
    title: "Your learning record starts here",
    body: "Sessions, concept estimates and your timetable are saved to this account and visible only to you.",
  },
  "check-email": {
    step: "Verify email",
    title: "One link to confirm it is you",
    body: "Open the verification link we sent. Your account is activated once the link is used.",
  },
  "verify-email": {
    step: "Verify email",
    title: "Confirming your address",
    body: "After verification you can sign in and take a short diagnostic to set your starting point.",
  },
  login: {
    step: "Sign in",
    title: "Pick up where you left off",
    body: "Your concept estimates, review list and session history are kept with your account.",
  },
  "forgot-password": {
    step: "Password reset",
    title: "Reset links work once",
    body: "Each link can be used a single time and expires. Your learning record is not affected.",
  },
  "reset-password": {
    step: "Password reset",
    title: "Choose a new password",
    body: "Setting a new password signs this account out on every device, so you will sign in again afterwards.",
  },
};

function AuthEarth({ route }) {
  const meta = STEP_COPY[route] || STEP_COPY.login;
  return (
    <div className="auth-earth">
      <div className="auth-globe" aria-hidden="true">
        <span className="auth-globe-map" />
      </div>
      <div className="auth-earth-text">
        <span className="kicker">{meta.step}</span>
        <h2 className="display auth-earth-title">{meta.title}</h2>
        <p className="auth-earth-body">{meta.body}</p>
      </div>
      <p className="auth-earth-credit">Imagery: NASA Blue Marble</p>
    </div>
  );
}

export const AUTH_ROUTES = new Set([
  "signup",
  "check-email",
  "verify-email",
  "login",
  "forgot-password",
  "reset-password",
]);

export function AuthShell({ route, children }) {
  return (
    <div className="auth">
      <aside className="auth-scene">
        <header className="auth-brand-bar">
          <button className="auth-brand" onClick={() => transitionTo("welcome")} aria-label="SkillForge home">
            <span className="auth-brand-mark" aria-hidden="true">
              SF
            </span>
            <span className="auth-brand-name">SkillForge</span>
          </button>
        </header>

        <div className="auth-visual-wrap">
          <AuthEarth route={route} />
        </div>
      </aside>

      <main className="auth-panel">
        <div className="auth-panel-inner" key={route}>
          {children}
        </div>
      </main>
    </div>
  );
}

export function Login({ onSignedIn, query = {} }) {
  const [email, setEmail] = useState(query.email || "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notVerified, setNotVerified] = useState(false);
  const [resendResult, setResendResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNotVerified(false);
    try {
      const res = await api.login(email, password);
      onSignedIn(res.user);
    } catch (err) {
      setError(err.message);
      setNotVerified(err.code === "email_not_verified");
    } finally {
      setBusy(false);
    }
  };

  const handleResend = async () => {
    try {
      const res = await api.resendVerification(email);
      setResendResult(res);
    } catch (err) {
      setError(err.message);
    }
  };

  const emailValidation = emailHint(email);

  return (
    <AuthLayout
      kicker="Sign in"
      title="Welcome back"
      subtitle="Pick up your learning where you left it."
      footer={
        <>
          New to SkillForge?{" "}
          <button className="link-btn" onClick={() => navigate("signup")}>
            Create an account
          </button>
        </>
      }
    >
      <form className="form" onSubmit={handleSubmit} noValidate>
        {query.verified && <Alert tone="ok">Email verified. Sign in to continue.</Alert>}
        {query.reset && <Alert tone="ok">Password updated. Sign in with your new password.</Alert>}
        {error && <Alert>{error}</Alert>}
        {notVerified && !resendResult && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={handleResend}>
            Send a new verification link
          </button>
        )}
        {resendResult && (
          <>
            <Alert tone="ok">{resendResult.message}</Alert>
            <DevNote result={resendResult} email={email} />
          </>
        )}
        <Field
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={emailValidation?.error}
          hint={emailValidation?.error ? emailValidation.text : undefined}
        />
        <PasswordField
          label="Password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <div className="form-row">
          <button type="button" className="link-btn" onClick={() => navigate("forgot-password")}>
            Forgot password?
          </button>
        </div>
        <button className="btn btn-primary btn-lg btn-block" disabled={busy || !email || !password}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </AuthLayout>
  );
}

export function Signup() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    student_id: "",
    password: "",
    confirm_password: "",
  });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const update = (field) => (e) => setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const problems = passwordProblems(form.password, form.email);
  const mismatch = form.confirm_password && form.confirm_password !== form.password;
  const emailVal = emailHint(form.email);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (problems.length || mismatch) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.register({
        ...form,
        student_id: form.student_id || null,
      });
      sessionStorage.setItem("sf_delivery", JSON.stringify(res));
      navigate("check-email", null, { email: form.email.trim().toLowerCase() });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const valid =
    !busy &&
    form.name.trim().length > 0 &&
    EMAIL_RE.test(form.email.trim()) &&
    problems.length === 0 &&
    form.confirm_password &&
    !mismatch;

  return (
    <AuthLayout
      kicker="Create account"
      title="Begin your journey"
      subtitle="Your sessions, concept estimates and timetable are saved to your account."
      footer={
        <>
          Already have an account?{" "}
          <button className="link-btn" onClick={() => navigate("login")}>
            Sign in
          </button>
        </>
      }
    >
      <form className="form" onSubmit={handleSubmit} noValidate>
        {error && <Alert>{error}</Alert>}
        <Field
          label="Full name"
          autoComplete="name"
          required
          maxLength={120}
          value={form.name}
          onChange={update("name")}
        />
        <Field
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={form.email}
          onChange={update("email")}
          hint={emailVal?.text}
          error={emailVal?.error}
        />
        <Field
          label="Registration ID"
          hint="Optional student ID"
          maxLength={32}
          value={form.student_id}
          onChange={update("student_id")}
        />
        <PasswordField
          label="Password"
          autoComplete="new-password"
          required
          value={form.password}
          onChange={update("password")}
        />
        <PasswordRules password={form.password} email={form.email} />
        <PasswordField
          label="Confirm password"
          autoComplete="new-password"
          required
          value={form.confirm_password}
          onChange={update("confirm_password")}
          hint={mismatch ? "Passwords do not match." : form.confirm_password ? "Passwords match." : undefined}
          error={mismatch}
        />
        <button className="btn btn-primary btn-lg btn-block" disabled={!valid}>
          {busy ? "Creating account…" : "Create account"}
        </button>
      </form>
    </AuthLayout>
  );
}

export function CheckEmail({ query = {} }) {
  const email = query.email || "";
  const [delivery, setDelivery] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem("sf_delivery") || "null");
    } catch {
      return null;
    }
  });
  const [resent, setResent] = useState(false);

  const handleResend = async () => {
    const res = await api.resendVerification(email);
    setDelivery(res);
    setResent(true);
  };

  const sent = delivery?.email_delivery === "sent";

  return (
    <AuthLayout
      title="Verify your email"
      subtitle={
        sent
          ? `We sent a verification link to ${email}. Open it to activate your account.`
          : `Your account for ${email} needs a verified email before you can sign in.`
      }
      footer={
        <button className="link-btn" onClick={() => navigate("login", null, { email })}>
          Back to sign in
        </button>
      }
    >
      <div className="form">
        <DevNote result={delivery} email={email} />
        {resent && <Alert tone="ok">A new link has been issued. Earlier links no longer work.</Alert>}
        <button className="btn btn-secondary btn-block" onClick={handleResend} disabled={!email}>
          Resend verification link
        </button>
      </div>
    </AuthLayout>
  );
}

export function VerifyEmail({ query = {} }) {
  const [state, setState] = useState({ status: "working" });
  const called = useRef(false);

  useEffect(() => {
    if (called.current) return;
    called.current = true;
    if (!query.token) {
      setState({ status: "error", message: "This verification link is incomplete." });
      return;
    }
    api
      .verifyEmail(query.token)
      .then(() => setState({ status: "done" }))
      .catch((err) => setState({ status: "error", message: err.message }));
  }, [query.token]);

  return (
    <AuthLayout title="Email verification">
      {state.status === "working" && <p className="muted">Checking your link…</p>}
      {state.status === "done" && (
        <div className="form">
          <Alert tone="ok">Your email is verified.</Alert>
          <button className="btn btn-primary btn-lg btn-block" onClick={() => navigate("login", null, { verified: 1 })}>
            Sign in
          </button>
        </div>
      )}
      {state.status === "error" && (
        <div className="form">
          <Alert>{state.message}</Alert>
          <p className="muted small">Sign in with your email and password to request a new link.</p>
          <button className="btn btn-secondary btn-block" onClick={() => navigate("login")}>
            Go to sign in
          </button>
        </div>
      )}
    </AuthLayout>
  );
}

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.forgotPassword(email);
      setResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout
      title="Reset your password"
      subtitle="Enter your account email and we'll send you a link to choose a new password."
      footer={
        <button className="link-btn" onClick={() => navigate("login")}>
          Back to sign in
        </button>
      }
    >
      {result ? (
        <div className="form">
          <Alert tone="ok">{result.message}</Alert>
          <DevNote result={result} email={email} />
        </div>
      ) : (
        <form className="form" onSubmit={handleSubmit} noValidate>
          {error && <Alert>{error}</Alert>}
          <Field
            label="Email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button className="btn btn-primary btn-lg btn-block" disabled={busy || !email}>
            {busy ? "Sending…" : "Send reset link"}
          </button>
        </form>
      )}
    </AuthLayout>
  );
}

export function ResetPassword({ query = {} }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const problems = passwordProblems(password);
  const mismatch = confirm && confirm !== password;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.resetPassword(query.token || "", password, confirm);
      navigate("login", null, { reset: 1 });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout
      title="Choose a new password"
      subtitle="Signing in again will be required on all your devices."
      footer={
        <button className="link-btn" onClick={() => navigate("forgot-password")}>
          Request a new link
        </button>
      }
    >
      <form className="form" onSubmit={handleSubmit} noValidate>
        {!query.token && <Alert>This reset link is incomplete.</Alert>}
        {error && <Alert>{error}</Alert>}
        <PasswordField
          label="New password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <PasswordRules password={password} email="" />
        <PasswordField
          label="Confirm new password"
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          hint={mismatch ? "Passwords do not match." : undefined}
          error={mismatch}
        />
        <button
          className="btn btn-primary btn-lg btn-block"
          disabled={busy || !query.token || problems.length > 0 || !confirm || mismatch}
        >
          {busy ? "Saving…" : "Update password"}
        </button>
      </form>
    </AuthLayout>
  );
}

