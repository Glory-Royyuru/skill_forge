# SkillForge — Adaptive Teacher Agent

**Current product (submission demo):** an offline teaching agent that runs
a **Diagnose → Teach → Assess → Adapt → Report** loop over a small
curriculum (Machine Learning, Python, DSA; 9 topics, 54 questions).

- **Deterministic teaching engine** (`backend/skillforge/teacher/engine.py`):
  baseline diagnosis from your history, lessons, server-side grading,
  difficulty that steps up/down with each answer, misconception-specific
  feedback, re-teaching after repeated misses, mastery tracking, and a
  learning report with a recommendation.
- **Offline learner model** (`backend/skillforge/teacher/learner_model.py`):
  Bayesian Knowledge Tracing in pure Python. It estimates P(known) per
  concept, chooses which concept to target next, flags probable guesses,
  and carries estimates between sessions. It is a supporting signal: the
  engine works without it (`TEACHER_LEARNER_MODEL=none`).
- **No external AI service** is called; everything runs locally.

### Run the demo

```
# Terminal 1 — backend (http://localhost:8000)
cd backend
.venv/Scripts/uvicorn.exe skillforge.api.app:app --port 8000

# Terminal 2 — frontend (http://localhost:5173)
cd frontend
npm install
npm run dev
```

An empty database is seeded with a short sample learning history on
startup (`TEACHER_SEED_DEMO=false` to disable).

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
