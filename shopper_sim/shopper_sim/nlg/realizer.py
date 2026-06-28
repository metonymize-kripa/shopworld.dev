"""The controllable surface realiser.

Turns an abstract utterance request (family + slot values + persona) into
shopper-facing text. Deterministic and LLM-free at runtime:

  1. choose a register from persona tech_fluency/patience (seeded),
  2. select a template from the frozen paraphrase bank (seeded),
  3. fill slots from provided values or seeded lexical-bank draws,
  4. optionally inject seeded noise (typos/abbreviations) for low-fluency
     personas.

Same ``(family, slots, persona, seed)`` -> byte-identical utterance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from ..engine.rng import DeterministicRNG
from ..engine.types import Persona, Vertical
from . import lexicon
from .paraphrase_bank import templates_for

_SLOT_RE = re.compile(r"\{(\w+)\}")


@dataclass(frozen=True)
class Utterance:
    text: str
    register: str
    family_id: str
    template: str
    slots: Mapping[str, str]


def _pick_register(persona: Persona, rng: DeterministicRNG) -> str:
    """Lower tech_fluency & patience -> terser; higher -> politer."""
    # weight registers by persona; seeded choice for variation.
    terse_w = 1.0 + 1.5 * (0.5 - persona.tech_fluency) + 1.0 * (0.5 - persona.patience)
    polite_w = 1.0 + 1.5 * (persona.tech_fluency - 0.5) + 0.5 * (persona.patience - 0.5)
    neutral_w = 1.0
    registers = ["terse", "neutral", "polite"]
    weights = [max(terse_w, 0.05), neutral_w, max(polite_w, 0.05)]
    return rng.weighted_choice(registers, weights)


def _default_slot_value(slot: str, vertical: Vertical, rng: DeterministicRNG) -> str:
    """Draw a plausible value for an unbound slot from the lexical banks."""
    s = rng.derive(f"slot:{slot}")
    if slot == "product":
        return s.choice(lexicon.products_for(vertical))
    if slot == "brand":
        return s.choice(lexicon.BRANDS)
    if slot == "color":
        return s.choice(lexicon.COLORS)
    if slot == "size":
        return s.choice(lexicon.SIZES)
    if slot == "claim":
        return s.choice(lexicon.CLAIMS)
    if slot == "spec":
        return s.choice(lexicon.SPEC_VALUES)
    if slot == "return_reason":
        return s.choice(lexicon.RETURN_REASONS)
    if slot == "exception_detail":
        return s.choice(lexicon.EXCEPTION_DETAILS)
    if slot == "line_item":
        return s.choice(lexicon.products_for(vertical))
    if slot == "location":
        return s.choice(("downtown", "the north store", "my zip code"))
    if slot == "device_model":
        return s.choice(("iPhone 15", "Dell XPS 13", "Galaxy S24"))
    if slot == "issue":
        return s.choice(("won't power on", "a cracked screen", "a faulty motor"))
    if slot == "change_type":
        return s.choice(("skip", "pause", "cancel", "reschedule"))
    if slot == "payment_type":
        return s.choice(("credit card", "Apple Pay", "gift card"))
    if slot == "substitution_pref":
        return s.choice(lexicon.products_for(vertical))
    if slot == "desired_variant":
        return f"{s.choice(lexicon.SIZES)} {s.choice(lexicon.COLORS)}"
    # Fallback: a readable placeholder.
    return slot.replace("_", " ")


_NOISE_ABBREV = {
    "please": "pls",
    "you": "u",
    "your": "ur",
    "the": "th",
    "order": "ordr",
}


def _inject_noise(text: str, persona: Persona, rng: DeterministicRNG) -> str:
    """Seeded typo/abbreviation noise, scaled by low tech_fluency."""
    noise_rate = max(0.0, 0.5 - persona.tech_fluency)  # 0..0.5
    if noise_rate <= 0.0:
        return text
    stream = rng.derive("noise")
    words = text.split(" ")
    out = []
    for w in words:
        lw = w.lower()
        if lw in _NOISE_ABBREV and stream.bernoulli(noise_rate):
            out.append(_NOISE_ABBREV[lw])
            continue
        # occasional dropped trailing punctuation
        if w.endswith((".", "?")) and stream.bernoulli(noise_rate * 0.5):
            out.append(w[:-1])
            continue
        out.append(w)
    return " ".join(out)


def realise(
    family_id: str,
    slots: Mapping[str, str],
    persona: Persona,
    vertical: Vertical,
    rng: DeterministicRNG,
) -> Utterance:
    """Produce a deterministic shopper utterance for a family."""
    rstream = rng.derive(f"realise:{family_id}")
    register = _pick_register(persona, rstream.derive("register"))
    templates = templates_for(family_id, register)
    template = rstream.derive("template").choice(templates)

    # Fill slots: provided values win; otherwise draw defaults deterministically.
    needed = _SLOT_RE.findall(template)
    filled: dict[str, str] = {}
    for slot in needed:
        if slot in slots and slots[slot] is not None:
            filled[slot] = str(slots[slot])
        elif slot == "family":
            filled[slot] = family_id.replace("_", " ")
        else:
            filled[slot] = _default_slot_value(slot, vertical, rstream)

    text = template
    for slot, value in filled.items():
        text = text.replace("{" + slot + "}", value)

    text = _inject_noise(text, persona, rstream)
    text = re.sub(r"\s+", " ", text).strip()
    return Utterance(
        text=text,
        register=register,
        family_id=family_id,
        template=template,
        slots=filled,
    )
