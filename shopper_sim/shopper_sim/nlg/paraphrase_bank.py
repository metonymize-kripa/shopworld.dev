"""The frozen paraphrase bank.

Each query family has a set of slotted templates capturing register variation
(terse vs polite vs detailed). In production this bank is generated OFFLINE by
an LLM and human-checked, then frozen. At runtime the realiser only *selects*
from the bank by seed -- it never generates -- which is what keeps utterances
reproducible and auditable with no LLM in the hot path.

Templates use ``{slot}`` placeholders filled by the realiser. Registers are
keyed so the realiser can pick a register appropriate to persona tech_fluency
and politeness.
"""

from __future__ import annotations

# register -> list of templates, per family id.
# Registers: "terse", "neutral", "polite".
PARAPHRASE_BANK: dict[str, dict[str, tuple[str, ...]]] = {
    "category_discovery": {
        "terse": ("{product}", "{product} {color}"),
        "neutral": ("looking for a {product}", "show me {product}s"),
        "polite": ("Hi, I'm trying to find a good {product}.",),
    },
    "exact_product_id": {
        "terse": ("{brand} {product} {spec}",),
        "neutral": ("do you have the {brand} {product} {spec}",),
        "polite": ("Could you tell me if you carry the {brand} {product} {spec}?",),
    },
    "variant_search": {
        "terse": ("{product} {color} {size}",),
        "neutral": ("{product} in {color}, size {size}",),
        "polite": ("I'd like the {product} in {color}, size {size} please.",),
    },
    "attribute_claim": {
        "terse": ("{claim} {product}",),
        "neutral": ("{product} that is {claim}",),
        "polite": ("Do you have a {product} that's {claim}?",),
    },
    "negative_constraints": {
        "terse": ("{product} no {claim}",),
        "neutral": ("{product} without {claim}",),
        "polite": ("I'm looking for a {product} that does not contain {claim}.",),
    },
    "compatibility": {
        "terse": ("{product} for {device_model}",),
        "neutral": ("does this {product} work with {device_model}",),
        "polite": ("Will this {product} be compatible with my {device_model}?",),
    },
    "price": {
        "terse": ("price {product}", "{product} cheaper anywhere"),
        "neutral": ("how much is the {product}", "can you price match the {product}"),
        "polite": ("Would you be able to match a lower price on the {product}?",),
    },
    "availability": {
        "terse": ("{product} in stock", "{product} stock {location}"),
        "neutral": ("is the {product} in stock", "when will the {product} restock"),
        "polite": ("Could you check whether the {product} is in stock near {location}?",),
    },
    "cart_operations": {
        "terse": ("remove {line_item}", "change {line_item} to {size}"),
        "neutral": ("please remove the {line_item} from my cart",),
        "polite": ("Could you take the {line_item} out of my cart, please?",),
    },
    "order_confirmation": {
        "terse": ("receipt order {order_id}",),
        "neutral": ("can I get the receipt for order {order_id}",),
        "polite": ("Could you resend the receipt for order {order_id}?",),
    },
    "order_editing": {
        "terse": ("change address order {order_id}",),
        "neutral": ("I need to change the shipping address on order {order_id}",),
        "polite": ("Hi, could I update the shipping address on order {order_id}?",),
    },
    "order_failure": {
        "terse": ("why order {order_id} cancelled",),
        "neutral": ("why was my order {order_id} cancelled",),
        "polite": ("Could you help me understand why order {order_id} was cancelled?",),
    },
    "live_fulfillment": {
        "terse": ("replace with {substitution_pref}",),
        "neutral": ("if it's out of stock replace with {substitution_pref}",),
        "polite": ("If anything's unavailable, please substitute {substitution_pref}.",),
    },
    "tracking": {
        "terse": ("where is order {order_id}",),
        "neutral": ("can you tell me where order {order_id} is",),
        "polite": ("Could you let me know the status of order {order_id}?",),
    },
    "delivery_exceptions": {
        "terse": ("order {order_id} {exception_detail}",),
        "neutral": ("my order {order_id} {exception_detail}",),
        "polite": ("I'm sorry to report that order {order_id} {exception_detail}.",),
    },
    "returns_policy": {
        "terse": ("can I return {product}",),
        "neutral": ("what's the return policy on the {product}",),
        "polite": ("Could you tell me the return policy for the {product}?",),
    },
    "return_initiation": {
        "terse": ("return order {order_id} {return_reason}",),
        "neutral": ("I want to return order {order_id}, {return_reason}",),
        "polite": ("I'd like to start a return for order {order_id} -- {return_reason}.",),
    },
    "exchanges_replacements": {
        "terse": ("exchange order {order_id} for {desired_variant}",),
        "neutral": ("can I exchange order {order_id} for {desired_variant}",),
        "polite": ("Could I exchange order {order_id} for {desired_variant} instead?",),
    },
    "refunds": {
        "terse": ("refund order {order_id}", "where is my refund {order_id}"),
        "neutral": ("when will I get the refund for order {order_id}",),
        "polite": ("Could you check on the refund status for order {order_id}?",),
    },
    "warranty_repair": {
        "terse": ("warranty claim {product} {issue}",),
        "neutral": ("I need to file a warranty claim, my {product} has {issue}",),
        "polite": ("I'd like to file a warranty claim -- my {product} has {issue}.",),
    },
    "subscriptions": {
        "terse": ("{change_type} subscription {subscription_id}",),
        "neutral": ("I want to {change_type} my subscription {subscription_id}",),
        "polite": ("Could you help me {change_type} subscription {subscription_id}?",),
    },
    "support_escalation": {
        "terse": ("agent", "talk to a human about {issue}"),
        "neutral": ("I'd like to speak to an agent about {issue}",),
        "polite": ("Could you connect me with a representative about {issue}?",),
    },
    "b2b_pro": {
        "terse": ("bulk {quantity} {product} tax exempt",),
        "neutral": ("I need a quote for {quantity} {product}, tax exempt {tax_exempt_id}",),
        "polite": ("Could I get a bulk quote for {quantity} {product}? We're tax-exempt ({tax_exempt_id}).",),
    },
    "promotions": {
        "terse": ("apply {promo_code}",),
        "neutral": ("my code {promo_code} isn't working",),
        "polite": ("Could you help? The promo code {promo_code} won't apply.",),
    },
    "channel_selection": {
        "terse": ("pickup {location}",),
        "neutral": ("can I pick this up at {location}",),
        "polite": ("Is curbside pickup available near {location}?",),
    },
    "checkout_forms": {
        "terse": ("ship to {address}",),
        "neutral": ("my address {address} isn't recognised",),
        "polite": ("My delivery address ({address}) isn't being accepted -- can you help?",),
    },
    "payment_method": {
        "terse": ("card declined",),
        "neutral": ("my {payment_type} was declined",),
        "polite": ("My {payment_type} was declined at checkout -- what should I do?",),
    },
}


# Fallback templates for families without a bespoke bank entry yet.
GENERIC_FALLBACK: dict[str, tuple[str, ...]] = {
    "terse": ("help with {family}",),
    "neutral": ("I have a question about {family}",),
    "polite": ("Could you help me with something regarding {family}?",),
}


def templates_for(family_id: str, register: str) -> tuple[str, ...]:
    """Return templates for a family+register, falling back gracefully."""
    fam = PARAPHRASE_BANK.get(family_id)
    if fam is None:
        return GENERIC_FALLBACK.get(register, GENERIC_FALLBACK["neutral"])
    reg = fam.get(register)
    if reg:
        return reg
    # fall back across registers within the family
    for r in ("neutral", "terse", "polite"):
        if fam.get(r):
            return fam[r]
    return GENERIC_FALLBACK["neutral"]
