"""The persona-parameterised behaviour engine.

Two layers, both deterministic given ``(scenario, persona, seed)``:

* **Journey Markov chain** -- transitions between lifecycle macro-states.
  Persona traits reshape the transition weights (a bargain hunter loops back to
  price states; an anxious gifter jumps to tracking/exception states).

* **Within-state decision models** -- small Bayesian-style conditional
  probability tables (CPTs) over persona traits -> a discrete decision
  (abandon vs continue, accept vs decline a substitution, etc). Sampled from
  the same seeded stream.

This layer turns abstract journey structure into concrete shopper *decisions*.
The dialogue policy (adapters) consumes those decisions; the NLG renders them.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from ..engine.rng import DeterministicRNG
from ..engine.types import Lifecycle, Persona


class Decision(enum.Enum):
    """Discrete within-state decisions the shopper can make."""

    CONTINUE = "continue"
    ABANDON = "abandon"
    ACCEPT = "accept"
    DECLINE = "decline"
    ESCALATE = "escalate"
    REPHRASE = "rephrase"


# -- within-state decision models -----------------------------------------

@dataclass(frozen=True)
class DecisionModel:
    """A persona-conditioned decision over {primary, alternative}.

    The probability of the *primary* outcome is a logistic function of a
    weighted sum of persona traits. Pure and deterministic given the rng.
    """

    primary: Decision
    alternative: Decision
    bias: float
    trait_weights: dict[str, float]

    def probability(self, persona: Persona) -> float:
        z = self.bias
        for trait, w in self.trait_weights.items():
            z += w * (persona.trait(trait) - 0.5)
        # logistic squashing into (0, 1)
        return 1.0 / (1.0 + _exp(-z))

    def decide(self, persona: Persona, rng: DeterministicRNG) -> Decision:
        p = self.probability(persona)
        return self.primary if rng.bernoulli(p) else self.alternative


def _exp(x: float) -> float:
    # local exp avoids importing math into a hot path's namespace churn;
    # math.exp is deterministic and fine.
    import math

    # clamp to avoid overflow on extreme z
    if x > 60:
        return 1e26
    if x < -60:
        return 0.0
    return math.exp(x)


# Library of calibrated decision models keyed by decision-point name.
DECISION_MODELS: dict[str, DecisionModel] = {
    # On an unexpected fee at checkout: abandon if price-sensitive & risk-averse.
    "fee_surprise": DecisionModel(
        primary=Decision.ABANDON,
        alternative=Decision.CONTINUE,
        bias=-0.6,
        trait_weights={"price_sensitivity": 2.5, "risk_aversion": 1.0, "patience": -1.0},
    ),
    # On a grocery substitution offer: accept if not too brand-loyal/risk-averse.
    "substitution_offer": DecisionModel(
        primary=Decision.ACCEPT,
        alternative=Decision.DECLINE,
        bias=0.4,
        trait_weights={"brand_loyalty": -2.0, "risk_aversion": -1.2, "patience": 0.5},
    ),
    # On a merchant stall: escalate if complaint-prone & impatient, else rephrase.
    "stall_response": DecisionModel(
        primary=Decision.ESCALATE,
        alternative=Decision.REPHRASE,
        bias=-0.5,
        trait_weights={"complaint_propensity": 2.0, "patience": -1.5},
    ),
    # On an action needing confirmation: confirm unless very risk-averse.
    "confirm_action": DecisionModel(
        primary=Decision.ACCEPT,
        alternative=Decision.DECLINE,
        bias=1.0,
        trait_weights={"risk_aversion": -2.0, "tech_fluency": 0.5},
    ),
    # On out-of-stock: wait/continue (e.g. accept backorder) vs abandon.
    "stockout_response": DecisionModel(
        primary=Decision.CONTINUE,
        alternative=Decision.ABANDON,
        bias=0.0,
        trait_weights={"patience": 2.0, "brand_loyalty": 1.0, "price_sensitivity": -0.5},
    ),
}


def decide(point: str, persona: Persona, rng: DeterministicRNG) -> Decision:
    """Make a within-state decision at a named decision point."""
    model = DECISION_MODELS.get(point)
    if model is None:
        raise KeyError(f"no decision model for point {point!r}")
    return model.decide(persona, rng.derive(f"decision:{point}"))


# -- journey Markov chain --------------------------------------------------

# Base transition weights between lifecycle stages (rows sum need not be 1; the
# RNG normalises). Persona traits modulate these multiplicatively.
_BASE_TRANSITIONS: dict[Lifecycle, dict[Lifecycle, float]] = {
    Lifecycle.DISCOVERY: {Lifecycle.EVALUATION: 3.0, Lifecycle.DISCOVERY: 1.0},
    Lifecycle.EVALUATION: {
        Lifecycle.CART: 2.0,
        Lifecycle.EVALUATION: 1.0,
        Lifecycle.DISCOVERY: 0.5,
    },
    Lifecycle.CART: {Lifecycle.CHECKOUT: 3.0, Lifecycle.EVALUATION: 0.8},
    Lifecycle.CHECKOUT: {Lifecycle.FULFILLMENT: 3.0, Lifecycle.CART: 0.4},
    Lifecycle.FULFILLMENT: {Lifecycle.POST_PURCHASE: 3.0},
    Lifecycle.POST_PURCHASE: {
        Lifecycle.RETURN: 1.0,
        Lifecycle.ACCOUNT: 0.6,
        Lifecycle.POST_PURCHASE: 0.5,
    },
    Lifecycle.RETURN: {Lifecycle.ACCOUNT: 0.5},
    Lifecycle.ACCOUNT: {},
}


def _persona_modulation(persona: Persona, dst: Lifecycle) -> float:
    """Multiplicative factor applied to a transition weight by persona traits."""
    factor = 1.0
    if dst == Lifecycle.EVALUATION:
        factor *= 1.0 + 0.6 * (persona.spec_orientation - 0.5)
        factor *= 1.0 + 0.6 * (persona.review_reliance - 0.5)
    if dst == Lifecycle.CART:
        # impatient shoppers rush to cart
        factor *= 1.0 + 0.8 * (0.5 - persona.patience)
    if dst == Lifecycle.RETURN:
        factor *= 1.0 + 1.0 * (persona.complaint_propensity - 0.5)
        factor *= 1.0 + 0.8 * (persona.risk_aversion - 0.5)
    if dst == Lifecycle.DISCOVERY:
        # bargain hunters loop back to keep browsing
        factor *= 1.0 + 0.8 * (persona.price_sensitivity - 0.5)
    return max(factor, 0.05)


def journey_walk(
    persona: Persona,
    rng: DeterministicRNG,
    start: Lifecycle = Lifecycle.DISCOVERY,
    max_steps: int = 8,
) -> list[Lifecycle]:
    """A seeded, persona-modulated walk over lifecycle stages.

    Deterministic given ``(persona, rng-seed)``. Used to shape free-form
    exploratory scenarios; preconditioned scenarios use explicit goal stacks
    instead (see scenario compiler).
    """
    stream = rng.derive("journey")
    path = [start]
    current = start
    for _ in range(max_steps - 1):
        base = _BASE_TRANSITIONS.get(current, {})
        if not base:
            break
        dsts = list(base.keys())
        weights = [base[d] * _persona_modulation(persona, d) for d in dsts]
        nxt = stream.weighted_choice(dsts, weights)
        path.append(nxt)
        if nxt == current:
            # allow at most a self-loop then force progress next iteration
            current = nxt
            continue
        current = nxt
    return path
