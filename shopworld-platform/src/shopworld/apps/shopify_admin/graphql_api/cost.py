"""
GraphQL query cost model and throttle simulator.

Shopify Admin GraphQL charges query cost points per field and connection node.
The SimulatedThrottle tracks the remaining budget for an episode and restores
points over simulated time.

Reference numbers from shopify-graphql-api-overview-gpt-5.5.md:
  - Max single-query cost:  1,000 points
  - Standard restore rate:  100 points/sec
  - Advanced restore rate:  200 points/sec
  - Plus restore rate:     1,000 points/sec
  - Enterprise rate:       2,000 points/sec

Cost model (simplified approximation of Shopify's actual model):
  - Scalar field:           1 point
  - Object field:           1 point
  - Connection (first N):   1 + N points   (N = requested page size)
  - Mutation:               10 points base + payload field costs

The field-level cost map below is intentionally approximate; it can be
refined against real Shopify introspection data later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


# ---------------------------------------------------------------------------
# Plan tiers
# ---------------------------------------------------------------------------

class ShopifyPlan(str, Enum):
    BASIC = "basic"
    SHOPIFY = "shopify"
    ADVANCED = "advanced"
    PLUS = "plus"
    ENTERPRISE = "enterprise"


RESTORE_RATE: Dict[ShopifyPlan, float] = {
    ShopifyPlan.BASIC:      50.0,
    ShopifyPlan.SHOPIFY:   100.0,
    ShopifyPlan.ADVANCED:  200.0,
    ShopifyPlan.PLUS:     1000.0,
    ShopifyPlan.ENTERPRISE: 2000.0,
}

MAX_BUCKET: Dict[ShopifyPlan, float] = {
    ShopifyPlan.BASIC:     1000.0,
    ShopifyPlan.SHOPIFY:   1000.0,
    ShopifyPlan.ADVANCED:  1000.0,
    ShopifyPlan.PLUS:     2000.0,
    ShopifyPlan.ENTERPRISE: 2000.0,
}

# Per-query hard cap
MAX_SINGLE_QUERY_COST = 1000


# ---------------------------------------------------------------------------
# Field cost table
# ---------------------------------------------------------------------------

# Maps top-level operation name → estimated cost points.
# Costs for connection fields include a per-node factor.
# This is a first-pass approximation; expand as needed.

OPERATION_BASE_COST: Dict[str, int] = {
    # Queries
    "shop": 1,
    "node": 1,
    "product": 2,
    "products": 2,          # + 1 per edge
    "productVariants": 2,   # + 1 per edge
    "order": 2,
    "orders": 2,
    "customer": 2,
    "customers": 2,
    "inventoryItem": 2,
    "inventoryItems": 2,
    "inventoryLevels": 2,
    "location": 1,
    "locations": 1,
    "fulfillmentOrder": 2,
    "fulfillmentOrders": 2,
    "collections": 2,
    "collection": 2,
    "discountNodes": 2,
    "metafields": 2,
    "metaobjects": 2,
    "abandonedCheckouts": 2,
    # Mutations (base; payload fields add more)
    "productCreate": 10,
    "productUpdate": 10,
    "productSet": 10,
    "productVariantUpdate": 10,
    "inventoryAdjustQuantities": 10,
    "inventoryItemUpdate": 10,
    "orderUpdate": 10,
    "orderClose": 10,
    "orderCancel": 10,
    "fulfillmentCreateV2": 10,
    "customerCreate": 10,
    "customerUpdate": 10,
    "tagsAdd": 10,
    "tagsRemove": 10,
    "metafieldsSet": 10,
    "refundCreate": 10,
    "discountCodeBasicCreate": 10,
}

PER_NODE_COST = 1  # added per requested connection node


def estimate_cost(operation_name: str, connection_size: int = 0) -> int:
    """
    Estimate the cost of a single GraphQL operation.

    Args:
        operation_name:  Top-level field name (e.g. "orders").
        connection_size: Number of nodes requested in a connection query.
    """
    base = OPERATION_BASE_COST.get(operation_name, 5)
    return base + connection_size * PER_NODE_COST


# ---------------------------------------------------------------------------
# Throttle simulator
# ---------------------------------------------------------------------------

@dataclass
class ThrottleState:
    """
    Leaky-bucket throttle matching Shopify's restore-rate model.

    Usage:
        throttle = ThrottleState(plan=ShopifyPlan.SHOPIFY)
        ok, remaining = throttle.consume(estimated_cost, elapsed_seconds)
        if not ok:
            # agent should back off
    """

    plan: ShopifyPlan = ShopifyPlan.SHOPIFY
    available: float = field(init=False)
    max_bucket: float = field(init=False)
    restore_rate: float = field(init=False)

    def __post_init__(self) -> None:
        self.max_bucket = MAX_BUCKET[self.plan]
        self.restore_rate = RESTORE_RATE[self.plan]
        self.available = self.max_bucket

    def restore(self, elapsed_seconds: float) -> None:
        """Add restored points for elapsed wall/simulated time."""
        self.available = min(
            self.max_bucket,
            self.available + elapsed_seconds * self.restore_rate,
        )

    def consume(
        self,
        cost: int,
        elapsed_seconds: float = 0.0,
    ) -> tuple[bool, float]:
        """
        Attempt to consume `cost` points after restoring for elapsed time.

        Returns:
            (ok, remaining_available)
            ok=False means the request should be throttled (429).
        """
        self.restore(elapsed_seconds)

        if cost > MAX_SINGLE_QUERY_COST:
            return False, self.available

        if cost > self.available:
            return False, self.available

        self.available -= cost
        return True, self.available

    @property
    def throttle_status(self) -> dict:
        """Shopify-style throttleStatus payload for query extensions."""
        return {
            "maximumAvailable": self.max_bucket,
            "currentlyAvailable": round(self.available, 1),
            "restoreRate": self.restore_rate,
        }
