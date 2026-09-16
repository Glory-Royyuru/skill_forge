# Phase 1 spec (as given at kickoff)

This is the Phase 1 build spec pasted verbatim into the session that
implemented it. `PRD.md` is the overall source of truth for the project;
where the two differ, **PRD.md wins**. As of this spec being added,
PRD.md's Section 7 (E-commerce Refunds), Section 6.2/6.3 (Environment
Adapter / Task Generator), and Section 12 (Evaluator) are consistent with
everything below — no conflicts were found.

---

ENVIRONMENT INTERFACE
```python
class Environment(Protocol):
    name: str
    def reset(self, task: Task) -> State
    def get_state(self) -> State            # learner-visible view only
    def list_tools(self) -> list[ToolSpec]
    def execute_action(self, action: Action) -> ActionResult
    def evaluate(self) -> EvaluationResult   # uses hidden ground truth
```
Environments are pure Python, seeded, deterministic, no network.

TASK GENERATOR
Seeded generator producing tasks with hidden ground truth. Splits fixed once by seed and stored:
- train: Teacher may see these, their failures, and use them as examples.
- validation: used for mastery checks; Teacher sees scores only.
- test: held out; never shown to the Teacher; final reporting only.

E-COMMERCE REFUND ENVIRONMENT
Tools:
```
search_orders(query), view_order(order_id), view_customer(customer_id), view_policy(section), view_order_history(customer_id),
process_refund(order_id, amount, method)  # method: original_payment | store_credit
reject_refund(order_id, reason_code)
escalate(order_id, reason_code)
```
Terminal actions: process_refund, reject_refund, escalate. Exactly one per attempt.

Ground-truth policy (encoded in evaluator, not shown verbatim to learner):
- R1. Standard window: refund if days_since_delivery <= 30 (inclusive).
- R2. Damaged/defective items: window extends to 60 days.
- R3. VIP customers: +15 days on any window.
- R4. Final-sale items: never refundable, except damaged-on-arrival reported within 7 days.
- R5. Opened electronics (not damaged): refund 85% of item price.
- R6. Gift orders: refund as store credit only.
- R7. Refunds over $500 (after adjustments): must escalate, not process.
- R8. Already refunded orders: reject with already_refunded.
- R9. Customer's claimed date conflicts with system record: system record wins.
- R10. Customer with >= 3 refunds in the last 90 days: escalate.

Rules interact. Tasks include distractors: misleading customer messages, multiple similar orders, missing fields requiring a lookup.

EVALUATOR
Deterministic, pure Python, no LLM.
- success: final action, amount (±$0.01), method, and reason code all correct.
- critical: money issued when it should not be, OR wrong amount/method on an issued refund, OR processing something that required escalation.
- score: partial credit (correct decision type 0.5 + correct parameters 0.5).
- error_type: derived from diff with ground truth: wrong_decision, wrong_amount, wrong_method, missed_escalation, invalid_tool_sequence, no_final_action.

Output: `{"success", "score", "critical", "error_type", "expected", "actual", "rules_involved"}`
rules_involved = the rule IDs the ground truth depended on.

---

## Phase 1 task list (as given at kickoff)

Before coding: write a 3-5 bullet plan in PROGRESS.md under Phase 1. Then build:

- The Environment interface and the e-commerce environment with all tools. Validate tool args against schemas; invalid calls return an error result and are recorded, not executed.
- `resolve_ground_truth(order, customer, history, request) -> Expected` as a single pure function. Where rules conflict and the spec is silent, choose the most conservative interpretation, and document each choice in the Decisions log and as a comment next to the code.
- The evaluator per spec.
- `get_state()`, tool results, and task objects given to agents must never expose ground truth. Add a test proving this.
- Unit tests: one or more per rule R1-R10, plus these interactions: VIP+damaged; damaged+final-sale within and after 7 days; opened electronics as a gift; refund over $500 after the 85% adjustment; day 30 and 31; damaged at day 60 and 61; VIP at day 45 and 46; system date overriding customer's claimed date; 3+ recent refunds.
- Task generator: seeded, reproducible, oversamples rule interactions and boundary days, includes the distractors. Tag tasks with rule IDs. Store splits in the tasks table.
- OracleAgent (tests/tooling only; may use resolve_ground_truth) acting through the real tools. RandomAgent choosing random valid tools.
- CLI:
  ```
  python -m skillforge envs generate --env ecommerce --seed 42 --n 300
  python -m skillforge envs stats
  python -m skillforge envs run-agent --agent oracle --split validation --n 50
  python -m skillforge envs run-agent --agent random --split validation --n 50
  ```
- Add a note in PROGRESS.md under Phase 2: the Anthropic provider's tool-result mapping must be implemented properly (tool_use / tool_result blocks) with tests before the learner loop is considered done.

### Gate

- pytest and ruff check . (no API keys set) both pass.
- A test proving the same seed generates identical tasks.
- OracleAgent on 200 tasks: must be 100%. If not, find and fix the bug in the policy function, evaluator, or oracle, then re-run — don't lower the bar.
- RandomAgent on 200 tasks: report the score (should be low).
- `envs stats`: every rule R1-R10 must appear in every split. If not, adjust the generator.

---

## Phase 1.1 amendments (fix pass after the Phase 1 gate)

Phase 1 passed its gate, but `envs stats` on the real generated distribution
surfaced problems that would have undermined Phase 2 (a static baseline
scoring well mostly by memorizing a skewed task mix, not by understanding
the policy). This fix pass, applied without changing the Environment
Protocol or the core R1-R10 policy:

**Evaluator — two new error types** (`evaluator.py`):
- `wrong_order`: a terminal action on an `order_id` other than the task's
  target now **ends the episode** (the environment no longer refuses/
  retries it — see the `order_id_mismatch` replacement below) and is
  classified `wrong_order`, critical iff the action was `process_refund`.
- `wrong_reason_code`: correct decision type (reject/escalate) but the
  wrong `reason_code` — score 0.5, never critical. This replaces what
  Phase 1 had folded into `wrong_decision` for the same case.
- `evaluate_attempt` gained a required `target_order_id` parameter.

**Environment — `order_id_mismatch` removed** (`environment.py`):
Phase 1's `_terminal_order_id_check` refused a terminal call on the wrong
order (`ok=False`, non-terminal, agent could retry). Phase 1.1 replaces
this: `_tool_process_refund`/`_tool_reject_refund`/`_tool_escalate` now
execute unconditionally once schema-valid, `ok=True, terminal=True`,
regardless of `order_id`. Correctness of the order is now purely an
evaluator concern (`wrong_order` above), not something the environment
gates on. See PROGRESS.md's Decisions log for the full reasoning.

**Generator — stratified, not just recipe+random** (`generator.py`):
Rewritten to hit, per split: decision-bucket distribution (process_full
~25%, process_adjusted ~20%, reject ~30%, escalate ~25%, all ±5%),
interaction share (2+ rules excluding R1/R9) >= 40%, R1-only share <= 20%,
and per-rule minimums at the default size (n=1400: train >= 60/rule,
validation/test >= 20/rule each). `DEFAULT_N` changed from 300 to 1400
accordingly. Achieved by exact weighted allocation (not rejection
sampling) across a menu of ~28 classified "cells", on top of the original
18 recipes (still guaranteeing every boundary day/named interaction).
Every task's `(request, initial_state)` is unique by construction (a
single globally-incrementing index across all splits), verified by a
dedicated test.

**CLI — `envs stats` reports and enforces all of the above**, exiting
non-zero with an itemized violation list if any target is missed.
