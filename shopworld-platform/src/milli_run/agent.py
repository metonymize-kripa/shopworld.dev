"""MilliRunAgent: neuro-symbolic merchant runtime under test.

Pipeline per ticket: shallow NLU intent + entities -> confidence router ->
guarded workflow state machine -> ordered Merchant API plan -> one tool call per
step. Every decision is written to an audit log. The agent touches ShopWorld
only through the Merchant API Surface (env.step), identical to the LLM agent.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from shopworld.agents.base import Agent
from shopworld.environment import Action, Observation

from milli_run import workflows
from milli_run.audit import AuditLog
from milli_run.nlu import ConfidenceRouter, EntityExtractor, LinearIntentClassifier
from milli_run.transactions.guards import PolicyGuards
from milli_run.transactions.planner import PlanStep, TransactionPlanner

# Train the shallow classifier once and reuse it across episodes/agents.
_CLASSIFIER: Optional[LinearIntentClassifier] = None


def get_classifier() -> LinearIntentClassifier:
    global _CLASSIFIER
    if _CLASSIFIER is None:
        _CLASSIFIER = LinearIntentClassifier()
    return _CLASSIFIER


class MilliRunAgent(Agent):
    name = "milli_run"

    def __init__(self) -> None:
        self.classifier = get_classifier()
        self.extractor = EntityExtractor()
        self.router = ConfidenceRouter()
        self.guards = PolicyGuards()
        self.planner = TransactionPlanner()
        self.audit = AuditLog()
        self._handled: set[str] = set()
        self._plan: List[PlanStep] = []

    def reset(self, observation: Observation, info: Dict[str, Any]) -> None:
        self.audit = AuditLog()
        self._handled = set()
        self._plan = []

    def act(self, observation: Observation) -> Optional[Action]:
        # Drain the current ticket's plan one step at a time.
        if self._plan:
            return self._to_action(self._plan.pop(0))

        ticket = self._next_ticket(observation)
        if ticket is None:
            return None

        self._handled.add(ticket["id"])
        self._plan = self._plan_for_ticket(ticket, observation)
        if not self._plan:
            return None
        return self._to_action(self._plan.pop(0))

    # -- internals -----------------------------------------------------------

    def _next_ticket(self, observation: Observation) -> Optional[Dict[str, Any]]:
        for ticket in observation.support_inbox.get("open_tickets", []):
            if ticket["id"] not in self._handled:
                return ticket
        return None

    def _find_order(self, observation: Observation, order_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not order_id:
            return None
        for order in observation.shopify_state.get("orders", []):
            if order.get("id") == order_id:
                return order
        return None

    # Threat/fraud/abuse signals that must be escalated to a human before any
    # automated workflow runs (milli.run policy supervisor; README §8 fraud/abuse).
    _RISK_TERMS = (
        "lawyer", "attorney", "sue", "lawsuit", "chargeback", "charge back",
        "dispute", "fraud", "scam", "report you", "bbb",
    )

    def _risk_signal(self, text: str) -> Optional[str]:
        low = text.lower()
        for term in self._RISK_TERMS:
            if term in low:
                return term
        return None

    def _plan_for_ticket(self, ticket: Dict[str, Any], observation: Observation) -> List[PlanStep]:
        text = f"{ticket.get('subject', '')} {ticket.get('description', '')}".strip()

        # Policy supervisor: escalate abusive/fraud/legal-threat tickets up front.
        risk = self._risk_signal(text)
        if risk is not None:
            self.audit.record("guard", name="risk", allowed=False, reason=f"risk_signal:{risk}")
            plan = workflows.escalate_unsupported(ticket, f"risk_signal:{risk}", self.audit)
            self.audit.record("plan", reads=0, writes=0)
            return plan

        intent = self.classifier.predict(text)
        entities = self.extractor.extract(text)
        decision = self.router.route(intent)
        self.audit.record(
            "nlu", intent=intent.label, confidence=round(intent.confidence, 3),
            order_ref=entities.order_ref,
        )
        self.audit.record("route", action=decision.action, reason=decision.reason)

        order = self._find_order(observation, ticket.get("order_id"))

        if decision.action == "handle" and intent.label in workflows.WORKFLOWS:
            plan = workflows.WORKFLOWS[intent.label](ticket, order, self.guards, self.audit)
        else:
            # Missing/unsupported workflow or low confidence -> route to human.
            plan = workflows.escalate_unsupported(ticket, decision.reason, self.audit)

        cats = self.planner.categorize(plan)
        self.audit.record("plan", reads=len(cats["read"]), writes=len(cats["write"]))
        if cats["write"]:
            self.audit.record("rollback_plan", inverses=self.planner.rollback_plan(plan))
        return plan

    def _to_action(self, step: PlanStep) -> Action:
        return Action(step.tool, dict(step.args))
