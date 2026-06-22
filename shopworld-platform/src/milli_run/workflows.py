"""Merchant workflow state machines (README §7, §11 workflows/).

Each workflow maps an intent + observed order state to a guarded, ordered plan
of Merchant API steps. State-dependence is the point: the same intent yields a
different correct plan under different store state (README §8).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from milli_run import templates
from milli_run.audit import AuditLog
from milli_run.transactions.guards import PolicyGuards
from milli_run.transactions.planner import PlanStep

# Intent label -> workflow name (the supported workflow set; anything else is a
# "missing workflow" failure mode, README §9).
SUPPORTED = {"WISMO", "CANCEL", "ADDRESS_CHANGE", "REFUND", "RETURN"}


def _reply(ticket_id: str, body: str) -> PlanStep:
    return PlanStep("tickets.reply", {"ticket_id": ticket_id, "body": body}, "customer reply")


def _escalate(ticket_id: str, reason: str) -> PlanStep:
    return PlanStep("tickets.escalate", {"ticket_id": ticket_id, "reason": reason}, "escalate")


def track_order(ticket: Dict, order: Optional[Dict], guards: PolicyGuards, audit: AuditLog) -> List[PlanStep]:
    tid, oid = ticket["id"], ticket.get("order_id")
    audit.record("read", tool="orders.query", order_id=oid)
    audit.record("read", tool="shipments.query", order_id=oid)
    audit.record("reply", template="wismo")
    return [
        PlanStep("orders.query", {"id": oid}, "ground order"),
        PlanStep("shipments.query", {"order_id": oid}, "check tracking"),
        _reply(tid, templates.wismo(order)),
    ]


def cancel_order(ticket: Dict, order: Optional[Dict], guards: PolicyGuards, audit: AuditLog) -> List[PlanStep]:
    tid, oid = ticket["id"], ticket.get("order_id")
    g = guards.cancel(order)
    audit.record("guard", name="cancel", allowed=g.allowed, reason=g.reason)
    steps = [PlanStep("orders.query", {"id": oid}, "ground order")]
    if g.allowed:
        audit.record("write", tool="orders.cancel", order_id=oid)
        steps.append(PlanStep("orders.cancel", {"order_id": oid, "reason": "customer"}, "cancel"))
        steps.append(_reply(tid, templates.cancel_confirmed(order)))
    else:
        steps.append(PlanStep("policy.lookup", {"query": "cancellation"}, "confirm policy"))
        steps.append(_reply(tid, templates.cancel_blocked(order)))
    return steps


def change_address(ticket: Dict, order: Optional[Dict], guards: PolicyGuards, audit: AuditLog) -> List[PlanStep]:
    tid, oid = ticket["id"], ticket.get("order_id")
    g = guards.address_change(order)
    audit.record("guard", name="address_change", allowed=g.allowed, reason=g.reason)
    steps = [PlanStep("orders.query", {"id": oid}, "ground order")]
    if g.allowed:
        audit.record("write", tool="orders.update", order_id=oid)
        steps.append(
            PlanStep(
                "orders.update",
                {"order_id": oid, "note": "Customer requested shipping address change (pre-fulfillment)."},
                "record address change",
            )
        )
        steps.append(_reply(tid, templates.address_change_confirmed()))
    else:
        steps.append(PlanStep("policy.lookup", {"query": "shipping"}, "confirm policy"))
        steps.append(_reply(tid, templates.address_change_blocked()))
        audit.record("escalate", reason=g.reason)
        steps.append(_escalate(tid, "address change after fulfillment"))
    return steps


def refund(ticket: Dict, order: Optional[Dict], guards: PolicyGuards, audit: AuditLog) -> List[PlanStep]:
    tid, oid = ticket["id"], ticket.get("order_id")
    amount = float(order.get("total_price", 0) or 0) if order else 0.0
    g = guards.refund(order, amount)
    audit.record("guard", name="refund", allowed=g.allowed, reason=g.reason, amount=amount)
    steps = [
        PlanStep("orders.query", {"id": oid}, "ground order"),
        PlanStep("policy.lookup", {"query": "refund"}, "confirm policy"),
    ]
    if g.allowed:
        audit.record("write", tool="refunds.create", order_id=oid, amount=amount)
        steps.append(
            PlanStep(
                "refunds.create",
                {"order_id": oid, "amount": amount, "reason": "requested_by_customer"},
                "issue refund",
            )
        )
        steps.append(_reply(tid, templates.refund_confirmed(order)))
    else:
        steps.append(_reply(tid, templates.refund_blocked(g.reason)))
        audit.record("escalate", reason=g.reason)
        steps.append(_escalate(tid, f"refund blocked: {g.reason}"))
    return steps


def return_item(ticket: Dict, order: Optional[Dict], guards: PolicyGuards, audit: AuditLog) -> List[PlanStep]:
    tid, oid = ticket["id"], ticket.get("order_id")
    g = guards.return_item(order)
    audit.record("guard", name="return", allowed=g.allowed, reason=g.reason)
    steps = [
        PlanStep("orders.query", {"id": oid}, "ground order"),
        PlanStep("policy.lookup", {"query": "return"}, "confirm policy"),
    ]
    if g.allowed:
        audit.record("write", tool="returns.create", order_id=oid)
        steps.append(
            PlanStep(
                "returns.create",
                {"order_id": oid, "return_reason": "customer_request"},
                "create return",
            )
        )
        steps.append(_reply(tid, templates.return_started()))
    else:
        steps.append(_reply(tid, templates.return_blocked()))
        audit.record("escalate", reason=g.reason)
        steps.append(_escalate(tid, f"return blocked: {g.reason}"))
    return steps


def escalate_unsupported(ticket: Dict, reason: str, audit: AuditLog) -> List[PlanStep]:
    tid = ticket["id"]
    audit.record("escalate", reason=reason)
    return [
        _reply(tid, templates.escalation(reason)),
        _escalate(tid, reason),
    ]


WORKFLOWS = {
    "WISMO": track_order,
    "CANCEL": cancel_order,
    "ADDRESS_CHANGE": change_address,
    "REFUND": refund,
    "RETURN": return_item,
}
