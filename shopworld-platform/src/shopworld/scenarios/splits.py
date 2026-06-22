"""Deterministic data splits and provenance tracking (README §6).

Each utterance is hashed to a split so the partition is stable across runs and
machines, and the three splits are guaranteed disjoint. This enforces the
leakage rule: NLU-training text, scenario-seed text, and held-out test text never
overlap.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List


class Split(str, Enum):
    NLU_TRAIN = "nlu_train"
    SCENARIO_SEED = "scenario_seed"
    HELDOUT_TEST = "heldout_test"


@dataclass(frozen=True)
class LabeledUtterance:
    text: str
    intent: str
    domain: str  # "support" | "retail"
    source: str  # "bitext" | "synthetic"
    split: Split


def assign_split(text: str) -> Split:
    """Stable split assignment from a hash of the text.

    60% NLU train, 20% scenario seed, 20% held-out test. Deterministic and
    machine-independent (md5 of the normalized text).
    """
    h = int(hashlib.md5(text.strip().lower().encode("utf-8")).hexdigest(), 16)
    bucket = h % 100
    if bucket < 60:
        return Split.NLU_TRAIN
    if bucket < 80:
        return Split.SCENARIO_SEED
    return Split.HELDOUT_TEST


def split_report(utterances: Iterable[LabeledUtterance]) -> Dict[str, int]:
    counts: Dict[str, int] = {s.value: 0 for s in Split}
    for u in utterances:
        counts[u.split.value] += 1
    return counts


def assert_no_leakage(utterances: List[LabeledUtterance]) -> bool:
    """Confirm the three splits share no utterance text (README §6)."""
    by_split: Dict[Split, set] = {s: set() for s in Split}
    for u in utterances:
        by_split[u.split].add(u.text.strip().lower())
    train, seed, test = by_split[Split.NLU_TRAIN], by_split[Split.SCENARIO_SEED], by_split[Split.HELDOUT_TEST]
    return not (train & seed) and not (train & test) and not (seed & test)
