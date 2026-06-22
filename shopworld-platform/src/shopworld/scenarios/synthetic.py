"""Calibrated synthetic utterance generation.

Used when a real Bitext CSV isn't available. Produces linguistically varied,
shopper-plausible utterances per intent by combining cores with politeness
prefixes and order-reference suffixes. Deterministic given the inputs.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

_PREFIXES = ["", "hi, ", "hello, ", "please ", "hey ", "quick one — ", "sorry but ", "urgent: "]
_SUFFIXES = ["", " for order #1042", " on my recent order", " asap", " today please", " thanks", " can you help", " — ordered last week"]


def expand(cores_by_intent: Dict[str, List[str]], per_intent: int) -> List[Tuple[str, str]]:
    """Generate up to ``per_intent`` distinct (text, intent) pairs per intent.

    Iterates suffixes in the outer loop and prefixes in the inner loop so the
    earliest-generated variants are diverse rather than all sharing a suffix.
    """
    out: List[Tuple[str, str]] = []
    for intent, cores in cores_by_intent.items():
        seen: set[str] = set()
        produced = 0
        for suffix in _SUFFIXES:
            for prefix in _PREFIXES:
                for core in cores:
                    if produced >= per_intent:
                        break
                    text = f"{prefix}{core}{suffix}".strip()
                    key = text.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append((text, intent))
                    produced += 1
                if produced >= per_intent:
                    break
            if produced >= per_intent:
                break
    return out
