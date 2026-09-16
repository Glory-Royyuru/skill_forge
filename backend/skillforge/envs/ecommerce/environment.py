"""The e-commerce refund Environment implementation.

Strict separation from `Task.ground_truth`: everything this class reads to
answer tool calls comes from `Task.initial_state` (the simulated "world" —
order/customer/history/distractors), which is legitimately learner-visible
piece by piece through tools. `Task.ground_truth` (the hidden `Expected`
decision) is never read here except inside `evaluate()`, and even there it
never flows back into `get_state()` or any `ActionResult`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from skillforge.envs.base import Action, ActionResult, EvaluationResult, State, Task
from skillforge.envs.ecommerce.evaluator import evaluate_attempt
from skillforge.envs.ecommerce.models import (
    Customer,
    ItemCategory,
    ItemCondition,
    Order,
    OrderHistory,
    RefundHistoryEntry,
    RefundRequest,
)
from skillforge.envs.ecommerce.policy import Expected, resolve_ground_truth
from skillforge.envs.ecommerce.tools import ECOMMERCE_TOOLS, POLICY_SECTIONS, TOOLS_BY_NAME, validate_args
from skillforge.llm.types import ToolSpec


@dataclass
class World:
    """Everything `Task.initial_state` carries, parsed into dataclasses.
    Shared by the environment and by OracleAgent (tooling-only — it is not
    a learner or a teacher, see envs/ecommerce/oracle.py) so both compute
    from identical, learner-reachable facts.
    """

    order: Order
    customer: Customer
    history: OrderHistory
    request: RefundRequest
    distractor_orders: list[Order]


def order_from_dict(d: dict[str, Any]) -> Order:
    return Order(
        order_id=d["order_id"],
        customer_id=d["customer_id"],
        item_name=d["item_name"],
        item_price=d["item_price"],
        category=ItemCategory(d["category"]),
        condition=ItemCondition(d["condition"]),
        is_final_sale=d["is_final_sale"],
        is_gift=d["is_gift"],
        is_opened=d["is_opened"],
        days_since_delivery=d["days_since_delivery"],
        already_refunded=d["already_refunded"],
    )


def parse_world(initial_state: dict[str, Any]) -> World:
    order = order_from_dict(initial_state["order"])
    customer = Customer(**initial_state["customer"])
    history = OrderHistory(
        entries=[RefundHistoryEntry(**e) for e in initial_state["history"]["entries"]]
    )
    request = RefundRequest(**initial_state["request"])
    distractors = [order_from_dict(o) for o in initial_state.get("distractor_orders", [])]
    return World(
        order=order, customer=customer, history=history, request=request, distractor_orders=distractors
    )


def _order_public_view(order: Order) -> dict[str, Any]:
    """The learner-visible fields of an order. `days_since_delivery` is the
    system record — deliberately visible, since the learner is supposed to
    look it up rather than trust the customer's claimed date (R9). This is
    a *world fact*, not the hidden decision; see the module docstring.
    """
    return {
        "order_id": order.order_id,
        "customer_id": order.customer_id,
        "item_name": order.item_name,
        "item_price": order.item_price,
        "category": order.category.value,
        "condition": order.condition.value,
        "is_final_sale": order.is_final_sale,
        "is_gift": order.is_gift,
        "is_opened": order.is_opened,
        "days_since_delivery": order.days_since_delivery,
        "already_refunded": order.already_refunded,
    }


class EcommerceRefundEnvironment:
    name = "ecommerce_refunds"

    def __init__(self) -> None:
        self._task: Task | None = None
        self._world: World | None = None
        self._expected: Expected | None = None
        self._done = False
        self._trajectory: list[tuple[Action, ActionResult]] = []

    # -- Environment protocol -------------------------------------------------

    def reset(self, task: Task) -> State:
        self._task = task
        self._world = parse_world(task.initial_state)
        # Recomputed here (not read from task.ground_truth) so evaluate()
        # never has to touch the hidden field either — it's derivable from
        # the same world facts the tools expose.
        self._expected = resolve_ground_truth(
            self._world.order, self._world.customer, self._world.history, self._world.request
        )
        self._done = False
        self._trajectory = []
        return self.get_state()

    def get_state(self) -> State:
        assert self._task is not None
        return State(
            request=self._task.request,
            done=self._done,
            data={
                "steps_taken": len(self._trajectory),
                "history": [
                    {
                        "tool": a.tool,
                        "args": a.args,
                        "ok": r.ok,
                        "output": r.output,
                        "error": r.error,
                    }
                    for a, r in self._trajectory
                ],
            },
        )

    def list_tools(self) -> list[ToolSpec]:
        return list(ECOMMERCE_TOOLS)

    def execute_action(self, action: Action) -> ActionResult:
        if self._done:
            result = ActionResult(ok=False, tool=action.tool, error="episode_already_terminated")
            self._trajectory.append((action, result))
            return result

        spec = TOOLS_BY_NAME.get(action.tool)
        if spec is None:
            result = ActionResult(ok=False, tool=action.tool, error=f"unknown_tool:{action.tool}")
            self._trajectory.append((action, result))
            return result

        valid, err = validate_args(action.args, spec.parameters)
        if not valid:
            result = ActionResult(ok=False, tool=action.tool, error=f"invalid_args:{err}")
            self._trajectory.append((action, result))
            return result

        handler = getattr(self, f"_tool_{action.tool}")
        result = handler(action.args)
        self._trajectory.append((action, result))
        if result.ok and result.terminal:
            self._done = True
        return result

    def evaluate(self) -> EvaluationResult:
        assert self._expected is not None
        return evaluate_attempt(self._expected, self._trajectory)

    # -- Tool handlers ---------------------------------------------------------

    def _all_orders(self) -> list[Order]:
        assert self._world is not None
        return [self._world.order, *self._world.distractor_orders]

    def _find_order(self, order_id: str) -> Order | None:
        for o in self._all_orders():
            if o.order_id == order_id:
                return o
        return None

    def _tool_search_orders(self, args: dict) -> ActionResult:
        assert self._world is not None
        query = args["query"].strip().lower()
        matches = []
        for o in self._all_orders():
            haystack = f"{o.order_id} {o.item_name}"
            if o.customer_id == self._world.customer.customer_id:
                haystack += f" {self._world.customer.name}"
            if query in haystack.lower():
                matches.append({"order_id": o.order_id, "item_name": o.item_name})
        return ActionResult(ok=True, tool="search_orders", output={"results": matches})

    def _tool_view_order(self, args: dict) -> ActionResult:
        order = self._find_order(args["order_id"])
        if order is None:
            return ActionResult(ok=False, tool="view_order", error="order_not_found")
        return ActionResult(ok=True, tool="view_order", output=_order_public_view(order))

    def _tool_view_customer(self, args: dict) -> ActionResult:
        assert self._world is not None
        customer = self._world.customer
        if args["customer_id"] != customer.customer_id:
            return ActionResult(ok=False, tool="view_customer", error="customer_not_found")
        return ActionResult(
            ok=True,
            tool="view_customer",
            output={"customer_id": customer.customer_id, "name": customer.name, "is_vip": customer.is_vip},
        )

    def _tool_view_policy(self, args: dict) -> ActionResult:
        section = args["section"]
        text = POLICY_SECTIONS.get(section)
        if text is None:
            return ActionResult(
                ok=False,
                tool="view_policy",
                error=f"unknown_section:{section}",
                output={"available_sections": sorted(POLICY_SECTIONS)},
            )
        return ActionResult(ok=True, tool="view_policy", output={"section": section, "text": text})

    def _tool_view_order_history(self, args: dict) -> ActionResult:
        assert self._world is not None
        customer = self._world.customer
        if args["customer_id"] != customer.customer_id:
            return ActionResult(ok=False, tool="view_order_history", error="customer_not_found")
        entries = [asdict(e) for e in self._world.history.entries]
        return ActionResult(ok=True, tool="view_order_history", output={"entries": entries})

    def _terminal_order_id_check(self, tool: str, order_id: str) -> ActionResult | None:
        """Terminal actions must target the order the request concerns —
        not a distractor. A mismatch is recorded as an error and does NOT
        end the episode, so the agent can retry with the right id.
        """
        assert self._world is not None
        if order_id != self._world.order.order_id:
            return ActionResult(ok=False, tool=tool, error="order_id_mismatch")
        return None

    def _tool_process_refund(self, args: dict) -> ActionResult:
        mismatch = self._terminal_order_id_check("process_refund", args["order_id"])
        if mismatch is not None:
            return mismatch
        return ActionResult(
            ok=True,
            tool="process_refund",
            output={
                "order_id": args["order_id"],
                "amount": args["amount"],
                "method": args["method"],
                "status": "refund_processed",
            },
            terminal=True,
        )

    def _tool_reject_refund(self, args: dict) -> ActionResult:
        mismatch = self._terminal_order_id_check("reject_refund", args["order_id"])
        if mismatch is not None:
            return mismatch
        return ActionResult(
            ok=True,
            tool="reject_refund",
            output={
                "order_id": args["order_id"],
                "reason_code": args["reason_code"],
                "status": "refund_rejected",
            },
            terminal=True,
        )

    def _tool_escalate(self, args: dict) -> ActionResult:
        mismatch = self._terminal_order_id_check("escalate", args["order_id"])
        if mismatch is not None:
            return mismatch
        return ActionResult(
            ok=True,
            tool="escalate",
            output={"order_id": args["order_id"], "reason_code": args["reason_code"], "status": "escalated"},
            terminal=True,
        )
