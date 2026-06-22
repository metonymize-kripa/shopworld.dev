"""Scenario generation inputs: Bitext-derived utterances with leakage controls.

Implements README §12 steps 5-6 (scenario generators from Bitext support/retail)
under the §6 data-leakage rules: every utterance is tagged with a split
(nlu_train / scenario_seed / heldout_test) and a provenance, and the splits are
disjoint by construction so NLU training language is never reused as held-out
ShopWorld test language.
"""

from shopworld.scenarios.splits import (
    LabeledUtterance,
    Split,
    assign_split,
    split_report,
    assert_no_leakage,
)
from shopworld.scenarios.bitext_support_importer import import_support_utterances
from shopworld.scenarios.bitext_retail_importer import import_retail_utterances

__all__ = [
    "LabeledUtterance",
    "Split",
    "assign_split",
    "split_report",
    "assert_no_leakage",
    "import_support_utterances",
    "import_retail_utterances",
]
