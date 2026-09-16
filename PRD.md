# SkillForge — Product Requirements Document

**Version:** 2.0 (final)
**Type:** Closed-loop teaching system for LLM agents, with a research evaluation harness
**Stack:** Python 3.11+, FastAPI, SQLite → PostgreSQL, React + Vite, provider-agnostic LLM layer

---

## 1. Summary

SkillForge teaches an LLM learner agent a procedural skill and **measures whether it actually improved**.

A human provides demonstrations (and optionally explanations) of a task in a controlled environment. A Teacher agent extracts a structured skill. The Learner attempts tasks. A deterministic Evaluator scores each attempt against ground truth. When the learner fails, the Teacher diagnoses the cause and produces an intervention that **edits the learner's skill memory**. The learner retries on new tasks. Mastery is measured only on a held-out set the Teacher never sees.

**Core loop:** Demonstrate → Extract → Practice → Evaluate → Diagnose → Intervene (update skill memory) → Retry → Measure on held-out set

**Central claim to test:** Diagnosis-driven, targeted updates to an agent's skill memory produce better held-out performance than static instructions, raw demonstrations, or self-reflection.

---

## 2. What "learning" means in SkillForge

The learner is a stateless LLM. SkillForge does not change model weights. **All learning lives in the Skill Memory**, a versioned artifact injected into the learner's context on every attempt.

Skill Memory contains:

| Part | Description |
|---|---|
| `skill` | Structured skill: goal, procedure, rules, exceptions (Section 9) |
| `lessons` | Short, specific notes added by interventions ("Check `item_condition` before applying the 30-day window") |
| `examples` | Curated worked examples and counterexamples drawn from the **training** pool only |
| `version` | Integer, incremented on every change, with a diff and the reason for change |

An intervention is a **patch** to Skill Memory (add/edit/remove a rule, lesson, or example). Every patch is stored with the failure that caused it. This makes learning inspectable, reversible, and comparable across versions.

Skill Memory has a size budget (configurable, default ~3,000 tokens). When it is exceeded, the Teacher must consolidate. This prevents "learning" from degenerating into an ever-growing list of special cases.

---

## 3. Goals

- **G1** Extract structured skills from demonstrations + explanations.
- **G2** Run learner agents with tool use in sandboxed environments.
- **G3** Evaluate attempts deterministically against ground truth.
- **G4** Diagnose failures and generate targeted Skill Memory patches.
- **G5** Measure improvement on a held-out set with proper statistics.
- **G6** Compare against strong baselines.
- **G7** Show the same architecture works in a second, unrelated environment.

## 4. Non-goals

- Training or fine-tuning models.
- Open-web or unrestricted computer use.
- Real enterprise integrations.
- A general chatbot or human education product.
- Claims of human-like learning.

---

## 5. Users

- **Researcher / student (primary for v1):** runs experiments, compares methods.
- **AI developer:** wants an agent to reliably follow a workflow.
- **Domain expert:** provides demonstrations and resolves ambiguities.

---

## 6. Architecture

```text
React UI ──► FastAPI
               │
   ┌───────────┼─────────────┬──────────────┐
   ▼           ▼             ▼              ▼
Teacher     Learner     Evaluator     Experiment Runner
   │           │             │              │
   │           ▼             │              │
   │     Tool Executor       │              │
   │           │             │              │
   └──────► Environment ◄────┘              │
               │                            │
               ▼                            ▼
        Database (SQLite/Postgres)     Results / Reports
               ▲
               │
        LLM Provider Layer (OpenAI | Anthropic | Mock)
```

### 6.1 LLM Provider Layer

A single interface (`LLMProvider.complete(messages, tools, model, temperature, seed)`) with implementations:

- `OpenAIProvider`
- `AnthropicProvider`
- `MockProvider` — deterministic scripted responses for tests; **all tests run without API keys**.

Model names come from config/env, never hardcoded. Every call is logged with role (teacher/learner), tokens, latency, and cost estimate. Responses may be cached by hash for reproducibility.

### 6.2 Environment Adapter

Every environment implements:

```python
class Environment(Protocol):
    name: str
    def reset(self, task: Task) -> State: ...
    def get_state(self) -> State: ...          # learner-visible view
    def list_tools(self) -> list[ToolSpec]: ...
    def execute_action(self, action: Action) -> ActionResult: ...
    def evaluate(self) -> EvaluationResult: ... # uses hidden ground truth
```

Environments are pure Python, seeded, deterministic, and have no network access.

### 6.3 Task Generator

Each environment has a seeded generator producing tasks with **hidden ground truth**. Tasks are split once, by seed, into:

- `train` — the Teacher may see these, their failures, and use them as examples.
- `validation` — used for mastery checks during training; Teacher sees scores only, not task contents.
- `test` — held out. Never shown to the Teacher. Used only for final reporting.

Splits are fixed and stored. A leakage check verifies no test task (or near-duplicate with identical relevant attributes) appears in Skill Memory examples.

---

## 7. Environment 1 — E-commerce Refunds

The policy must be hard enough that a written rule list is **not** sufficient for a strong model to score ~100%. If Baseline B exceeds ~85% on validation, difficulty is increased before building the Teacher (see Phase 2 gate).

### Tools

```text
search_orders(query)          view_order(order_id)
view_customer(customer_id)    view_policy(section)
view_order_history(customer_id)
process_refund(order_id, amount, method)   # method: original_payment | store_credit
reject_refund(order_id, reason_code)
escalate(order_id, reason_code)
```

### Ground-truth policy (encoded in evaluator, not shown verbatim to the learner)

1. Standard window: refund if `days_since_delivery <= 30` (inclusive).
2. Damaged/defective items: window extends to 60 days.
3. VIP customers: +15 days on any window.
4. Final-sale items: never refundable, except damaged-on-arrival reported within 7 days.
5. Opened electronics (not damaged): refund 85% of item price.
6. Gift orders: refund as store credit only.
7. Refunds over $500: must escalate, not process.
8. Already refunded orders: reject with `already_refunded`.
9. Customer's claimed date conflicts with system record: system record wins.
10. Customer with ≥3 refunds in the last 90 days: escalate.

Rules interact (VIP + damaged + opened electronics + gift). Tasks include distractors: misleading customer messages, multiple similar orders, missing fields requiring a lookup.

### Scoring

- `success`: final action, amount (±$0.01), method, and reason code all correct.
- `critical_error`: money issued when it should not be, or amount/method wrong on an issued refund, or processing something that required escalation.
- `score`: partial credit (correct decision type 0.5, correct parameters 0.5).
- `error_type`: machine-derived from diff with ground truth (e.g. `wrong_decision`, `wrong_amount`, `wrong_method`, `missed_escalation`, `invalid_tool_sequence`, `no_final_action`).

## 8. Environment 2 — File Organization (Phase 8)

Tools: `list_files, read_file, create_folder, move_file, rename_file, delete_duplicate`.
Hidden rules: classification by content (invoice / receipt / report / personal), naming convention `YYYY-MM-DD_type_vendor.ext`, duplicates detected by content hash, ambiguous files go to `_review/`.
Evaluator compares final filesystem tree to ground truth.

---

## 9. Skill Representation

```json
{
  "name": "Customer Refund Processing",
  "goal": "Resolve refund requests according to policy",
  "preconditions": ["A refund request references an order"],
  "procedure": ["Locate order", "Check customer status", "Determine applicable window", "Decide action", "Execute with correct parameters"],
  "rules": [
    {"id": "R1", "when": "days_since_delivery <= window", "then": "eligible", "notes": "window=30 default"}
  ],
  "exceptions": [
    {"id": "E1", "when": "item_condition == damaged", "then": "window = 60"}
  ],
  "open_questions": ["Is day 30 inclusive?"],
  "confidence": {"R1": 0.9, "E1": 0.6}
}
```

Rules are natural-language conditions (not executable). `open_questions` are surfaced to the human.

---

## 10. Demonstrations & Extraction

### v1 format: JSON traces (no recording UI yet)

```json
{
  "task_id": "demo-003",
  "request": "Customer says headphones arrived broken, delivered 41 days ago",
  "actions": [
    {"tool": "search_orders", "args": {"query": "..."}, "result": {...}},
    {"tool": "process_refund", "args": {"order_id": "...", "amount": 89.99, "method": "original_payment"}}
  ],
  "explanation": "Damaged items get 60 days, so 41 days is fine."
}
```

Requirements:
- A skill needs **multiple demonstrations including rejections and escalations**. A single positive demo cannot reveal a threshold.
- Explanations are optional but supported and encouraged.
- The Teacher lists ambiguities as `open_questions`; a human answers them (CLI or UI). Answers are stored as clarifications.

### Extraction fidelity metric

Each environment ships a ground-truth rule list (for measurement only). After extraction, compute:
- rule recall / precision (LLM-judged match + human spot-check),
- number of open questions and how many a human resolved.

---

## 11. Learner Agent

Receives: task request, tool specs, current Skill Memory (or baseline-specific context), learner-visible state.
Runs a tool-calling loop with a max step limit (default 15). Must end with exactly one terminal action (`process_refund | reject_refund | escalate`) or the attempt is `no_final_action`.
Never receives ground truth or evaluator output during the attempt.

---

## 12. Evaluator

Deterministic, pure Python, no LLM. The Teacher is never the source of truth for pass/fail.
Output:

```json
{"success": false, "score": 0.5, "critical": true, "error_type": "wrong_method",
 "expected": {...}, "actual": {...}, "rules_involved": ["R6"]}
```

`rules_involved` is derived from which policy branches the ground truth took. It is available to the Teacher only for **train** tasks.

---

## 13. Teacher Agent

Functions:
1. **Extract** skill from demonstrations (Section 10).
2. **Diagnose** a failed train attempt: inputs are task, learner trajectory, evaluator output, current Skill Memory. Output:
   ```json
   {"category": "knowledge|decision|planning|execution|exception|generalization",
    "root_cause": "...", "evidence": ["step 3: ignored item_condition"], "confidence": 0.7}
   ```
3. **Intervene**: produce a Skill Memory patch. Allowed patch ops: `add_rule, edit_rule, add_exception, add_lesson, add_example, add_counterexample, remove_item, consolidate`. Examples must reference train tasks only.
4. **Curriculum**: choose next train tasks, weighted toward the diagnosed weakness (e.g. more gift orders after a `wrong_method` failure).
5. **Ask the human** when confidence < threshold or diagnoses conflict.

### Failure categories (with disambiguation rules)

| Category | Use when |
|---|---|
| knowledge | Rule is missing or wrong in Skill Memory |
| decision | Rule is present and correct, but learner applied it wrongly to the facts |
| planning | Learner skipped a needed lookup or acted before gathering facts |
| execution | Correct decision, wrong tool/arguments/format |
| exception | Base rule applied correctly but an exception in memory was ignored |
| generalization | Learner succeeds on seen patterns but fails on a new combination |

Check order: knowledge → planning → exception → decision → execution → generalization. First match wins.

---

## 14. Training Loop

```text
init Skill Memory from extraction
repeat until stop:
    task ← curriculum.next(train)
    attempt ← learner.run(task, memory)
    result ← evaluator.evaluate()
    if fail:
        diagnosis ← teacher.diagnose(...)
        patch ← teacher.intervene(...)
        memory ← apply(patch)  (version++)
    every K attempts: run validation subset → record score
stop when: validation ≥ mastery threshold for 2 consecutive checks,
           OR attempt budget exhausted, OR token budget exhausted
final: run full test set once with frozen memory
```

## 15. Mastery

Computed on the **test** set with frozen Skill Memory, n ≥ 50 tasks, ≥ 3 seeds.

Default criteria (configurable):
- Task success ≥ 90%
- Critical error rate ≤ 2%
- Success on exception-involving tasks ≥ 85%

Report mean ± std (or 95% CI) across seeds. Status: `MASTERED | LEARNING | NEEDS_TRAINING`.

---

## 16. Research Design

**Question:** Does diagnosis-driven Skill Memory patching improve held-out skill acquisition over simpler methods, and at what cost?

### Conditions (same learner model, same attempt budget where applicable)

| ID | Condition | Learner context |
|---|---|---|
| A | No training | Task + tools + short policy summary only |
| B | Static skill | Extracted skill, never updated |
| C | Raw demos (few-shot) | Demonstration traces, no extraction |
| D | Generic feedback | Skill + "your last attempt was wrong, the correct action was X" appended |
| E | Self-reflection (Reflexion-style) | Learner writes its own lessons after each failure; no teacher |
| F | **SkillForge** | Diagnosis + targeted patches + curriculum |
| F-ablations | F without diagnosis; F without curriculum | For attribution |

### Metrics

- Test success rate, critical error rate, exception-task success
- Learning efficiency: train attempts to reach validation threshold
- Cost: total tokens and $ (teacher + learner)
- Extraction fidelity (Section 10)
- **Diagnosis accuracy** via defect injection (Section 17)
- Skill Memory size over time
- Transfer: memory trained with model X evaluated with model Y
- Retention/stability: same frozen memory re-run later, different seeds

### Statistics
- ≥ 3 seeds per condition; bootstrap 95% CI; paired comparison on identical test tasks.
- Temperature and model versions recorded in every run.
- No results numbers in documents until experiments produce them.

---

## 17. Diagnosis Validation (Defect Injection)

Start from a Skill Memory that achieves high validation success, then inject a known defect:

| Injected defect | Expected category |
|---|---|
| Delete rule R6 (gift → store credit) | knowledge |
| Change VIP bonus from +15 to +5 | knowledge |
| Remove "look up customer" from procedure | planning |
| Corrupt tool description for `process_refund.method` | execution |
| Delete exception E1 (damaged → 60 days) | exception |

Measure: does the Teacher's diagnosis match the category and identify the affected rule? Does its patch restore performance?

---

## 18. Data Model

```text
agents(id, name, provider, model, config_json, created_at)
environments(id, name, version)
skills(id, name, environment_id, created_at)
skill_memory_versions(id, skill_id, version, content_json, parent_version, patch_json, reason, created_at)
demonstrations(id, skill_id, trace_json, explanation, created_at)
clarifications(id, skill_id, question, answer, created_at)
tasks(id, environment_id, seed, split, request, initial_state_json, ground_truth_json)
training_sessions(id, skill_id, agent_id, condition, status, config_json, created_at)
attempts(id, session_id, task_id, memory_version, trajectory_json, result_json, tokens, cost, created_at)
diagnoses(id, attempt_id, category, root_cause, evidence_json, confidence)
interventions(id, diagnosis_id, patch_json, resulting_version)
evaluations(id, session_id, split, memory_version, seed, metrics_json, created_at)
llm_calls(id, session_id, role, provider, model, input_tokens, output_tokens, latency_ms, cost, cache_hit, created_at)
experiments(id, name, config_json, status, created_at)
```

`ground_truth_json` is never returned by any learner- or teacher-facing API for test/validation tasks.

---

## 19. API (v1)

```http
GET  /api/health
GET  /api/environments
POST /api/environments/{name}/tasks/generate
GET  /api/tasks?split=train

POST /api/agents            GET /api/agents
POST /api/skills            GET /api/skills        GET /api/skills/{id}
POST /api/skills/{id}/demonstrations
POST /api/skills/{id}/extract
GET  /api/skills/{id}/memory?version=
POST /api/skills/{id}/clarifications

POST /api/training                     GET /api/training/{id}
POST /api/training/{id}/step           # one attempt → eval → (diagnose → patch)
POST /api/training/{id}/run            # background loop
GET  /api/training/{id}/attempts

POST /api/experiments                  GET /api/experiments/{id}
GET  /api/experiments/{id}/report
```

A CLI (`python -m skillforge ...`) mirrors key operations so experiments don't require the UI.

---

## 20. Frontend (minimal first)

- `/` — skills, sessions, latest metrics
- `/skills/:id` — Skill Memory viewer with version history and diffs; open questions
- `/training/:id` — live attempts: trajectory, evaluator result, diagnosis, patch
- `/experiments/:id` — condition comparison table, learning curve, CI bars, cost
- Later: `/demonstrate/:id` interactive recording studio

---

## 21. Safety

- Environments are in-process simulations; no network, no filesystem outside a temp sandbox.
- Tools validated against schemas; invalid calls recorded as errors, not executed.
- All actions logged.
- API keys only via environment variables; never logged.
- Token and cost budgets enforced per session and per experiment.

---

## 22. Project Phases (each ends with a verification gate)

| Phase | Build | Gate: must be true before moving on |
|---|---|---|
| 0 | Repo scaffold, config, DB, provider layer with Mock, logging, tests, `/api/health` | `pytest` passes with no API keys; server starts; health returns ok |
| 1 | E-commerce env, task generator with splits, deterministic evaluator | Evaluator unit tests cover every policy rule and interactions; generating with same seed is identical; a scripted "oracle" agent scores 100% |
| 2 | Learner loop with real provider; conditions A and B; CLI to run a batch | Real run on 20 validation tasks works; token/cost logged; **B success < ~85%** (else increase difficulty) |
| 3 | Demonstration JSON format, 8–12 handwritten demos, Teacher extraction, clarifications, fidelity metric | Extracted skill saved as memory v1; fidelity report produced; open questions answerable via CLI |
| 4 | Diagnosis, patching, curriculum, training loop, validation checks, memory versioning | One full session runs end-to-end; memory diffs readable; validation curve recorded; leakage check passes |
| 5 | Experiment runner: conditions A–F + ablations, seeds, bootstrap CIs, report | Report generated (markdown + JSON) comparing all conditions on test split |
| 6 | Defect injection suite | Diagnosis accuracy table generated |
| 7 | React UI (dashboard, skill memory, training view, experiment report) | Can watch a session live and view a report in browser |
| 8 | File organization environment + generator + evaluator + demos | Same Teacher/loop code runs unchanged on env 2; report produced |
| 9 | Demonstration studio UI, skill library, transfer experiment | Record a demo in UI; transfer results table |

## 23. MVP

Phases 0–5. The MVP is a reproducible experiment showing whether SkillForge beats baselines on held-out tasks in one environment, runnable from the CLI.

## 24. Related Work to Position Against

Reflexion (verbal self-reflection), Voyager (skill libraries), Agent Workflow Memory (workflow induction from trajectories), τ-bench (tool-agent-user benchmark with policy-following retail domain and state-based evaluation), ExpeL / trajectory-based prompt optimization, and prompt optimizers (DSPy, OPRO, TextGrad). τ-bench retail is a possible later external validation environment.

## 25. Definition

**SkillForge** is a closed-loop system that turns human demonstrations into an inspectable, versioned skill memory for LLM agents, improves that memory through diagnosis-driven practice, and verifies improvement with deterministic evaluation on held-out tasks.
