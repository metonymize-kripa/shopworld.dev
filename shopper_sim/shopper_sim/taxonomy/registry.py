"""The master taxonomy: all 52 macro query families from the source doc.

Each entry maps a macro family to its lifecycle stage, rubric layer, and
single-shot/multistep classification. This module is the single source of
truth for coverage; the test-suite asserts all 52 are present and that every
inherently-multistep family has at least one preconditioned scenario template.

The ``overlays`` field records which verticals materially extend a family
(e.g. exchanges under apparel add size-conversion expectations).
"""

from __future__ import annotations

from ..engine.types import IntentLayer, Lifecycle, QueryFamily, Turns, Vertical

# Convenience aliases
L = Lifecycle
Y = IntentLayer
T = Turns
V = Vertical

# fmt: off
_FAMILIES: tuple[QueryFamily, ...] = (
    QueryFamily("store_entry", 1, "Store / marketplace entry", L.DISCOVERY, Y.PRODUCT, T.SINGLE,
                overlays=(V.GENERIC,)),
    QueryFamily("shopping_mission", 2, "Shopping mission", L.DISCOVERY, Y.PRODUCT, T.SINGLE),
    QueryFamily("category_discovery", 3, "Category discovery", L.DISCOVERY, Y.PRODUCT, T.SINGLE),
    QueryFamily("exact_product_id", 4, "Exact product identification", L.DISCOVERY, Y.PRODUCT, T.SINGLE),
    QueryFamily("brand_line", 5, "Brand and line", L.DISCOVERY, Y.PRODUCT, T.SINGLE),
    QueryFamily("variant_search", 6, "Variant search", L.DISCOVERY, Y.PRODUCT, T.SINGLE),
    QueryFamily("technical_spec", 7, "Technical specification", L.EVALUATION, Y.PRODUCT, T.SINGLE,
                overlays=(V.ELECTRONICS, V.HOME)),
    QueryFamily("attribute_claim", 8, "Attribute and claim", L.EVALUATION, Y.PRODUCT, T.SINGLE,
                overlays=(V.GROCERY, V.BEAUTY)),
    QueryFamily("negative_constraints", 9, "Negative constraints", L.EVALUATION, Y.PRODUCT, T.SINGLE),
    QueryFamily("compatibility", 10, "Compatibility", L.EVALUATION, Y.PRODUCT, T.ESCALATING,
                typical_info_slots=("device_model", "vehicle"), overlays=(V.ELECTRONICS,)),
    QueryFamily("use_case", 11, "Use-case / solution", L.EVALUATION, Y.PRODUCT, T.SINGLE),
    QueryFamily("symptom_problem", 12, "Symptom / problem", L.EVALUATION, Y.PRODUCT, T.ESCALATING,
                typical_info_slots=("symptom_detail",), overlays=(V.PHARMACY, V.BEAUTY)),
    QueryFamily("subjective_quality", 13, "Subjective quality", L.EVALUATION, Y.PRODUCT, T.SINGLE),
    QueryFamily("style_taste", 14, "Style / taste", L.EVALUATION, Y.PRODUCT, T.SINGLE,
                overlays=(V.APPAREL,)),
    QueryFamily("social_proof", 15, "Social proof", L.EVALUATION, Y.PRODUCT, T.SINGLE),
    QueryFamily("product_education", 16, "Product education", L.EVALUATION, Y.PRODUCT, T.ESCALATING,
                typical_info_slots=("product_ref",)),
    QueryFamily("product_comparison", 17, "Product comparison", L.EVALUATION, Y.PRODUCT, T.MULTI,
                typical_info_slots=("product_a", "product_b")),
    QueryFamily("complements_bundles", 18, "Complements and bundles", L.EVALUATION, Y.PRODUCT, T.MULTI,
                typical_info_slots=("base_product",)),
    QueryFamily("availability", 19, "Availability", L.EVALUATION, Y.FULFILLMENT, T.ESCALATING,
                typical_info_slots=("product_ref", "location")),
    QueryFamily("channel_selection", 20, "Channel selection", L.FULFILLMENT, Y.FULFILLMENT, T.MULTI,
                typical_info_slots=("location",)),
    QueryFamily("price", 21, "Price", L.EVALUATION, Y.TRANSACTION, T.ESCALATING,
                typical_info_slots=("product_ref", "competitor")),
    QueryFamily("promotions", 22, "Promotions", L.CHECKOUT, Y.TRANSACTION, T.MULTI,
                typical_info_slots=("promo_code",)),
    QueryFamily("benefits_subsidies", 23, "Benefits and subsidies", L.CHECKOUT, Y.TRANSACTION, T.MULTI,
                typical_info_slots=("benefit_type",), overlays=(V.GROCERY, V.PHARMACY)),
    QueryFamily("financing_credit", 24, "Financing and credit", L.CHECKOUT, Y.TRANSACTION, T.MULTI,
                typical_info_slots=("financing_type",)),
    QueryFamily("tax_fees", 25, "Tax and fees", L.CHECKOUT, Y.TRANSACTION, T.MULTI),
    QueryFamily("cart_operations", 26, "Cart operations", L.CART, Y.TRANSACTION, T.MULTI,
                typical_info_slots=("line_item",)),
    QueryFamily("basket_rules", 27, "Basket rules", L.CART, Y.TRANSACTION, T.MULTI),
    QueryFamily("gifts_registries", 28, "Gifts and registries", L.CART, Y.TRANSACTION, T.MULTI,
                typical_info_slots=("registry_id", "recipient"), overlays=(V.GENERIC,)),
    QueryFamily("identity_login", 29, "Identity and login", L.CHECKOUT, Y.ACCOUNT, T.MULTI,
                typical_info_slots=("email",)),
    QueryFamily("profile_preferences", 30, "Profile and preferences", L.ACCOUNT, Y.ACCOUNT, T.MULTI,
                typical_info_slots=("field", "new_value")),
    QueryFamily("checkout_forms", 31, "Checkout forms", L.CHECKOUT, Y.TRANSACTION, T.MULTI,
                typical_info_slots=("address",)),
    QueryFamily("payment_method", 32, "Payment method", L.CHECKOUT, Y.TRANSACTION, T.MULTI,
                typical_info_slots=("payment_type",)),
    QueryFamily("checkout_trust", 33, "Checkout trust and security", L.CHECKOUT, Y.TRANSACTION, T.MULTI,
                typical_info_slots=("identity_proof",)),
    QueryFamily("fulfillment_promise", 34, "Fulfillment promise", L.FULFILLMENT, Y.FULFILLMENT, T.MULTI,
                typical_info_slots=("product_ref", "location")),
    QueryFamily("fulfillment_constraints", 35, "Fulfillment constraints", L.FULFILLMENT, Y.FULFILLMENT, T.MULTI,
                typical_info_slots=("address",)),
    QueryFamily("order_confirmation", 36, "Order confirmation", L.POST_PURCHASE, Y.TRANSACTION, T.MULTI,
                typical_info_slots=("order_id",)),
    QueryFamily("order_editing", 37, "Order editing", L.POST_PURCHASE, Y.EXCEPTION, T.MULTI,
                typical_info_slots=("order_id", "new_value", "identity_proof")),
    QueryFamily("order_failure", 38, "Order failure", L.POST_PURCHASE, Y.EXCEPTION, T.MULTI,
                typical_info_slots=("order_id",)),
    QueryFamily("live_fulfillment", 39, "Live fulfillment", L.FULFILLMENT, Y.EXCEPTION, T.MULTI,
                typical_info_slots=("order_id", "substitution_pref"), overlays=(V.GROCERY,)),
    QueryFamily("tracking", 40, "Tracking", L.POST_PURCHASE, Y.FULFILLMENT, T.MULTI,
                typical_info_slots=("order_id",)),
    QueryFamily("delivery_exceptions", 41, "Delivery exceptions", L.POST_PURCHASE, Y.EXCEPTION, T.MULTI,
                typical_info_slots=("order_id", "exception_detail")),
    QueryFamily("returns_policy", 42, "Returns policy", L.RETURN, Y.RETURN, T.MULTI,
                typical_info_slots=("product_ref",)),
    QueryFamily("return_initiation", 43, "Return initiation", L.RETURN, Y.RETURN, T.MULTI,
                typical_info_slots=("order_id", "return_reason")),
    QueryFamily("exchanges_replacements", 44, "Exchanges and replacements", L.RETURN, Y.RETURN, T.MULTI,
                typical_info_slots=("order_id", "desired_variant"), overlays=(V.APPAREL, V.ELECTRONICS)),
    QueryFamily("refunds", 45, "Refunds", L.RETURN, Y.RETURN, T.MULTI,
                typical_info_slots=("order_id",)),
    QueryFamily("warranty_repair", 46, "Warranty / repair / service", L.POST_PURCHASE, Y.RETURN, T.MULTI,
                typical_info_slots=("product_ref", "issue"), overlays=(V.ELECTRONICS, V.HOME)),
    QueryFamily("ownership_support", 47, "Ownership support", L.POST_PURCHASE, Y.RETURN, T.ESCALATING,
                typical_info_slots=("product_ref",), overlays=(V.ELECTRONICS,)),
    QueryFamily("subscriptions", 48, "Subscriptions", L.ACCOUNT, Y.ACCOUNT, T.MULTI,
                typical_info_slots=("subscription_id", "change_type"), overlays=(V.GROCERY, V.PHARMACY)),
    QueryFamily("loyalty_membership", 49, "Loyalty and membership", L.ACCOUNT, Y.ACCOUNT, T.MULTI,
                typical_info_slots=("member_id",)),
    QueryFamily("support_escalation", 50, "Customer support escalation", L.POST_PURCHASE, Y.EXCEPTION, T.MULTI,
                typical_info_slots=("issue", "order_id")),
    QueryFamily("privacy_compliance", 51, "Privacy / compliance", L.ACCOUNT, Y.ACCOUNT, T.MULTI,
                typical_info_slots=("request_type",), overlays=(V.PHARMACY,)),
    QueryFamily("b2b_pro", 52, "B2B / pro buying", L.CHECKOUT, Y.TRANSACTION, T.MULTI,
                typical_info_slots=("quantity", "tax_exempt_id"), overlays=(V.B2B,)),
)
# fmt: on


_BY_ID: dict[str, QueryFamily] = {f.id: f for f in _FAMILIES}
_BY_NUMBER: dict[int, QueryFamily] = {f.number: f for f in _FAMILIES}

# The 12 "hard core" multistep families that presuppose journey state and
# cannot be tested single-shot (from the plan's bolded-M set).
HARD_CORE_MULTISTEP: frozenset[str] = frozenset(
    {
        "order_editing",
        "order_failure",
        "live_fulfillment",
        "tracking",
        "delivery_exceptions",
        "return_initiation",
        "exchanges_replacements",
        "refunds",
        "warranty_repair",
        "subscriptions",
        "support_escalation",
        "b2b_pro",
    }
)


def all_families() -> tuple[QueryFamily, ...]:
    return _FAMILIES


def family_by_id(family_id: str) -> QueryFamily:
    try:
        return _BY_ID[family_id]
    except KeyError as exc:
        raise KeyError(f"unknown family id {family_id!r}") from exc


def family_by_number(number: int) -> QueryFamily:
    try:
        return _BY_NUMBER[number]
    except KeyError as exc:
        raise KeyError(f"unknown family number {number!r}") from exc


def families_by_layer(layer: IntentLayer) -> tuple[QueryFamily, ...]:
    return tuple(f for f in _FAMILIES if f.layer == layer)


def families_for_vertical(vertical: Vertical) -> tuple[QueryFamily, ...]:
    """Families that are either generic or carry an overlay for this vertical."""
    return tuple(f for f in _FAMILIES if vertical in f.overlays or not f.overlays)
