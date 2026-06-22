"""Import Bitext customer-support utterances into ShopWorld intents (README §6).

If a Bitext support CSV is present (default: data/bitext/support.csv with columns
including an utterance/instruction field and an intent/category field), it is
parsed and mapped to merchant intents. Otherwise calibrated synthetic utterances
are generated so the pipeline runs without the external dataset. Every utterance
is split-tagged and provenance-tagged.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Optional

from shopworld.scenarios.splits import LabeledUtterance, assign_split
from shopworld.scenarios.synthetic import expand

_DEFAULT_CSV = Path(__file__).resolve().parents[3] / "data" / "bitext" / "support.csv"

# Bitext support intent/category -> ShopWorld merchant intent.
BITEXT_INTENT_MAP = {
    "track_order": "WISMO",
    "delivery_period": "WISMO",
    "track_refund": "REFUND",
    "check_refund_policy": "REFUND",
    "get_refund": "REFUND",
    "cancel_order": "CANCEL",
    "change_order": "CANCEL",
    "change_shipping_address": "ADDRESS_CHANGE",
    "set_up_shipping_address": "ADDRESS_CHANGE",
    "return": "RETURN",
    "check_return_policy": "RETURN",
    "complaint": "ESCALATE",
    "review": "OTHER",
    "contact_human_agent": "ESCALATE",
}

_SYNTHETIC_CORES = {
    "WISMO": [
        "where is my order", "my package hasn't arrived", "when will my order ship",
        "tracking hasn't updated", "is my delivery on the way", "my order is late",
        "i still haven't received my parcel", "any update on my shipment",
    ],
    "CANCEL": [
        "cancel my order", "i want to cancel my purchase", "please stop my order",
        "can i cancel before it ships", "call off this order", "i changed my mind, cancel it",
        "do not ship my order", "cancel order please",
    ],
    "REFUND": [
        "i want a refund", "can i get my money back", "please refund me",
        "i'd like a refund for this", "refund my payment", "give me my money back",
        "i need a refund", "process a refund please",
    ],
    "RETURN": [
        "how do i return this", "i want to return my item", "can i send this back",
        "start a return for me", "this doesn't fit, returning it", "i need to return a product",
        "how do i send it back", "return request please",
    ],
    "ADDRESS_CHANGE": [
        "change my shipping address", "update my delivery address", "ship to a different address",
        "i moved, update the address", "wrong address, please fix", "send it to my new place",
        "correct my address", "edit shipping address",
    ],
    "ESCALATE": [
        "i want to speak to a manager", "this is a complaint", "let me talk to a human",
        "i'm very unhappy with this", "escalate my issue", "i need a supervisor",
    ],
    "OTHER": [
        "do you have this in blue", "what are your store hours", "thanks for the help",
        "is this in stock", "what payment methods do you take", "great service",
    ],
}


def _load_csv(path: Path) -> List[LabeledUtterance]:
    rows: List[LabeledUtterance] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row.get("utterance") or row.get("instruction") or row.get("text") or ""
            raw_intent = (row.get("intent") or row.get("category") or "").strip().lower()
            text = text.strip()
            if not text:
                continue
            intent = BITEXT_INTENT_MAP.get(raw_intent, "OTHER")
            rows.append(
                LabeledUtterance(text, intent, "support", "bitext", assign_split(text))
            )
    return rows


def import_support_utterances(
    csv_path: Optional[Path] = None, target_per_intent: int = 80
) -> List[LabeledUtterance]:
    path = csv_path or _DEFAULT_CSV
    if path.exists():
        return _load_csv(path)
    # Fallback: synthetic generation (~target_per_intent * n_intents utterances).
    pairs = expand(_SYNTHETIC_CORES, per_intent=target_per_intent)
    return [
        LabeledUtterance(text, intent, "support", "synthetic", assign_split(text))
        for text, intent in pairs
    ]
