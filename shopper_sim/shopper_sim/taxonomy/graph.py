"""The journey graph.

A weighted property graph whose nodes are query families and whose edges encode
how shopper journeys compose: lifecycle ordering (PRECEDES), happy-path to
exception (ESCALATES_TO), and state presupposition (REQUIRES).

Scenario generation is a *seeded weighted walk* over this graph, which is why a
graph representation is used rather than a flat list: composing a realistic
post-purchase exception journey is pathfinding, not lookup.

The graph lives only in the authoring path. Compiled scenarios are frozen JSON;
the runtime engine never touches the graph.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from ..engine.rng import DeterministicRNG
from .registry import all_families, family_by_id


class EdgeKind(enum.Enum):
    PRECEDES = "precedes"          # lifecycle ordering
    ESCALATES_TO = "escalates_to"  # happy path -> exception
    REQUIRES = "requires"          # presupposes prior state
    COMPLEMENTS = "complements"    # discovery branching
    SUBSTITUTES = "substitutes"


@dataclass(frozen=True)
class Edge:
    src: str        # family id
    dst: str        # family id
    kind: EdgeKind
    weight: float   # relative transition weight (> 0)


class JourneyGraph:
    """In-memory property graph of query families and their relationships."""

    def __init__(self) -> None:
        self._nodes: set[str] = {f.id for f in all_families()}
        self._out: dict[str, list[Edge]] = {n: [] for n in self._nodes}

    def add_edge(self, src: str, dst: str, kind: EdgeKind, weight: float = 1.0) -> None:
        if src not in self._nodes:
            raise KeyError(f"unknown source family {src!r}")
        if dst not in self._nodes:
            raise KeyError(f"unknown destination family {dst!r}")
        if weight <= 0:
            raise ValueError("edge weight must be positive")
        self._out[src].append(Edge(src, dst, kind, weight))

    def edges_from(self, src: str, kind: EdgeKind | None = None) -> list[Edge]:
        edges = self._out.get(src, [])
        if kind is None:
            return list(edges)
        return [e for e in edges if e.kind == kind]

    def nodes(self) -> set[str]:
        return set(self._nodes)

    def all_edges(self) -> list[Edge]:
        """Every edge in the graph, ordered deterministically (src, dst, kind)."""
        edges: list[Edge] = []
        for src in sorted(self._out):
            edges.extend(self._out[src])
        return sorted(edges, key=lambda e: (e.src, e.dst, e.kind.value))

    def weighted_walk(
        self,
        start: str,
        rng: DeterministicRNG,
        kinds: tuple[EdgeKind, ...],
        max_steps: int,
    ) -> list[str]:
        """A seeded weighted walk from ``start`` following edges of ``kinds``.

        Produces an ordered list of family ids forming a journey. Stops when no
        outgoing edge of the allowed kinds exists or ``max_steps`` is reached.
        The walk never revisits a family (journeys are acyclic by construction).
        """
        if start not in self._nodes:
            raise KeyError(f"unknown start family {start!r}")
        path = [start]
        visited = {start}
        current = start
        for _ in range(max_steps - 1):
            candidates = [
                e for e in self.edges_from(current)
                if e.kind in kinds and e.dst not in visited
            ]
            if not candidates:
                break
            chosen = rng.weighted_choice(candidates, [e.weight for e in candidates])
            path.append(chosen.dst)
            visited.add(chosen.dst)
            current = chosen.dst
        return path


def build_default_graph() -> JourneyGraph:
    """Construct the canonical journey graph with calibrated edge weights.

    Weights are hand-set to reflect realistic journey shapes (e.g. discovery
    usually precedes evaluation; placed orders sometimes escalate to delivery
    exceptions; exceptions lead to returns/refunds/escalation). In production
    these would be calibrated against published behavioural statistics.
    """
    g = JourneyGraph()

    # --- Lifecycle PRECEDES backbone -------------------------------------
    g.add_edge("category_discovery", "exact_product_id", EdgeKind.PRECEDES, 2.0)
    g.add_edge("category_discovery", "variant_search", EdgeKind.PRECEDES, 1.5)
    g.add_edge("category_discovery", "subjective_quality", EdgeKind.PRECEDES, 1.0)
    g.add_edge("exact_product_id", "product_education", EdgeKind.PRECEDES, 1.5)
    g.add_edge("exact_product_id", "product_comparison", EdgeKind.PRECEDES, 1.0)
    g.add_edge("variant_search", "availability", EdgeKind.PRECEDES, 1.5)
    g.add_edge("product_comparison", "price", EdgeKind.PRECEDES, 1.5)
    g.add_edge("availability", "cart_operations", EdgeKind.PRECEDES, 2.0)
    g.add_edge("price", "promotions", EdgeKind.PRECEDES, 1.0)
    g.add_edge("cart_operations", "channel_selection", EdgeKind.PRECEDES, 1.0)
    g.add_edge("cart_operations", "checkout_forms", EdgeKind.PRECEDES, 2.0)
    g.add_edge("checkout_forms", "payment_method", EdgeKind.PRECEDES, 2.5)
    g.add_edge("payment_method", "checkout_trust", EdgeKind.PRECEDES, 1.0)
    g.add_edge("payment_method", "order_confirmation", EdgeKind.PRECEDES, 2.0)
    g.add_edge("order_confirmation", "fulfillment_promise", EdgeKind.PRECEDES, 1.5)
    g.add_edge("fulfillment_promise", "tracking", EdgeKind.PRECEDES, 2.0)

    # --- ESCALATES_TO (happy path -> exception) --------------------------
    g.add_edge("order_confirmation", "order_editing", EdgeKind.ESCALATES_TO, 1.0)
    g.add_edge("order_confirmation", "order_failure", EdgeKind.ESCALATES_TO, 0.5)
    g.add_edge("tracking", "delivery_exceptions", EdgeKind.ESCALATES_TO, 1.2)
    g.add_edge("delivery_exceptions", "support_escalation", EdgeKind.ESCALATES_TO, 1.0)
    g.add_edge("delivery_exceptions", "refunds", EdgeKind.ESCALATES_TO, 1.0)
    g.add_edge("live_fulfillment", "refunds", EdgeKind.ESCALATES_TO, 0.8)
    g.add_edge("order_confirmation", "return_initiation", EdgeKind.ESCALATES_TO, 0.8)
    g.add_edge("return_initiation", "refunds", EdgeKind.ESCALATES_TO, 1.5)
    g.add_edge("return_initiation", "exchanges_replacements", EdgeKind.ESCALATES_TO, 1.0)
    g.add_edge("warranty_repair", "support_escalation", EdgeKind.ESCALATES_TO, 0.7)

    # --- REQUIRES (state presupposition) ---------------------------------
    g.add_edge("order_editing", "order_confirmation", EdgeKind.REQUIRES, 1.0)
    g.add_edge("tracking", "order_confirmation", EdgeKind.REQUIRES, 1.0)
    g.add_edge("delivery_exceptions", "order_confirmation", EdgeKind.REQUIRES, 1.0)
    g.add_edge("return_initiation", "order_confirmation", EdgeKind.REQUIRES, 1.0)
    g.add_edge("refunds", "return_initiation", EdgeKind.REQUIRES, 1.0)
    g.add_edge("exchanges_replacements", "order_confirmation", EdgeKind.REQUIRES, 1.0)
    g.add_edge("subscriptions", "identity_login", EdgeKind.REQUIRES, 0.5)

    # --- COMPLEMENTS / SUBSTITUTES (discovery branching) -----------------
    g.add_edge("exact_product_id", "complements_bundles", EdgeKind.COMPLEMENTS, 1.0)
    g.add_edge("exact_product_id", "compatibility", EdgeKind.COMPLEMENTS, 0.8)
    g.add_edge("availability", "product_comparison", EdgeKind.SUBSTITUTES, 0.6)

    return g
