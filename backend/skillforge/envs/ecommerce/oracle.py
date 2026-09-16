"""OracleAgent: tests/tooling only, never learner- or teacher-facing.

It computes the correct answer by calling `resolve_ground_truth` directly
on the same world facts (`Task.initial_state`) the environment itself
parses — it never touches `Task.ground_truth`. It still acts "through the
real tools": its chosen Action is submitted to `Environment.execute_action`
like any other agent's, so the environment's validation/scoring plumbing
is genuinely exercised end to end.
"""

from __future__ import annotations

from skillforge.envs.base import Action, State, Task, ToolSpec
from skillforge.envs.ecommerce.environment import parse_world
from skillforge.envs.ecommerce.policy import Expected, resolve_ground_truth


class OracleAgent:
    name = "oracle"

    def __init__(self, task: Task):
        world = parse_world(task.initial_state)
        self._order_id = world.order.order_id
        self._expected: Expected = resolve_ground_truth(
            world.order, world.customer, world.history, world.request
        )
        self._acted = False

    def choose_action(self, state: State, tools: list[ToolSpec]) -> Action | None:
        del state, tools  # the oracle already knows the answer
        if self._acted:
            return None
        self._acted = True

        e = self._expected
        if e.action == "process_refund":
            return Action(
                tool="process_refund",
                args={"order_id": self._order_id, "amount": e.amount, "method": e.method},
            )
        if e.action == "reject_refund":
            return Action(
                tool="reject_refund",
                args={"order_id": self._order_id, "reason_code": e.reason_code},
            )
        return Action(
            tool="escalate",
            args={"order_id": self._order_id, "reason_code": e.reason_code},
        )
