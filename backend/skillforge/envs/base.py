"""The environment-agnostic types and Protocol every environment implements.

Kept free of anything e-commerce-specific so Phase 8's second environment
(file organization) can reuse this module — and the `run_episode` harness
in `envs/agents.py` — completely unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

# Reused rather than redefined: an environment's tools are handed straight
# to `LLMProvider.complete(tools=...)` in the Phase 2 learner loop, so tool
# schemas should already be in the shape the LLM layer expects.
from skillforge.llm.types import ToolSpec

__all__ = [
    "Task",
    "State",
    "Action",
    "ActionResult",
    "EvaluationResult",
    "Environment",
    "ToolSpec",
]


@dataclass
class Task:
    """One generated task. `ground_truth` holds only the hidden *decision*
    (see `skillforge.envs.ecommerce.policy.Expected`) — never the raw world
    facts, which live in `initial_state` and are reachable through tools.
    """

    id: str
    seed: int
    split: str  # "train" | "validation" | "test"
    request: str
    initial_state: dict[str, Any]
    ground_truth: dict[str, Any]


@dataclass
class State:
    """The learner-visible view returned by `Environment.get_state()`.
    Must never contain anything from `Task.ground_truth`.
    """

    request: str
    done: bool
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    tool: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    ok: bool
    tool: str
    output: Any = None
    error: str | None = None
    # True only for a successfully-executed action that ends the episode.
    terminal: bool = False


@dataclass
class EvaluationResult:
    success: bool
    score: float
    critical: bool
    error_type: str | None
    expected: dict[str, Any]
    actual: dict[str, Any]
    rules_involved: list[str] = field(default_factory=list)


@runtime_checkable
class Environment(Protocol):
    name: str

    def reset(self, task: Task) -> State: ...
    def get_state(self) -> State: ...  # learner-visible view only
    def list_tools(self) -> list[ToolSpec]: ...
    def execute_action(self, action: Action) -> ActionResult: ...
    def evaluate(self) -> EvaluationResult: ...  # uses hidden ground truth
