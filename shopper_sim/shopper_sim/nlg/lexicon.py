"""Controlled lexical banks for NLG slot-filling.

These are small, fixed vocabularies the surface realiser draws from. Selection
is seeded, so the same scenario+seed always yields the same lexical choices.
In production these would be merchant-catalogue-derived; here they are generic
but representative.
"""

from __future__ import annotations

from ..engine.types import Vertical

# Generic catalogue, keyed loosely by vertical for realism.
PRODUCTS: dict[Vertical, tuple[str, ...]] = {
    Vertical.GENERIC: ("water bottle", "desk lamp", "backpack", "phone case", "notebook"),
    Vertical.APPAREL: ("linen shirt", "running shoes", "wool coat", "denim jeans", "rain jacket"),
    Vertical.GROCERY: ("almond milk", "oat cereal", "olive oil", "ground coffee", "pasta sauce"),
    Vertical.BEAUTY: ("vitamin C serum", "matte foundation", "sulfate-free shampoo", "lip balm"),
    Vertical.ELECTRONICS: ("USB-C charger", "4K monitor", "wireless earbuds", "mechanical keyboard"),
    Vertical.HOME: ("air fryer", "area rug", "stand mixer", "cordless vacuum", "ceiling fan"),
    Vertical.PHARMACY: ("allergy tablets", "vitamin D drops", "pain relief gel", "cough syrup"),
    Vertical.B2B: ("drywall sheets", "safety gloves", "shop towels", "industrial cleaner"),
    Vertical.DIGITAL: ("photo editing license", "ebook bundle", "music subscription"),
}

BRANDS: tuple[str, ...] = ("Acme", "NorthPeak", "Lumen", "EverGood", "Vela", "Brightline")

COLORS: tuple[str, ...] = ("blue", "black", "forest green", "charcoal", "sand", "burgundy")
SIZES: tuple[str, ...] = ("small", "medium", "large", "X-large")
CLAIMS: tuple[str, ...] = ("organic", "cruelty-free", "BPA-free", "recycled", "fragrance-free")
SPEC_VALUES: tuple[str, ...] = ("65W", "120Hz", "5000 BTU", "8x10", "1080p")

RETURN_REASONS: tuple[str, ...] = (
    "wrong size", "arrived damaged", "changed my mind", "not as described", "missing parts",
)
EXCEPTION_DETAILS: tuple[str, ...] = (
    "marked delivered but I never got it", "box was crushed", "wrong item inside",
    "only half the order arrived",
)


def products_for(vertical: Vertical) -> tuple[str, ...]:
    return PRODUCTS.get(vertical, PRODUCTS[Vertical.GENERIC])
