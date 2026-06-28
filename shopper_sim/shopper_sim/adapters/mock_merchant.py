"""Mock merchant adapters.

Deterministic, scriptable stand-in merchants so the full pipeline runs without
a live store. Three quality tiers let the test-suite and demos show score
separation:

  * ``GoodMerchant``  -- asks for the right info, then resolves the goal.
  * ``CluelessMerchant`` -- asks for impossible info, stalls, never resolves.
  * ``OvereagerMerchant`` -- resolves without asking, sometimes wrongly.

A real ``AgentAdapter`` (httpx/MCP) and ``WebAdapter`` (Playwright) would
implement the same ``MerchantAdapter`` protocol; those live in
``agent_adapter.py`` and ``web_adapter.py`` as transport shells.
"""

from __future__ import annotations

from ..engine.types import Goal, Scenario
from .base import MerchantAdapter, MerchantTurn


class _ScenarioAwareMerchant(MerchantAdapter):
    """Base class that knows the scenario's goals so it can respond plausibly.

    A real merchant does NOT get the scenario; these mocks do, purely to
    generate believable scripted behaviour for testing. The shopper side never
    sees the merchant's internals.
    """

    def __init__(self, scenario: Scenario) -> None:
        self._scenario = scenario
        self._goal_by_signals = scenario.goals
        self._turn_index = 0

    def open_session(self, scenario_id: str, seed: int) -> None:
        self._turn_index = 0

    def close_session(self) -> None:
        pass

    def _active_goal(self, utterance: str) -> Goal:
        """Heuristically map an utterance to the goal it addresses."""
        u = utterance.lower()
        best = self._scenario.goals[0]
        best_score = -1
        for g in self._scenario.goals:
            score = sum(1 for sig in g.satisfaction_signals if sig.lower() in u)
            score += sum(1 for s in g.info_slots if s.replace("_", " ") in u)
            score += sum(1 for v in g.params.values() if str(v).lower() in u)
            if score > best_score:
                best_score = score
                best = g
        return best


class GoodMerchant(_ScenarioAwareMerchant):
    """Asks for one needed slot, then answers using goal satisfaction signals."""

    def __init__(self, scenario: Scenario) -> None:
        super().__init__(scenario)
        self._asked: dict[str, bool] = {}
        self._provided: dict[str, bool] = {}
        self._satisfied: set[str] = set()

    def send(self, utterance: str) -> MerchantTurn:
        self._turn_index += 1
        goal = self._active_goal(utterance)
        u = utterance.lower()

        # If the goal needs a slot and the shopper hasn't provided it, ask once.
        needed_slot = self._first_unmet_slot(goal, u)
        if needed_slot is not None and not self._asked.get(goal.id + needed_slot):
            self._asked[goal.id + needed_slot] = True
            return MerchantTurn(
                text=self._ask_for(needed_slot),
                has_question=True,
            )

        # Otherwise resolve the goal using its satisfaction signals.
        self._satisfied.add(goal.id)
        signals = " ".join(goal.satisfaction_signals[:2]) or "done"
        return MerchantTurn(
            text=f"All set -- {signals}. Anything else?",
            has_question=False,
        )

    def _active_goal(self, utterance: str) -> Goal:
        """Map an utterance to a goal, preferring not-yet-satisfied goals."""
        u = utterance.lower()
        best = None
        best_score = -1.0
        for g in self._scenario.goals:
            score = 0.0
            score += 2.0 * sum(1 for sig in g.satisfaction_signals if sig.lower() in u)
            score += sum(1 for s in g.info_slots if s.replace("_", " ") in u)
            score += sum(1 for v in g.params.values() if str(v).lower() in u)
            # Strong preference for goals we haven't already closed.
            if g.id in self._satisfied:
                score -= 5.0
            if score > best_score:
                best_score = score
                best = g
        return best or self._scenario.goals[0]

    def _first_unmet_slot(self, goal: Goal, utterance: str) -> str | None:
        for slot in goal.info_slots:
            if slot in ("identity_proof",):
                continue  # GoodMerchant only verifies when truly needed
            token = str(goal.params.get(slot, "")).lower()
            readable = slot.replace("_", " ")
            present = (token and token in utterance) or (readable in utterance)
            if not present and not self._provided.get(goal.id + slot):
                self._provided[goal.id + slot] = True
                return slot
        return None

    @staticmethod
    def _ask_for(slot: str) -> str:
        prompts = {
            "order_id": "Sure -- what's your order number?",
            "email": "Happy to help. Could you sign in or share your email address?",
            "address": "What's the shipping address you'd like to use?",
            "return_reason": "What's the reason for your return?",
            "product_ref": "Which product are you asking about?",
            "device_model": "Which model do you have?",
            "subscription_id": "Which subscription id is it?",
            "tax_exempt_id": "Do you have a tax exempt certificate id?",
            "quantity": "How many units do you need?",
            "issue": "Can you describe the issue?",
            "substitution_pref": "Any substitution preference if it's out of stock?",
            "new_value": "What would you like to change it to?",
            "product_a": "Which is the first product to compare?",
            "product_b": "And the second product to compare with?",
            "base_product": "Which product is this for?",
        }
        return prompts.get(slot, f"Could you share your {slot.replace('_', ' ')}?")


class CluelessMerchant(_ScenarioAwareMerchant):
    """Asks for impossible info and stalls; never resolves."""

    def send(self, utterance: str) -> MerchantTurn:
        self._turn_index += 1
        if self._turn_index == 1:
            return MerchantTurn(
                text="To proceed I'll need your account PIN and the security code we sent.",
                has_question=True,
            )
        return MerchantTurn(
            text="Hmm, I'm not sure I understand. Could you repeat that?",
            has_question=False,
        )


class OvereagerMerchant(_ScenarioAwareMerchant):
    """Resolves immediately without asking for needed info."""

    def send(self, utterance: str) -> MerchantTurn:
        self._turn_index += 1
        goal = self._active_goal(utterance)
        signals = " ".join(goal.satisfaction_signals[:2]) or "done"
        return MerchantTurn(
            text=f"Done! I've handled it -- {signals}.",
            has_question=False,
        )


class RefusingMerchant(_ScenarioAwareMerchant):
    """Flatly refuses -- tests the refusal path."""

    def send(self, utterance: str) -> MerchantTurn:
        self._turn_index += 1
        return MerchantTurn(text="Sorry, we can't help with that here.")
