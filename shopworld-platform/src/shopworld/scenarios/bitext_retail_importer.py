"""Import Bitext retail/ecommerce utterances (README §6, §12 step 6).

Retail utterances supply storefront/cart/checkout/product-help language. For the
merchant MVP these are used to diversify wording and to seed the shopper track
(README §5, deferred). Same CSV-or-synthetic + split-tagging contract as the
support importer.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Optional

from shopworld.scenarios.splits import LabeledUtterance, assign_split
from shopworld.scenarios.synthetic import expand

_DEFAULT_CSV = Path(__file__).resolve().parents[3] / "data" / "bitext" / "retail.csv"

BITEXT_INTENT_MAP = {
    "product_search": "PRODUCT_SEARCH",
    "search_product": "PRODUCT_SEARCH",
    "product_availability": "AVAILABILITY",
    "check_availability": "AVAILABILITY",
    "price_inquiry": "PRICE",
    "shipping_info": "SHIPPING_INFO",
    "delivery_options": "SHIPPING_INFO",
    "add_to_cart": "CART",
    "checkout": "CHECKOUT",
    "payment_methods": "CHECKOUT",
}

_SYNTHETIC_CORES = {
    "PRODUCT_SEARCH": [
        "do you sell waterproof hiking boots", "looking for a linen duvet cover",
        "i need a case for iphone 15 pro max", "show me black dresses for a wedding",
        "find me a compact travel stroller", "any noise cancelling headphones",
    ],
    "AVAILABILITY": [
        "is this in stock", "do you have this in size medium", "when will this be back in stock",
        "is the blue one available", "any stock in store", "can i get this in large",
    ],
    "PRICE": [
        "how much is this", "what's the price of this item", "is there a discount",
        "do you price match", "any coupons available", "what does shipping cost",
    ],
    "SHIPPING_INFO": [
        "how long does delivery take", "do you ship internationally", "what are the delivery options",
        "can i get express shipping", "when will it arrive", "do you offer free shipping",
    ],
    "CART": [
        "add this to my cart", "i want two of these", "remove an item from my cart",
        "update the quantity in my cart", "save this for later", "what's in my cart",
    ],
    "CHECKOUT": [
        "how do i check out", "what payment methods do you accept", "can i pay with paypal",
        "is checkout secure", "apply my gift card at checkout", "i want to place my order",
    ],
}


def _load_csv(path: Path) -> List[LabeledUtterance]:
    rows: List[LabeledUtterance] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (row.get("utterance") or row.get("instruction") or row.get("text") or "").strip()
            raw_intent = (row.get("intent") or row.get("category") or "").strip().lower()
            if not text:
                continue
            intent = BITEXT_INTENT_MAP.get(raw_intent, "OTHER")
            rows.append(LabeledUtterance(text, intent, "retail", "bitext", assign_split(text)))
    return rows


def import_retail_utterances(
    csv_path: Optional[Path] = None, target_per_intent: int = 84
) -> List[LabeledUtterance]:
    path = csv_path or _DEFAULT_CSV
    if path.exists():
        return _load_csv(path)
    pairs = expand(_SYNTHETIC_CORES, per_intent=target_per_intent)
    return [
        LabeledUtterance(text, intent, "retail", "synthetic", assign_split(text))
        for text, intent in pairs
    ]
