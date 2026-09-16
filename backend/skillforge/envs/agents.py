"""Environment-agnostic agent Protocol, a schema-driven RandomAgent, and the
episode-running harness. Nothing here knows about e-commerce (or any other
environment) specifically, so it is reused unchanged in Phase 8.
"""

from __future__ import annotations

import random
from typing import Protocol

from skillforge.envs.base import Action, ActionResult, Environment, EvaluationResult, State, Task, ToolSpec

DEFAULT_MAX_STEPS = 15


class Agent(Protocol):
    name: str

    def choose_action(self, state: State, tools: list[ToolSpec]) -> Action | None: ...


class RandomAgent:
    """Picks a uniformly random tool and fills its arguments with random
    values that satisfy the tool's JSON-schema types (so calls are usually
    schema-valid but almost never *correct* — it has no idea what a real
    order id is). Used as a low-bar sanity baseline against OracleAgent's
    100%, not as a serious policy.
    """

    name = "random"

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def choose_action(self, state: State, tools: list[ToolSpec]) -> Action | None:
        if not tools:
            return None
        tool = self._rng.choice(tools)
        args = _random_args(self._rng, tool.parameters)
        return Action(tool=tool.name, args=args)


def _random_args(rng: random.Random, schema: dict) -> dict:
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    args: dict = {}
    for key, prop in properties.items():
        if key not in required and rng.random() < 0.3:
            continue  # sometimes omit optional fields
        args[key] = _random_value(rng, prop)
    return args


def _random_value(rng: random.Random, prop: dict):
    enum_values = prop.get("enum")
    if enum_values:
        return rng.choice(enum_values)
    prop_type = prop.get("type")
    if prop_type == "string":
        return f"RAND-{rng.randint(0, 9999)}"
    if prop_type == "number":
        return round(rng.uniform(0, 1000), 2)
    if prop_type == "integer":
        return rng.randint(0, 1000)
    if prop_type == "boolean":
        return rng.choice([True, False])
    return None


def run_episode(
    env: Environment,
    task: Task,
    agent: Agent,
    max_steps: int = DEFAULT_MAX_STEPS,
) -> tuple[EvaluationResult, list[tuple[Action, ActionResult]]]:
    """Drive one agent through one task to completion (or `max_steps`),
    then evaluate. Returns the evaluation plus the full (action, result)
    trajectory for inspection/logging.
    """
    state = env.reset(task)
    tools = env.list_tools()
    trajectory: list[tuple[Action, ActionResult]] = []

    for _ in range(max_steps):
        action = agent.choose_action(state, tools)
        if action is None:
            break
        result = env.execute_action(action)
        trajectory.append((action, result))
        if result.ok and result.terminal:
            break
        state = env.get_state()

    return env.evaluate(), trajectory
