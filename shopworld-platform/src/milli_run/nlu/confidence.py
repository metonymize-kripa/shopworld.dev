"""Confidence routing: clarify/escalate low-certainty cases (README §7)."""

from __future__ import annotations

from dataclasses import dataclass

from milli_run.nlu.svm_model import Intent


@dataclass
class RouteDecision:
    action: str  # "handle" | "escalate" | "clarify"
    intent: str
    confidence: float
    reason: str


class ConfidenceRouter:
    """Decide whether to act on an intent or route it for review.

    Below ``escalate_below`` the model is too unsure to act safely -> escalate.
    Between that and ``clarify_below`` it asks the customer to clarify. Above
    ``clarify_below`` it handles the request. The ``OTHER`` intent is always
    routed (out of supported workflow scope).
    """

    def __init__(self, escalate_below: float = 0.35, clarify_below: float = 0.5):
        self.escalate_below = escalate_below
        self.clarify_below = clarify_below

    def route(self, intent: Intent) -> RouteDecision:
        if intent.label == "OTHER":
            return RouteDecision("escalate", intent.label, intent.confidence, "unsupported_workflow")
        if intent.confidence < self.escalate_below:
            return RouteDecision("escalate", intent.label, intent.confidence, "low_confidence")
        if intent.confidence < self.clarify_below:
            return RouteDecision("clarify", intent.label, intent.confidence, "ambiguous")
        return RouteDecision("handle", intent.label, intent.confidence, "confident")
