# SkillForge — Adaptive Teacher Agent

A multi-student learning platform for the **VNR VJIET B.Tech. CSE (AI & ML),
R22, III Year V Semester** syllabus. Each student has an account; a Teacher
Agent runs a **Diagnose → Teach → Assess → Adapt → Report** loop over the
syllabus and remembers, per student, how every concept went.

- **Curriculum** (`backend/skillforge/teacher/content/`): the eight V Semester
  courses — Computer Networks, Artificial Intelligence, Operating Systems,
  Machine Learning, Explainable AI, Computer Networks and Operating Systems
  Laboratory, Machine Learning Laboratory, Gender Sensitization — organized
  as subject → unit → topic → concept → question, using the syllabus's own
  units and terminology (125 topics). 14 topics currently have a question
  bank (84 questions, 6 per topic, 2 per difficulty level); the others are
  listed and marked "No question bank yet". Seeded into the database on
  startup; the database is the runtime source of truth.
- **Accounts**: registration with email verification, sign-in with an
  HttpOnly session cookie, sign-out (server-side revocation), forgot/reset
  password. Passwords are hashed with scrypt; session, verification and
  reset tokens are stored only as SHA-256 hashes, expire, and are single-use.
- **Per-student data**: learning sessions, every graded answer with the
  Teacher's adaptive decision, learner-model state per concept, and a
  weekly timetable. Every query is scoped to the signed-in student; other
  students' resources return 404.
- **Deterministic teaching engine** (`backend/skillforge/teacher/engine.py`):
  baseline diagnosis from the student's history, lessons, server-side grading,
  difficulty that steps up/down with each answer, remediation that revisits
  a missed concept at the same or an easier level, misconception-specific
  feedback, re-teaching after repeated misses, mastery tracking, and a
  learning report with a recommendation.
- **Offline learner model** (`backend/skillforge/teacher/learner_model.py`):
  Bayesian Knowledge Tracing in pure Python with configured (textbook)
  slip/guess/learn parameters — it is not trained on data. It estimates
  P(known) per concept, chooses which concept to target next, flags probable
  guesses, and is persisted per student (`learner_concepts`), so the next
  session on a topic starts from that student's estimates. It is a supporting
  signal: grading, difficulty and mastery never depend on it, and the engine
  works without it (`TEACHER_LEARNER_MODEL=none`).
- **Learner intelligence** (`backend/skillforge/learner/`): every graded
  interaction is an evidence event (Teacher session and diagnostic weight 1.0,
  Rapid Round 0.5). The *learner state* combines BKT with attempts, recent
  accuracy, repeated mistakes, difficulty and cognitive-type performance and
  recency (response time is recorded only as a secondary signal), and applies
  documented status rules (one correct answer is never mastery; one wrong
  answer is never "needs review"). Topic/subject/overall estimates are means
  over assessed concepts, always shown with coverage.
- **Recommendation engine** (`learner/recommend.py`): deterministic,
  explainable next actions (diagnostic, remediation, review, class
  preparation from the timetable, revisit, harder question, new topic,
  flashcards, Rapid Round), each carrying its evidence.
- **Cold start**: an optional 8-question diagnostic (one per subject)
  establishes a starting point without ever marking anything mastered.
- **Practice**: personalised flashcards (backs revealed server-side only on
  flip; ratings are a secondary signal) and a server-timed 60-second Rapid
  Round. **Calendar** of real activity, **PTM mode** (evidence-driven SWOT of
  the student's own record), activity level/XP kept separate from mastery,
  optional seasonal themes (presentation only).
- **No trained ML model.** `learner/prediction.py` defines the interface for a
  future P(correct) predictor and a clearly labelled BKT baseline.
- **No external AI service** is called. Everything runs locally; only actual
  email delivery needs a network (SMTP).
- **Design**: "a modern textbook that comes alive" — ink (charcoal), paper
  (ivory/parchment) and leather (a restrained crimson accent), Fraunces for
  display and Inter for interface text (both self-hosted via `@fontsource`, so
  the app stays offline-capable). The landing page and sign-in are built
  around a physical book made of CSS 3D planes (`frontend/src/components/Book.jsx`,
  `styles/book.css`); no 3D library is used. Tokens and shared components live
  in `src/index.css` and `src/styles/system.css`, motion primitives in
  `src/components/motion.jsx`. Every animation respects
  `prefers-reduced-motion`.

### Run it locally

```
# Terminal 1 — backend (http://localhost:8000); --reload picks up code changes
cd backend
.venv/Scripts/uvicorn.exe skillforge.api.app:app --reload --port 8000

# Terminal 2 — frontend (http://localhost:5173)
cd frontend
npm install
npm run dev
```

On startup the backend applies pending schema migrations and seeds the
curriculum (both idempotent). To run them by hand:

```
cd backend
python -m skillforge db upgrade        # apply pending migrations
python -m skillforge curriculum seed   # upsert the VNR curriculum
```

New accounts start empty: there is no demo or sample progress.

**Troubleshooting — "the server is out of date".** The frontend talks to
whatever process is listening on port 8000. A backend started without
`--reload` keeps serving the code it started with, so features added later
(e.g. accounts) answer 404. The frontend detects this through
`GET /api/health` (`api_version`) and says so instead of showing "Not Found";
restart the backend to fix it. `tests/test_api_contract.py` additionally checks
that every endpoint in `frontend/src/api.js` is registered by the backend.

### Email (verification and password reset)

`EMAIL_BACKEND=console` (default) sends nothing: each email, with its link, is
written to the backend log, and the sign-up / forgot-password screens say so.
In development (`APP_ENV=development`, `DEV_EMAIL_OUTBOX=true`) the screens can
also reveal the link via `GET /api/dev/outbox`, which only answers requests
from localhost and returns 404 in any other configuration.

To deliver real email, set `EMAIL_BACKEND=smtp` and `SMTP_HOST`, `SMTP_PORT`,
`SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` (and `SMTP_STARTTLS` /
`SMTP_SSL`) in `backend/.env`, and set `FRONTEND_BASE_URL` to the address
students use so links point there. See `backend/.env.example` for every
variable. For HTTPS deployments set `SESSION_COOKIE_SECURE=true`,
`APP_ENV=production` and `CORS_ORIGINS`.

### Tests

```
cd backend
python -m pytest        # no API keys or SMTP server needed
python -m ruff check .
cd ../frontend && npm run build
```

---

## Original SkillForge design

A closed-loop system that teaches LLM agents procedural skills: a human
provides demonstrations, a **Teacher** agent extracts a structured skill
into a versioned **Skill Memory**, a **Learner** agent attempts tasks in a
simulated environment, a deterministic **Evaluator** scores attempts, and
the Teacher diagnoses failures and patches the Skill Memory. Improvement is
measured on held-out tasks.

See `CLAUDE.md` for how this repo is built (one phase at a time) and
`PROGRESS.md` for the current phase checklist.

## Repo layout

```
backend/skillforge/
  api/      FastAPI app and routes
  core/     settings
  db/       SQLAlchemy models, engine/session construction
  llm/      provider-agnostic LLM layer (OpenAI, Anthropic, Mock)
  envs/     simulated environments (Phase 1+)
  agents/   Teacher / Learner agents (Phase 2+)
  cli/      `python -m skillforge <command>`
backend/tests/
frontend/   React UI placeholder (Phase 7+)
```

## Setup

Requires Python 3.11+.

### macOS / Linux (with `make`)

```sh
make install   # pip install -e backend[dev]
make test      # pytest, no API keys required
make lint      # ruff check
make run       # starts the API on http://127.0.0.1:8000
```

### Windows (plain commands, no `make` needed)

```powershell
cd backend
pip install -e ".[dev]"
pytest
ruff check .
uvicorn skillforge.api.app:app --reload --port 8000
```

(The same commands work from `bash`/Git Bash — just adjust `cd` as needed.)

Then, in another terminal:

```powershell
curl http://127.0.0.1:8000/api/health
```

Or, without starting a server:

```powershell
cd backend
python -m skillforge health
```

## Configuration

Copy `backend/.env.example` to `backend/.env` and fill in as needed. Every
setting has a working default — the app and the full test suite run with
**no API keys set** (agents default to the `mock` provider). See
`backend/skillforge/core/settings.py` for the full list of settings.

## Tests

Tests never require API keys — anything that would call a real LLM uses
`MockProvider` (`backend/skillforge/llm/mock.py`) instead. Run them with
`pytest` from `backend/`.
