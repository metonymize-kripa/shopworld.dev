"""The persona library: named shopper archetypes.

Personas are immutable and standard so the battery stays comparable across
merchants. Each is a trait vector in [0, 1] that parameterises the behaviour
engine's Markov transitions and decision models, plus the dialogue policy.
"""

from __future__ import annotations

from ..engine.types import Persona, Vertical

_PERSONAS: tuple[Persona, ...] = (
    Persona(
        id="bargain_hunter",
        name="Bargain Hunter",
        price_sensitivity=0.95, patience=0.6, tech_fluency=0.6, brand_loyalty=0.2,
        risk_aversion=0.4, spec_orientation=0.4, review_reliance=0.7,
        complaint_propensity=0.5, channel_pickup_pref=0.6,
    ),
    Persona(
        id="anxious_gifter",
        name="Anxious Gifter",
        price_sensitivity=0.4, patience=0.3, tech_fluency=0.5, brand_loyalty=0.5,
        risk_aversion=0.85, spec_orientation=0.3, review_reliance=0.8,
        complaint_propensity=0.7, channel_pickup_pref=0.3,
    ),
    Persona(
        id="spec_maximalist",
        name="Spec Maximalist",
        price_sensitivity=0.3, patience=0.8, tech_fluency=0.95, brand_loyalty=0.4,
        risk_aversion=0.3, spec_orientation=0.95, review_reliance=0.6,
        complaint_propensity=0.4, channel_pickup_pref=0.4,
        vertical_affinity=Vertical.ELECTRONICS,
    ),
    Persona(
        id="loyal_regular",
        name="Loyal Regular",
        price_sensitivity=0.3, patience=0.7, tech_fluency=0.5, brand_loyalty=0.9,
        risk_aversion=0.5, spec_orientation=0.4, review_reliance=0.4,
        complaint_propensity=0.3, channel_pickup_pref=0.5,
    ),
    Persona(
        id="impatient_mobile",
        name="Impatient Mobile Shopper",
        price_sensitivity=0.5, patience=0.15, tech_fluency=0.4, brand_loyalty=0.3,
        risk_aversion=0.4, spec_orientation=0.2, review_reliance=0.5,
        complaint_propensity=0.6, channel_pickup_pref=0.7,
    ),
    Persona(
        id="cautious_first_timer",
        name="Cautious First-Timer",
        price_sensitivity=0.6, patience=0.5, tech_fluency=0.25, brand_loyalty=0.4,
        risk_aversion=0.9, spec_orientation=0.3, review_reliance=0.9,
        complaint_propensity=0.4, channel_pickup_pref=0.4,
    ),
    Persona(
        id="grocery_replenisher",
        name="Grocery Replenisher",
        price_sensitivity=0.6, patience=0.5, tech_fluency=0.5, brand_loyalty=0.6,
        risk_aversion=0.5, spec_orientation=0.2, review_reliance=0.3,
        complaint_propensity=0.5, channel_pickup_pref=0.6,
        vertical_affinity=Vertical.GROCERY,
    ),
    Persona(
        id="pro_buyer",
        name="Pro / B2B Buyer",
        price_sensitivity=0.7, patience=0.8, tech_fluency=0.7, brand_loyalty=0.5,
        risk_aversion=0.4, spec_orientation=0.8, review_reliance=0.4,
        complaint_propensity=0.6, channel_pickup_pref=0.5,
        vertical_affinity=Vertical.B2B,
    ),
)

_BY_ID: dict[str, Persona] = {p.id: p for p in _PERSONAS}


def all_personas() -> tuple[Persona, ...]:
    return _PERSONAS


def persona_by_id(persona_id: str) -> Persona:
    try:
        return _BY_ID[persona_id]
    except KeyError as exc:
        raise KeyError(f"unknown persona id {persona_id!r}") from exc
