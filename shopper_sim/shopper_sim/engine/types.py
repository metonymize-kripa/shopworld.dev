"""Core domain types for the shopper simulator.

These are the vocabulary every subsystem speaks: the intent taxonomy
(lifecycle, macro families, query families), persona traits, scenarios, the
multistep goal stack, and the dialogue-policy enums.

All dataclasses are frozen so that, once compiled, scenarios behave as
immutable content-addressable artifacts.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


class Lifecycle(enum.Enum):
    """The shopper-journey lifecycle stages."""

    DISCOVERY = "discovery"
    EVALUATION = "evaluation"
    CART = "cart"
    CHECKOUT = "checkout"
    FULFILLMENT = "fulfillment"
    POST_PURCHASE = "post_purchase"
    RETURN = "return"
    ACCOUNT = "account"


class IntentLayer(enum.Enum):
    """The seven rubric roll-up layers from the source taxonomy."""

    PRODUCT = "product"
    TRANSACTION = "transaction"
    FULFILLMENT = "fulfillment"
    EXCEPTION = "exception"
    RETURN = "return"
    ACCOUNT = "account"
    VERTICAL = "vertical"


class Vertical(enum.Enum):
    GENERIC = "generic"
    APPAREL = "apparel"
    GROCERY = "grocery"
    BEAUTY = "beauty"
    ELECTRONICS = "electronics"
    HOME = "home"
    PHARMACY = "pharmacy"
    B2B = "b2b"
    DIGITAL = "digital"


class Turns(enum.Enum):
    """Whether a family is inherently single-shot or multistep."""

    SINGLE = "S"
    MULTI = "M"
    ESCALATING = "M*"  # single-shot that may escalate to multi on clarify


@dataclass(frozen=True)
class QueryFamily:
    """A leaf query family, e.g. 'order_editing' (family #37)."""

    id: str  # stable slug, e.g. "order_editing"
    number: int  # 1..52 macro index from the source taxonomy
    name: str
    lifecycle: Lifecycle
    layer: IntentLayer
    turns: Turns
    # The information slots a competent merchant may need to ask for.
    typical_info_slots: tuple[str, ...] = ()
    # Verticals that materially extend this family.
    overlays: tuple[Vertical, ...] = ()

    @property
    def is_multistep(self) -> bool:
        return self.turns in (Turns.MULTI, Turns.ESCALATING)


# -- personas --------------------------------------------------------------

@dataclass(frozen=True)
class Persona:
    """A shopper archetype as a vector of traits in [0, 1].

    Traits feed both the journey Markov transition weights and the within-state
    decision models, plus the dialogue policy's choice points.
    """

    id: str
    name: str
    price_sensitivity: float = 0.5
    patience: float = 0.5
    tech_fluency: float = 0.5
    brand_loyalty: float = 0.5
    risk_aversion: float = 0.5
    spec_orientation: float = 0.5
    review_reliance: float = 0.5
    complaint_propensity: float = 0.5
    channel_pickup_pref: float = 0.5  # 0 = ship, 1 = pickup
    vertical_affinity: Vertical = Vertical.GENERIC

    def trait(self, name: str) -> float:
        value = getattr(self, name)
        if not isinstance(value, (int, float)):
            raise TypeError(f"trait {name!r} is not numeric")
        return float(value)


# -- multistep goal stack --------------------------------------------------

@dataclass(frozen=True)
class Goal:
    """One objective on the shopper's goal stack.

    The precondition / satisfaction model is what forces real multistep
    behaviour: a goal whose precondition presupposes journey state (an order
    exists, an item was delivered) cannot be satisfied by a single query.
    """

    id: str
    family_id: str
    description: str
    # Journey-state keys that must hold before this goal can be pursued.
    preconditions: tuple[str, ...] = ()
    # Journey-state keys this goal establishes once satisfied.
    establishes: tuple[str, ...] = ()
    # Info slots the shopper is WILLING to provide if asked (must exist in the
    # factsheet to actually be providable).
    info_slots: tuple[str, ...] = ()
    # Keys the satisfaction predicate looks for in merchant responses.
    satisfaction_signals: tuple[str, ...] = ()
    # Free-form parameters bound at scenario-compile time (e.g. order_id).
    params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Factsheet:
    """The immutable ground truth of what THIS shopper knows.

    The dialogue policy answers merchant clarifying questions ONLY from here.
    Asking for something absent tests whether the merchant demands impossible
    info; the shopper never volunteers a slot it was not asked for.
    """

    known_slots: Mapping[str, Any] = field(default_factory=dict)

    def has(self, slot: str) -> bool:
        return slot in self.known_slots

    def get(self, slot: str) -> Optional[Any]:
        return self.known_slots.get(slot)


# -- scenarios -------------------------------------------------------------

@dataclass(frozen=True)
class Scenario:
    """A runnable test: an ordered goal stack + persona binding + factsheet.

    Compiled from the taxonomy graph into an immutable artifact. The
    ``scenario_id`` is its content hash, assigned at compile time.
    """

    scenario_id: str
    title: str
    vertical: Vertical
    primary_layer: IntentLayer
    goals: tuple[Goal, ...]
    factsheet: Factsheet
    # Initial journey-state assumptions (e.g. {"order_exists": True}).
    initial_state: Mapping[str, Any] = field(default_factory=dict)
    # Persona is bound at run time, but a scenario may recommend one.
    recommended_persona_id: Optional[str] = None
    tags: tuple[str, ...] = ()

    @property
    def is_multistep(self) -> bool:
        return any(len(g.preconditions) > 0 for g in self.goals) or len(self.goals) > 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "vertical": self.vertical.value,
            "primary_layer": self.primary_layer.value,
            "goals": [
                {
                    "id": g.id,
                    "family_id": g.family_id,
                    "description": g.description,
                    "preconditions": list(g.preconditions),
                    "establishes": list(g.establishes),
                    "info_slots": list(g.info_slots),
                    "satisfaction_signals": list(g.satisfaction_signals),
                    "params": dict(g.params),
                }
                for g in self.goals
            ],
            "factsheet": {"known_slots": dict(self.factsheet.known_slots)},
            "initial_state": dict(self.initial_state),
            "recommended_persona_id": self.recommended_persona_id,
            "tags": list(self.tags),
        }
