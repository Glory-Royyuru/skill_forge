# SkillForge — Progress

## Phase checklist

- [x] **Phase 0 — Ready for review.** Scaffold, config, DB, LLM provider
      layer, health endpoint.
      Gate: tests pass with no API keys; server starts; health ok.
      16/16 tests pass, ruff clean, server verified manually. Awaiting
      sign-off before starting Phase 1.
- [ ] **Phase 1.** E-commerce refund environment, seeded task generator with
      train/validation/test splits, deterministic evaluator.
      Gate: oracle agent scores 100%; same seed gives identical tasks.
- [ ] **Phase 2.** Learner tool-calling loop; baselines A (no training) and
      B (static skill); batch CLI.
      Gate: real run works; baseline B below ~85% or difficulty is
      increased.
- [ ] **Phase 3.** JSON demonstrations, Teacher skill extraction,
      clarifications, extraction fidelity metric.
      Gate: memory v1 saved; fidelity report.
- [ ] **Phase 4.** Diagnosis, Skill Memory patches, curriculum, training
      loop, versioning, leakage check.
      Gate: full session end to end; readable memory diffs.
- [ ] **Phase 5.** Experiment runner for all conditions, seeds, bootstrap
      CIs, report.
      Gate: comparison report on test split.
- [ ] **Phase 6.** Defect-injection suite for diagnosis accuracy.
      Gate: accuracy table.
- [ ] **Phase 7.** React UI.
      Gate: watch a session live, view a report.
- [ ] **Phase 8.** Second environment (file organization).
      Gate: same loop runs unchanged.
- [ ] **Phase 9.** Demonstration studio UI, skill library, transfer
      experiment.

## Decisions log

- (Phase 0) Repo scaffolded fresh; no PRD.md present yet — following the
  kickoff message as the spec of record until PRD.md is added.
- (Phase 0) `pyproject.toml` lives in `backend/` (not repo root), so the
  package root aligns with `backend/skillforge/`. All commands `cd` into
  `backend/` first (see Makefile / README).
- (Phase 0) No global DB/engine singletons. `Database` (in
  `db/database.py`) bundles an engine + session factory for one URL; the
  FastAPI app and CLI each construct their own from settings, and tests
  construct one against a temp SQLite file. Avoids cross-test state leakage
  without needing fixture teardown gymnastics.
- (Phase 0) `get_settings()` is deliberately uncached (no `lru_cache`) —
  settings are cheap to build and tests frequently change env vars between
  calls via `monkeypatch`.
- (Phase 0) All primary keys are plain autoincrement integers; JSON columns
  use SQLAlchemy's generic `JSON` type (stored as TEXT under SQLite).
  `skill_memory_versions.parent_version` and `interventions.resulting_version`
  are treated as version *numbers* (scoped to a skill), not foreign keys to
  row ids — the spec's column names were ambiguous on this point.
- (Phase 0) `llm_calls.session_id` is nullable, since LLM calls can happen
  outside a training session (e.g. ad hoc Teacher extraction, tests).
- (Phase 0) `OpenAIProvider`/`AnthropicProvider` import the `openai` /
  `anthropic` SDKs lazily inside `__init__` (not at module load), so the
  rest of the codebase — and all tests — import cleanly even though the
  packages are listed as dependencies.
- (Phase 0) Response cache (`llm/cache.py`) is a simple in-memory
  process-local dict keyed by a SHA-256 hash of the normalized request.
  Good enough for Phase 0; swappable for a persistent backend later without
  touching `LoggingLLMClient` call sites.
- (Phase 0) CLI uses stdlib `argparse` rather than adding a CLI framework
  dependency (click/typer) — only one subcommand exists so far.

