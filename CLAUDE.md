# CLAUDE.md — Standing rules for SkillForge

SkillForge is a closed-loop system that teaches LLM agents procedural skills:
a human provides demonstrations, a Teacher agent extracts a structured skill
into a versioned "Skill Memory", a Learner agent attempts tasks in a
simulated environment, a deterministic Evaluator scores attempts, and the
Teacher diagnoses failures and patches the Skill Memory. Improvement is
measured on held-out tasks.

## Session start

- At the start of every session, read `PROGRESS.md`, and `PRD.md` if it
  exists in the repo root.
- For Phase 1 specifically, `docs/SPEC_PHASE1.md` holds the Phase 1 kickoff
  spec verbatim (environment interface, task generator, e-commerce refund
  policy R1-R10, evaluator output shape, task list, and gate). Use it as
  the source of truth for Phase 1 until `PRD.md` is added; once `PRD.md`
  exists, **`PRD.md` wins** on any conflict (as of this note, PRD.md
  Sections 6.2/6.3/7/12 are consistent with `docs/SPEC_PHASE1.md` — no
  conflicts found).
- Implement **only** the phase named in the user's latest message. Do not
  create code, folders, or stubs for later phases, even if they seem
  convenient or obviously needed later.
- Each phase ends at a verification gate. When you reach it, STOP and hand
  back control. Do not start the next phase until explicitly told to.
- Prefer small, working, tested code over breadth. If something is
  ambiguous, pick the simplest reasonable option and list it under
  "Decisions" in the end-of-phase summary. If a decision is costly to
  reverse, ask first.

## Stack

- Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest, ruff.
- Package lives in `backend/skillforge/`.
- Tests live in `backend/tests/`.

## Rules

- Tests must **never** require API keys. Use `MockProvider` for anything
  that would otherwise call a real LLM.
- Never hardcode model names or API keys. Read them from environment
  variables via the settings module (`skillforge.core.settings`). Keep
  `.env.example` up to date with every new variable.
- Every new module gets tests. Run `pytest` and `ruff check` before
  declaring a phase done.
- Ground truth for validation/test tasks must never be reachable from
  learner- or teacher-facing code. Keep it isolated (e.g. a separate field
  or module that only the Evaluator imports).

## End-of-phase summary format

Every phase ends with a message in this exact shape:

1. **What was built** — files, briefly.
2. **Decisions made and why.**
3. **Exact commands to verify the gate**, with expected output.
4. **Anything incomplete or risky.**
5. Update `PROGRESS.md` to mark the phase ready for review.

Then stop and wait.
