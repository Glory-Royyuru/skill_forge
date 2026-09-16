# SkillForge — Progress

## Phase checklist

- [x] **Phase 0 — Done.** Scaffold, config, DB, LLM provider layer, health
      endpoint.
      Gate: tests pass with no API keys; server starts; health ok.
      Re-verified: 16/16 tests pass, ruff clean, server started and
      `/api/health` returned `{"status":"ok","database":"ok"}` (200), CLI
      `health` command returned exit 0. See PRD.md (added to repo root) and
      `docs/SPEC_PHASE1.md` for the Phase 1 spec.
- [x] **Phase 1 — Done.** E-commerce refund environment, seeded task
      generator with train/validation/test splits, deterministic evaluator.
      Gate: oracle agent scores 100%; same seed gives identical tasks.

      **Gate results:** 103/103 tests pass, ruff clean. OracleAgent
      100.000% (200/200) on validation via
      `envs run-agent --agent oracle`; critical_rate 0.000%. RandomAgent
      0.000% (200/200) success, mean_score 0.000, critical_rate 0.000%
      (it can never target the right order id, so it can't accidentally
      issue money — see Decisions log). `envs stats` shows every rule
      R1-R10 present in every split at both n=300 and n=1400. Determinism
      verified both by a dedicated unit test and by a live
      `generate_tasks(seed=42, n=300)` called twice, asserted
      byte-identical.
      **Superseded by Phase 1.1** (below): the "RandomAgent can't
      accidentally issue money" claim above no longer holds once
      `wrong_order` was added — a wrong-order `process_refund` is now
      legitimately critical. Kept here for the historical record of what
      Phase 1's gate actually measured.
- [x] **Phase 1.1 — Done.** Fix pass after the Phase 1 gate: `envs stats`
      on the real distribution surfaced two problems that would have
      undermined Phase 2 — (1) a wrong-order terminal call was refused and
      retried rather than scored, so an agent could never be penalized for
      targeting the wrong order; (2) task generation was recipe+random
      rather than stratified, so the decision mix, interaction share, and
      per-rule counts were whatever fell out of random sampling, not
      controlled targets.
      Gate: pytest + ruff clean; regenerate seed=7 n=1400; `envs stats`
      exits 0; Oracle 100% / Random reported on 200 validation tasks.
      See the Decisions log for what changed and why, and
      `docs/SPEC_PHASE1.md`'s "Phase 1.1 amendments" section for the full
      technical summary.

      **Plan:**
      - `envs/base.py` + `envs/agents.py`: generic `Environment` Protocol,
        `Task`/`State`/`Action`/`ActionResult`/`EvaluationResult` types
        (reusing `llm.types.ToolSpec` for tool schemas), a generic
        `RandomAgent` (drives purely off JSON-schema tool specs, no env
        knowledge) and a `run_episode()` harness — reusable unchanged for
        Phase 8's second environment.
      - `envs/ecommerce/{models,policy,evaluator,environment,oracle,
        generator,persistence}.py`: domain dataclasses; a single pure
        `resolve_ground_truth()` encoding R1-R10 with every ambiguous call
        documented below; a deterministic `evaluate_attempt()`; the
        `Environment` implementation with schema-validated tools; an
        `OracleAgent` that recomputes `resolve_ground_truth()` from the
        same world facts the environment uses (never touches the hidden
        `ground_truth_json` answer) and acts through the real tools.
      - Strict separation: `initial_state_json` = learner-reachable world
        facts (order/customer/history — what tools reveal piecemeal);
        `ground_truth_json` = only the hidden *decision*
        (`Expected`: action/amount/method/reason_code/rules_involved),
        touched only by `evaluate()`. A dedicated test asserts no tool
        output or `get_state()` ever contains decision fields.
      - Seeded `generate_tasks()`: a fixed set of "recipe" scenarios (one
        per rule/boundary/interaction in the gate's test list) each
        emitted once per split for *guaranteed* per-split rule coverage,
        topped up with fully-randomized filler scenarios (with
        distractors: extra orders, a customer-claimed date that can
        disagree with the system record, unrelated order mentions) for
        volume/diversity. Splits assigned by shuffling with the seeded
        RNG, not wall-clock/hash-based.
      - CLI (`envs generate|stats|run-agent`) persists into the existing
        `tasks` table (delete-then-reinsert per `(environment, seed)` for
        idempotency) and reports rule-coverage / oracle / random scores.
- [ ] **Phase 2.** Learner tool-calling loop; baselines A (no training) and
      B (static skill); batch CLI.
      Gate: real run works; baseline B below ~85% or difficulty is
      increased.
      **Note (added during Phase 1):** the Anthropic provider's tool-result
      mapping (`_split_system` in `llm/anthropic_provider.py`) currently
      does a simplified `tool` → `user` role pass-through with no real
      `tool_use`/`tool_result` content blocks. This must be implemented
      properly, with tests, before the Phase 2 learner loop is considered
      done — the current mapping will not round-trip multi-turn tool use
      correctly against the real Anthropic Messages API.
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

- (Phase 1) **Policy interpretations** (all in `envs/ecommerce/policy.py`,
  each also documented inline as a code comment at the branch it affects):
  - R8 (already refunded) is checked first and short-circuits every other
    rule — unambiguous, and a reject can't wrongly issue money either way.
  - R4's final-sale check runs before the standard/damaged/VIP window
    logic, as its own gate with a fixed 7-day damaged-on-arrival exception.
  - **R3's VIP +15 day bonus does NOT extend R4's 7-day final-sale
    exception window**, even though R3 says "any window." Conservative
    reading: extending it would let more final-sale refunds through,
    increasing the risk of wrongly issuing money on items policy calls
    non-refundable. `R3` never applies to R2/R1's window formula either
    unless that formula is actually in play (final-sale bypasses it).
  - **R7 (>$500) and R10 (>=3 refunds/90d) only ever convert a would-be
    `process_refund` into `escalate`.** They never turn an already-decided
    reject (already-refunded, final-sale, window-expired) into an
    escalate, since no money is at risk in a reject either way — escalation
    exists to add human oversight where money would otherwise move.
  - R7's threshold applies to the *post-adjustment* amount (after R5's 85%
    cut), and "over $500" is strictly `>`, not `>=` — exactly $500.00
    processes normally.
  - `ItemCondition.DAMAGED` is used uniformly for both R2 ("damaged")
    and R4's "damaged-on-arrival" exception — the spec never distinguishes
    a general damage flag from a delivery-damage flag, so one field covers
    both.
  - `view_policy`'s handbook text is in natural customer-service language
    (no "R1"/"R2" rule ids) — "not shown verbatim to the learner" is read
    as protecting the evaluator's internal rule bookkeeping, not as a
    reason to cripple a tool the spec explicitly lists as real.
  - ~~A terminal action (`process_refund`/`reject_refund`/`escalate`) whose
    `order_id` doesn't match the request's target order is rejected as
    `order_id_mismatch` and does **not** end the episode (the agent can
    retry against the right order).~~ **Superseded in Phase 1.1** — see
    below: it now ends the episode and is scored `wrong_order`.
  - A reason-code mismatch on an otherwise-correct `reject_refund`/
    `escalate` (right action, wrong reason) has no dedicated bucket in the
    given `error_type` vocabulary (`wrong_decision, wrong_amount,
    wrong_method, missed_escalation, invalid_tool_sequence,
    no_final_action`), so it's folded into `wrong_decision`.
  - When both R7 and R10 fire on the same task, `reason_code` reports
    `"frequent_refunds"` (a fixed, documented tie-break) but
    `rules_involved` still lists both `R7` and `R10`.
  - **R9 bug found and fixed during Phase 1 verification**: `rules_involved`
    never contained `"R9"` because R9 ("system record wins") is enforced
    structurally — `resolve_ground_truth` never reads the customer's claimed
    date at all for eligibility — so there was no branch to tag it from.
    `envs stats` showed R9 missing from every split. Fixed by reading
    `request.claimed_days_since_delivery` in exactly one place: to tag
    `"R9"` into `rules_involved` when it actually disagrees with
    `order.days_since_delivery`. This tagging never influences the
    eligibility decision itself (still `order.days_since_delivery` only),
    so "system record wins" still holds by construction.
- (Phase 1) Strict separation between `Task.initial_state` (the simulated
  "world" — order/customer/history/distractors; legitimately
  learner-reachable piece by piece through tools) and `Task.ground_truth`
  (only the hidden `Expected` decision: action/amount/method/reason_code/
  rules_involved). The environment recomputes `Expected` from
  `initial_state` in `reset()` rather than reading `Task.ground_truth` at
  all, so evaluate() is the only code path that ever touches it.
  `test_environment.py::test_ground_truth_never_reachable_from_state_or_tool_outputs`
  and `::test_task_ground_truth_contains_no_world_leak_and_no_extra_facts`
  are the tests proving this.
- (Phase 1) `OracleAgent` is handed the `Task` directly (not routed through
  `get_state()`/tool calls) and calls `resolve_ground_truth` on
  `Task.initial_state` — the same world facts the environment itself
  parses. It never touches `Task.ground_truth`. It still "acts through the
  real tools": its single computed `Action` is submitted to
  `Environment.execute_action` like any other agent's, so the environment's
  validation/scoring plumbing is genuinely exercised.
- (Phase 1) `RandomAgent` (in `envs/agents.py`) is fully environment-
  agnostic — it drives off `ToolSpec.parameters` JSON-schema shape alone,
  with no e-commerce-specific knowledge, so it (and the `run_episode`
  harness) is reused unchanged in Phase 8's second environment.
- (Phase 1) Task generation is a fixed set of "recipe" scenarios — one per
  rule/boundary/interaction the gate lists — each instantiated once per
  split, so every rule is *guaranteed* present in every split regardless of
  `n` or RNG luck, topped up with fully-randomized filler scenarios (with
  distractors) for volume/diversity. Splits for filler tasks are assigned
  by shuffling positions with the same seeded RNG and slicing by ratio.
  ~~Minimum `n` is `len(RECIPES) * 3` (54)~~ **superseded in Phase 1.1**
  (stratification raised the real minimum to ~140 — see below);
  `generate_tasks` still raises `ValueError` below the minimum rather than
  silently producing a split with missing rule coverage.
- (Phase 1) `tasks.ground_truth_json` stores exactly the `Expected` shape
  (`asdict()` of the dataclass, including `rules_involved`) — no separate
  `rule_ids` column was needed. `envs stats` reads `rules_involved`
  straight out of the DB for its coverage report; this is dev/CLI tooling
  reading the DB directly, not a learner- or teacher-facing code path, so
  it doesn't violate the ground-truth-isolation rule (PRD ties
  `rules_involved` visibility restrictions specifically to the *Teacher*,
  for train vs. non-train splits — a concern for Phase 3+, not for this
  CLI report).
- (Phase 1) Ruff's `line-length` was bumped from 100 to 110 (repo-wide,
  `backend/pyproject.toml`) — at 100 there were 64 wrapping violations,
  many in test files where the extra width reads better than a forced
  wrap. All remaining violations at 110 were fixed by hand rather than
  bumping further. Also applied ruff's `UP042` suggestion: the `(str,
  Enum)` mixin classes in `envs/ecommerce/models.py` became `StrEnum`
  (stdlib, Python 3.11+) — same JSON-serialization behavior, less
  boilerplate.
- (Phase 1.1) **`wrong_order` ends the episode instead of being refused.**
  Phase 1's environment refused a terminal call on the wrong order
  (`order_id_mismatch`, non-terminal, free retry) reasoning that the given
  `error_type` vocabulary had "no slot" for it. The user's Phase 1.1 spec
  corrected this directly: a terminal action on the wrong order now
  executes (the environment no longer knows or cares which order is
  "right" — that's not its job) and `evaluate_attempt` classifies it as
  `wrong_order`, critical iff the action was `process_refund`. This is
  more realistic (a real refund tool doesn't grant free retries for
  targeting the wrong order) and — because `RandomAgent`'s fabricated
  order ids essentially never match the target — it also fixed a
  Phase 1 blind spot: RandomAgent could never previously be critical at
  all, which was a weaker baseline than intended for Phase 2 comparisons.
- (Phase 1.1) **`wrong_reason_code` split out from `wrong_decision`.**
  Same-action-wrong-reason (reject/escalate) now gets its own
  `error_type` instead of folding into `wrong_decision`, giving Phase 4's
  diagnosis step a real signal to distinguish "picked the wrong action
  entirely" from "picked the right action, wrong justification."
- (Phase 1.1) **Generator rewritten as stratified allocation, not
  rejection sampling.** `envs stats` on Phase 1's recipe+random generator
  showed the decision mix, interaction share, and per-rule counts were
  whatever random sampling happened to produce — no control over them.
  Rejection sampling (generate randomly, keep only what's needed) was
  considered and rejected: hitting *exact* percentage targets that way
  requires either many discarded samples near the end (slow, and awkward
  to keep deterministic) or accepting drift. Instead: a weighted menu of
  ~28 "cells", each hand-classified into (decision bucket, interaction
  flag, R1-only flag) and self-checked against `resolve_ground_truth`'s
  actual output at generation time (`AssertionError` if a cell's
  assumption about its own output is wrong — this caught real bugs during
  tuning, see below). Per split: compute each bucket's target count from
  the 25/20/30/25% split, subtract what the 18 fixed recipes already
  contribute, then allocate the remainder across that bucket's cells by
  weight by exact largest-remainder rounding — not sampled, so a split's
  bucket percentages land within a fraction of a point of target at any
  `n`, every run, every seed.
- (Phase 1.1) **`DEFAULT_N` changed from 300 to 1400.** The per-rule
  minimums (60 train / 20 val+test) are spec'd "at the default size
  (220)" — chosen so validation and test both land on exactly 220 tasks
  by construction (`DEFAULT_SPLIT_COUNTS = {"train": 960, "validation":
  220, "test": 220}`, summing to 1400). `envs generate`'s `--n` still
  defaults to `DEFAULT_N`, so plain `envs generate --seed X` remains the
  "guaranteed to pass every target" path.
- (Phase 1.1) **Per-rule minimums, and the CLI's stricter checks, are
  hard-enforced only at `n == DEFAULT_N`.** Scaling the 60/20/20 minimums
  proportionally to arbitrary `n` sounds appealing but interacts badly
  with integer rounding in the cell allocator: e.g. `n=180` failed R8's
  scaled minimum by one task while `n=160` and `n=300` both passed — a
  real but harmless artifact of proportional rounding, not a generator
  bug. Since the spec only promises the minimums "at the default size,"
  `generate_tasks()` hard-fails only there; for any other `n` it applies a
  much weaker sanity check (every rule present at least once). `envs
  stats`, by contrast, *always* reports and flags shortfalls at whatever
  size is actually persisted (see next entry) — that's intentionally
  stricter than the generator's own internal guarantee.
- (Phase 1.1) **`envs stats` validates unconditionally, even below
  `DEFAULT_N`.** At `n=300` (a size that generates successfully),
  validation/test's interaction share lands at ~38%, just under the 40%
  floor — an inherent consequence of the 18 fixed recipes (only ~17%
  interaction) making up a larger fraction of a smaller split, not a bug.
  `envs stats` reports this as a real, honest failure rather than
  suppressing it below some size threshold: the tool's job is to describe
  what's actually in the database, and the CLI's own `--n` default already
  steers users to the one size (1400) where every target is guaranteed.
  Existing tests/call sites using small `n` (54, 60, 100) were bumped to
  clear the new ~140 minimum; stratification-heavy tests use
  `DEFAULT_N` explicitly.
- (Phase 1.1) **R9 tagging bug, round two.** While tuning cell weights to
  clear the per-rule minimums, the R9 crosscutting overlay (applied to
  every cell to add a claimed-date conflict ~35% of the time) was
  initially applied unconditionally, including to the two cells declared
  `r1_only=True` — which silently broke their own promise
  (`rules_involved` became `["R1", "R9"]`, not `["R1"]`). The cell
  self-check assertion (see above) caught this immediately on the first
  real generation run, before it could reach a test file. Fixed by adding
  an `allow_r9` flag, `False` for `r1_only` cells only.
- (Phase 0) Repo scaffolded fresh; no PRD.md present yet — following the
  kickoff message as the spec of record until PRD.md is added.
- (Phase 0, verification pass) PRD.md appeared in the repo (added via a
  GitHub web upload, commit `2aafa74`) between the original Phase 0 build
  and this verification pass; git history also shows Phase 0 itself was
  already committed (`b0847be` "feat: complete phase 0 foundation", merged
  via `d95ae2a`) with content byte-identical to what this session
  re-verified. Read PRD.md in full: it is consistent with (a superset of)
  the Phase 1 spec given for this session — same Environment protocol,
  same R1-R10 policy, same evaluator output shape, same data model. No
  conflicts to reconcile. Since the working tree already matched HEAD, no
  new "Phase 0: scaffold, DB, LLM provider layer, health endpoint" commit
  was created (would have been empty); this PROGRESS.md update is the
  honest follow-up commit instead.
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

