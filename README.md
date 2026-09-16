# SkillForge

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
