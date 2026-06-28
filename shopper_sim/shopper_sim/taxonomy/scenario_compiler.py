"""Scenario compilation.

Compiles taxonomy + goal templates into immutable, content-addressed
``Scenario`` artifacts. This is where the multistep structure is *secured*:
hard-core families get goal-stack templates whose preconditions presuppose
journey state (an order exists, an item was delivered), so they cannot be
satisfied by a single query.

The ``scenario_id`` is the content hash of the compiled scenario, making the
battery a frozen, versioned ruler.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from ..engine.hashing import content_hash
from ..engine.types import (
    Factsheet,
    Goal,
    IntentLayer,
    Scenario,
    Vertical,
)
from .registry import HARD_CORE_MULTISTEP, family_by_id


@dataclass(frozen=True)
class ScenarioTemplate:
    """A parameterisable recipe that compiles into one or more Scenarios."""

    key: str
    title: str
    vertical: Vertical
    primary_layer: IntentLayer
    build: Callable[["TemplateContext"], tuple[tuple[Goal, ...], Factsheet, dict]]
    tags: tuple[str, ...] = ()
    recommended_persona_id: str | None = None


@dataclass(frozen=True)
class TemplateContext:
    """Binding context passed to a template's build function."""

    order_id: str
    product_ref: str
    address: str
    subscription_id: str


def _finalize(
    template: ScenarioTemplate,
    goals: tuple[Goal, ...],
    factsheet: Factsheet,
    initial_state: dict,
) -> Scenario:
    """Assemble a scenario and assign its content-hash id."""
    body = {
        "title": template.title,
        "vertical": template.vertical.value,
        "primary_layer": template.primary_layer.value,
        "goals": [
            {
                "id": g.id,
                "family_id": g.family_id,
                "description": g.description,
                "preconditions": list(g.preconditions),
                "establishes": list(g.establishes),
                "info_slots": list(g.info_slots),
                "satisfaction_signals": list(g.satisfaction_signals),
                "params": dict(g.params),
            }
            for g in goals
        ],
        "factsheet": dict(sorted(factsheet.known_slots.items())),
        "initial_state": dict(sorted(initial_state.items())),
        "tags": list(template.tags),
        "recommended_persona_id": template.recommended_persona_id,
    }
    sid = content_hash(body)
    return Scenario(
        scenario_id=sid,
        title=template.title,
        vertical=template.vertical,
        primary_layer=template.primary_layer,
        goals=goals,
        factsheet=factsheet,
        initial_state=initial_state,
        recommended_persona_id=template.recommended_persona_id,
        tags=template.tags,
    )


# -- single-shot template builders ----------------------------------------

def _single_shot(family_id: str):
    fam = family_by_id(family_id)

    def build(ctx: TemplateContext):
        # Single-shot families resolve in one turn: the shopper's opening
        # utterance already carries the needed info. We still populate the
        # factsheet with plausible values so that if a merchant *does* ask a
        # clarifying question, the shopper can answer it from ground truth
        # rather than looping.
        known = {"product_ref": ctx.product_ref}
        params = {"product_ref": ctx.product_ref}
        for slot in fam.typical_info_slots:
            value = _default_single_shot_slot(slot, ctx)
            known[slot] = value
            params[slot] = value
        goal = Goal(
            id=f"{family_id}_g0",
            family_id=family_id,
            description=f"Resolve a {fam.name} query in one shot.",
            preconditions=(),
            establishes=(),
            info_slots=fam.typical_info_slots,
            satisfaction_signals=("answered", "result", "found"),
            params=params,
        )
        return (goal,), Factsheet(known_slots=known), {}

    return build


def _default_single_shot_slot(slot: str, ctx: TemplateContext) -> str:
    """Plausible ground-truth value for a single-shot family's info slot."""
    presets = {
        "product_a": "NorthPeak rain jacket",
        "product_b": "Vela storm shell",
        "base_product": ctx.product_ref,
        "competitor": "a rival store",
        "device_model": "iPhone 15",
        "vehicle": "2019 Honda Civic",
        "location": "my zip code",
        "symptom_detail": "it keeps happening after a week",
        "product_ref": ctx.product_ref,
        "recipient": "my brother",
        "registry_id": "REG-4410",
    }
    return presets.get(slot, slot.replace("_", " "))


# -- multistep template builders (hard-core families) ----------------------

def _build_order_editing(ctx: TemplateContext):
    locate = Goal(
        id="locate_order",
        family_id="order_confirmation",
        description="Locate the existing order before editing it.",
        preconditions=("order_exists",),
        establishes=("order_located",),
        info_slots=("order_id",),
        satisfaction_signals=("order", "found", "confirmed"),
        params={"order_id": ctx.order_id},
    )
    edit = Goal(
        id="edit_address",
        family_id="order_editing",
        description="Change the shipping address on the located order.",
        preconditions=("order_located",),
        establishes=("address_changed",),
        info_slots=("order_id", "new_value", "identity_proof"),
        satisfaction_signals=("updated", "changed", "address"),
        params={"order_id": ctx.order_id, "new_value": ctx.address},
    )
    fs = Factsheet(
        known_slots={
            "order_id": ctx.order_id,
            "new_value": ctx.address,
            "identity_proof": "email-on-file",
        }
    )
    return (locate, edit), fs, {"order_exists": True, "order_shipped": False}


def _build_tracking(ctx: TemplateContext):
    locate = Goal(
        id="locate_order",
        family_id="order_confirmation",
        description="Identify which order to track.",
        preconditions=("order_exists",),
        establishes=("order_located",),
        info_slots=("order_id",),
        satisfaction_signals=("order", "found"),
        params={"order_id": ctx.order_id},
    )
    track = Goal(
        id="track_order",
        family_id="tracking",
        description="Get the delivery status of the located order.",
        preconditions=("order_located",),
        establishes=("status_known",),
        info_slots=("order_id",),
        satisfaction_signals=("shipped", "delivery", "arriving", "tracking", "status"),
        params={"order_id": ctx.order_id},
    )
    fs = Factsheet(known_slots={"order_id": ctx.order_id})
    return (locate, track), fs, {"order_exists": True}


def _build_delivery_exception(ctx: TemplateContext):
    report = Goal(
        id="report_exception",
        family_id="delivery_exceptions",
        description="Report a delivery problem for an order.",
        preconditions=("order_exists", "order_delivered_status"),
        establishes=("exception_reported",),
        info_slots=("order_id", "exception_detail"),
        satisfaction_signals=("sorry", "investigate", "resend", "refund", "replace"),
        params={"order_id": ctx.order_id},
    )
    resolve = Goal(
        id="resolve_exception",
        family_id="refunds",
        description="Obtain a resolution (refund or replacement).",
        preconditions=("exception_reported",),
        establishes=("resolution_offered",),
        info_slots=("order_id",),
        satisfaction_signals=("refund", "replacement", "credit", "resolution"),
        params={"order_id": ctx.order_id},
    )
    fs = Factsheet(known_slots={"order_id": ctx.order_id})
    return (report, resolve), fs, {"order_exists": True, "order_delivered_status": True}


def _build_return_flow(ctx: TemplateContext):
    policy = Goal(
        id="check_policy",
        family_id="returns_policy",
        description="Confirm the item is returnable.",
        preconditions=("order_exists",),
        establishes=("policy_confirmed",),
        info_slots=("product_ref",),
        satisfaction_signals=("return", "window", "eligible", "policy"),
        params={"product_ref": ctx.product_ref},
    )
    initiate = Goal(
        id="initiate_return",
        family_id="return_initiation",
        description="Start the return and obtain a label.",
        preconditions=("policy_confirmed",),
        establishes=("return_initiated",),
        info_slots=("order_id", "return_reason"),
        satisfaction_signals=("label", "started", "return", "qr", "drop-off"),
        params={"order_id": ctx.order_id},
    )
    refund = Goal(
        id="confirm_refund",
        family_id="refunds",
        description="Confirm the refund method and timing.",
        preconditions=("return_initiated",),
        establishes=("refund_confirmed",),
        info_slots=("order_id",),
        satisfaction_signals=("refund", "days", "method", "credit"),
        params={"order_id": ctx.order_id},
    )
    fs = Factsheet(
        known_slots={
            "order_id": ctx.order_id,
            "product_ref": ctx.product_ref,
            "return_reason": "wrong size",
        }
    )
    return (policy, initiate, refund), fs, {"order_exists": True, "order_delivered_status": True}


def _build_subscription_change(ctx: TemplateContext):
    locate = Goal(
        id="find_subscription",
        family_id="identity_login",
        description="Authenticate to access the subscription.",
        preconditions=(),
        establishes=("authenticated",),
        info_slots=("email",),
        satisfaction_signals=("signed in", "verified", "account", "logged"),
        params={},
    )
    change = Goal(
        id="change_subscription",
        family_id="subscriptions",
        description="Skip or cancel the active subscription.",
        preconditions=("authenticated",),
        establishes=("subscription_changed",),
        info_slots=("subscription_id", "change_type"),
        satisfaction_signals=("skipped", "paused", "cancelled", "rescheduled", "updated"),
        params={"subscription_id": ctx.subscription_id, "change_type": "cancel"},
    )
    fs = Factsheet(
        known_slots={
            "email": "shopper@example.com",
            "subscription_id": ctx.subscription_id,
            "change_type": "cancel",
        }
    )
    return (locate, change), fs, {"subscription_active": True}


def _build_b2b_quote(ctx: TemplateContext):
    quote = Goal(
        id="request_quote",
        family_id="b2b_pro",
        description="Request a bulk quote.",
        preconditions=(),
        establishes=("quote_requested",),
        info_slots=("quantity", "product_ref"),
        satisfaction_signals=("quote", "bulk", "pricing", "total"),
        params={"quantity": "200", "product_ref": ctx.product_ref},
    )
    tax = Goal(
        id="apply_tax_exempt",
        family_id="b2b_pro",
        description="Apply tax-exempt status to the quote.",
        preconditions=("quote_requested",),
        establishes=("tax_exempt_applied",),
        info_slots=("tax_exempt_id",),
        satisfaction_signals=("tax", "exempt", "removed", "applied"),
        params={},
    )
    fs = Factsheet(
        known_slots={
            "quantity": "200",
            "product_ref": ctx.product_ref,
            "tax_exempt_id": "TX-99821",
        }
    )
    return (quote, tax), fs, {}


def _build_warranty_claim(ctx: TemplateContext):
    claim = Goal(
        id="file_claim",
        family_id="warranty_repair",
        description="File a warranty claim for a faulty product.",
        preconditions=("order_exists",),
        establishes=("claim_filed",),
        info_slots=("product_ref", "issue"),
        satisfaction_signals=("claim", "warranty", "repair", "replace", "rma"),
        params={"product_ref": ctx.product_ref},
    )
    escalate = Goal(
        id="escalate_claim",
        family_id="support_escalation",
        description="Escalate if the claim path is unclear.",
        preconditions=("claim_filed",),
        establishes=("escalated",),
        info_slots=("issue",),
        satisfaction_signals=("agent", "representative", "team", "escalat"),
        params={},
    )
    fs = Factsheet(
        known_slots={"product_ref": ctx.product_ref, "issue": "won't power on"}
    )
    return (claim, escalate), fs, {"order_exists": True}


def _build_live_fulfillment(ctx: TemplateContext):
    instruct = Goal(
        id="set_substitution",
        family_id="live_fulfillment",
        description="Set substitution preferences for a live grocery order.",
        preconditions=("order_exists", "order_in_progress"),
        establishes=("substitution_set",),
        info_slots=("order_id", "substitution_pref"),
        satisfaction_signals=("substitut", "replace", "noted", "preference"),
        params={"order_id": ctx.order_id},
    )
    approve = Goal(
        id="approve_substitution",
        family_id="live_fulfillment",
        description="Approve or decline a proposed substitution.",
        preconditions=("substitution_set",),
        establishes=("substitution_resolved",),
        info_slots=("order_id",),
        satisfaction_signals=("approved", "declined", "refund", "confirmed"),
        params={"order_id": ctx.order_id},
    )
    fs = Factsheet(known_slots={"order_id": ctx.order_id, "substitution_pref": "any similar brand"})
    return (instruct, approve), fs, {"order_exists": True, "order_in_progress": True}


_MULTISTEP_BUILDERS: dict[str, Callable[[TemplateContext], tuple]] = {
    "order_editing": _build_order_editing,
    "tracking": _build_tracking,
    "delivery_exceptions": _build_delivery_exception,
    "return_initiation": _build_return_flow,
    "refunds": _build_return_flow,  # refund tested within the return flow
    "subscriptions": _build_subscription_change,
    "b2b_pro": _build_b2b_quote,
    "warranty_repair": _build_warranty_claim,
    "live_fulfillment": _build_live_fulfillment,
    "exchanges_replacements": _build_return_flow,
    "order_failure": _build_tracking,  # locate-then-diagnose shape
    "support_escalation": _build_warranty_claim,  # claim-then-escalate shape
}


def default_context() -> TemplateContext:
    return TemplateContext(
        order_id="A1024",
        product_ref="NorthPeak rain jacket",
        address="42 Elm St, Apt 3, Springfield",
        subscription_id="SUB-7781",
    )


def compile_family_scenario(
    family_id: str,
    ctx: TemplateContext | None = None,
    vertical: Vertical | None = None,
) -> Scenario:
    """Compile a single scenario for the given family.

    Hard-core multistep families use their bespoke multi-goal builder; all
    others use the single-shot builder. If ``vertical`` is given it overrides
    the family's default overlay, so a family with multiple overlays (e.g.
    warranty_repair under both electronics and home) compiles to a distinct,
    separately-addressed scenario per overlay.
    """
    ctx = ctx or default_context()
    fam = family_by_id(family_id)
    layer = fam.layer
    chosen_vertical = vertical or (fam.overlays[0] if fam.overlays else Vertical.GENERIC)
    if family_id in _MULTISTEP_BUILDERS:
        builder = _MULTISTEP_BUILDERS[family_id]
        kind = "multistep"
    else:
        builder = _single_shot(family_id)
        kind = "single_shot"

    suffix = "" if chosen_vertical == Vertical.GENERIC else f" [{chosen_vertical.value}]"
    title = f"{'Multistep' if kind == 'multistep' else 'Single-shot'}: {fam.name}{suffix}"
    tags = (kind, family_id, chosen_vertical.value)

    goals, factsheet, initial_state = builder(ctx)
    template = ScenarioTemplate(
        key=f"{family_id}_{chosen_vertical.value}_scenario",
        title=title,
        vertical=chosen_vertical,
        primary_layer=layer,
        build=builder,  # not re-called; kept for provenance
        tags=tags,
    )
    return _finalize(template, goals, factsheet, initial_state)


def compile_full_battery(
    ctx: TemplateContext | None = None,
    expand_overlays: bool = True,
) -> tuple[Scenario, ...]:
    """Compile the coverage battery.

    With ``expand_overlays=True`` (default) a family with multiple vertical
    overlays yields one scenario per overlay, so every (family x applicable
    overlay) pair from the taxonomy is exercised -- this is where the 52 macro
    families fan out toward the operational-family count. With
    ``expand_overlays=False`` exactly one scenario per family is emitted (the
    family's default overlay), giving a compact 52-scenario smoke battery.
    """
    from .registry import all_families

    ctx = ctx or default_context()
    scenarios: list[Scenario] = []
    for fam in all_families():
        if not expand_overlays or not fam.overlays:
            scenarios.append(compile_family_scenario(fam.id, ctx))
            continue
        for overlay in fam.overlays:
            scenarios.append(compile_family_scenario(fam.id, ctx, vertical=overlay))
    return tuple(scenarios)


def compile_graph_journey(
    start_family: str,
    seed: int,
    ctx: TemplateContext | None = None,
    max_steps: int = 4,
    edge_kinds: tuple = (),
) -> Scenario:
    """Compile an *exploratory* multi-family scenario by walking the journey graph.

    Unlike the bespoke hard-core templates (which encode specific, curated
    journeys), this composes a journey by a seeded weighted walk over the
    journey graph from ``start_family``, chaining each visited family into a
    goal. Successive goals are linked by preconditions so the journey is a real
    multistep stack, not a bag of unrelated queries.

    This makes the journey graph load-bearing: the same graph used for authoring
    drives generated scenarios. Deterministic given ``(start_family, seed)``.
    """
    from ..engine.rng import DeterministicRNG
    from .graph import EdgeKind, build_default_graph

    ctx = ctx or default_context()
    kinds = edge_kinds or (EdgeKind.PRECEDES, EdgeKind.ESCALATES_TO)
    graph = build_default_graph()
    rng = DeterministicRNG(seed).derive(f"graph_journey:{start_family}")
    path = graph.weighted_walk(start_family, rng, kinds=kinds, max_steps=max_steps)

    goals: list[Goal] = []
    known: dict[str, object] = {"product_ref": ctx.product_ref}
    prev_establish: str | None = None
    for i, fid in enumerate(path):
        fam = family_by_id(fid)
        establish = f"step_{i}_done"
        precondition = (prev_establish,) if prev_establish else ()
        slots = tuple(fam.typical_info_slots)
        for s in slots:
            known.setdefault(s, _default_single_shot_slot(s, ctx))
        goals.append(
            Goal(
                id=f"step_{i}_{fid}",
                family_id=fid,
                description=f"Handle {fam.name} as step {i + 1} of the journey.",
                preconditions=precondition,
                establishes=(establish,),
                info_slots=slots,
                satisfaction_signals=("answered", "result", "found", "confirmed", "done"),
                params={"product_ref": ctx.product_ref},
            )
        )
        prev_establish = establish

    primary = family_by_id(path[-1]).layer
    template = ScenarioTemplate(
        key=f"graph_journey_{start_family}_{seed}",
        title=f"Graph journey from {family_by_id(start_family).name} ({len(path)} steps)",
        vertical=Vertical.GENERIC,
        primary_layer=primary,
        build=lambda _ctx: (tuple(goals), Factsheet(known_slots=known), {}),
        tags=("graph_journey", start_family),
    )
    # First goal has no precondition, so the initial_state can be empty.
    return _finalize(template, tuple(goals), Factsheet(known_slots=known), {})
