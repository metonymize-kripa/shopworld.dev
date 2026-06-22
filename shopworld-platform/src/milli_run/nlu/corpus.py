"""Bridge Bitext-imported utterances into milli.run NLU training (README §6).

Only the ``nlu_train`` split is used for training; ``heldout_test`` is never
touched here, preserving the leakage rule. Bitext ESCALATE maps to OTHER for the
classifier because milli.run handles escalation through its risk guard, not the
intent model.
"""

from __future__ import annotations

from typing import List, Tuple

from shopworld.scenarios import import_support_utterances
from shopworld.scenarios.splits import Split

from milli_run.nlu.training_data import TRAINING_UTTERANCES

# Classifier label set (no ESCALATE — handled by the risk guard).
_CLASSIFIER_LABELS = {"WISMO", "CANCEL", "REFUND", "RETURN", "ADDRESS_CHANGE", "OTHER"}


def bitext_training(split: Split = Split.NLU_TRAIN) -> List[Tuple[str, str]]:
    """Bitext support utterances from the given split, mapped to classifier labels."""
    out: List[Tuple[str, str]] = []
    for u in import_support_utterances():
        if u.split != split:
            continue
        label = u.intent if u.intent in _CLASSIFIER_LABELS else "OTHER"
        out.append((u.text, label))
    return out


def augmented_training() -> List[Tuple[str, str]]:
    """Built-in seed utterances + Bitext nlu_train split."""
    return list(TRAINING_UTTERANCES) + bitext_training()
