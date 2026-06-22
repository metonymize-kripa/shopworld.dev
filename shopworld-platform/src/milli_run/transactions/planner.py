"""Transaction planner: turn a workflow into a safe ordered read/write plan.

The planner classifies each step (read vs write vs customer comms) and produces a
descriptive rollback plan, so milli.run can reason about transaction safety and
explain what it would undo on failure (README §7: commit/rollback, audit).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

_READ_TOOLS = {
    "orders.query",
    "customers.query",
    "fulfillments.query",
    "shipments.query",
    "inventory.query",
    "refunds.query",
    "returns.query",
    "products.query",
    "discounts.query",
}
_POLICY_TOOLS = {"policy.lookup", "policy.explain"}
_REPLY_TOOLS = {"tickets.reply"}
_ESCALATE_TOOLS = {"tickets.escalate"}

# write tool -> human-readable inverse (for the rollback plan / audit)
_INVERSE = {
    "orders.cancel": "reinstate order",
    "orders.update": "restore previous note/tags",
    "refunds.create": "void refund",
    "returns.create": "cancel return request",
    "inventory.adjust": "apply inverse delta",
    "customers.update": "restore previous customer fields",
}


def classify(tool: str) -> str:
    if tool in _READ_TOOLS:
        return "read"
    if tool in _POLICY_TOOLS:
        return "policy"
    if tool in _REPLY_TOOLS:
        return "reply"
    if tool in _ESCALATE_TOOLS:
        return "escalate"
    return "write"


@dataclass
class PlanStep:
    tool: str
    args: Dict[str, Any] = field(default_factory=dict)
    note: str = ""

    @property
    def kind(self) -> str:
        return classify(self.tool)


@dataclass
class TransactionPlanner:
    def categorize(self, steps: List[PlanStep]) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = {"read": [], "write": [], "policy": [], "reply": [], "escalate": []}
        for s in steps:
            out[s.kind].append(s.tool)
        return out

    def rollback_plan(self, steps: List[PlanStep]) -> List[str]:
        """Descriptive inverse operations for the write steps, in reverse order."""
        inverses = []
        for s in reversed(steps):
            if s.kind == "write":
                inverses.append(_INVERSE.get(s.tool, f"undo {s.tool}"))
        return inverses
