"""
Shopify Admin API scope definitions and per-operation enforcement.

Each GraphQL operation requires one or more OAuth scopes.  The scope
check happens inside the resolver so agents get a realistic
FORBIDDEN / UNAUTHENTICATED error rather than a silent no-op.

Scope names mirror the real Shopify Admin API scopes:
  https://shopify.dev/docs/api/usage/access-scopes
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Set


# ---------------------------------------------------------------------------
# Canonical scope strings
# ---------------------------------------------------------------------------

class Scope:
    READ_PRODUCTS        = "read_products"
    WRITE_PRODUCTS       = "write_products"
    READ_ORDERS          = "read_orders"
    WRITE_ORDERS         = "write_orders"
    READ_ALL_ORDERS      = "read_all_orders"
    READ_CUSTOMERS       = "read_customers"
    WRITE_CUSTOMERS      = "write_customers"
    READ_INVENTORY       = "read_inventory"
    WRITE_INVENTORY      = "write_inventory"
    READ_FULFILLMENTS    = "read_fulfillments"
    WRITE_FULFILLMENTS   = "write_fulfillments"
    READ_SHIPPING        = "read_shipping"
    WRITE_SHIPPING       = "write_shipping"
    READ_DISCOUNTS       = "read_discounts"
    WRITE_DISCOUNTS      = "write_discounts"
    READ_PRICE_RULES     = "read_price_rules"
    WRITE_PRICE_RULES    = "write_price_rules"
    READ_METAFIELDS      = "read_metafields"          # implicit on most resources
    WRITE_METAFIELDS     = "write_metafields"
    READ_METAOBJECTS     = "read_metaobjects"
    WRITE_METAOBJECTS    = "write_metaobjects"
    READ_REPORTS         = "read_reports"
    READ_ANALYTICS       = "read_analytics"
    READ_LOCATIONS       = "read_locations"


# ---------------------------------------------------------------------------
# Per-operation scope requirements
# Maps operation name → minimum set of scopes (any one is sufficient unless
# all_required=True is noted in a comment).
# ---------------------------------------------------------------------------

OPERATION_SCOPES: Dict[str, FrozenSet[str]] = {
    # --- Queries ---
    "shop":                  frozenset(),                          # public
    "node":                  frozenset(),                          # resolved per-type
    "product":               frozenset([Scope.READ_PRODUCTS]),
    "products":              frozenset([Scope.READ_PRODUCTS]),
    "productVariants":       frozenset([Scope.READ_PRODUCTS]),
    "collection":            frozenset([Scope.READ_PRODUCTS]),
    "collections":           frozenset([Scope.READ_PRODUCTS]),
    "order":                 frozenset([Scope.READ_ORDERS, Scope.READ_ALL_ORDERS]),
    "orders":                frozenset([Scope.READ_ORDERS, Scope.READ_ALL_ORDERS]),
    "fulfillmentOrder":      frozenset([Scope.READ_ORDERS, Scope.READ_FULFILLMENTS]),
    "fulfillmentOrders":     frozenset([Scope.READ_ORDERS, Scope.READ_FULFILLMENTS]),
    "abandonedCheckouts":    frozenset([Scope.READ_ORDERS]),
    "customer":              frozenset([Scope.READ_CUSTOMERS]),
    "customers":             frozenset([Scope.READ_CUSTOMERS]),
    "inventoryItem":         frozenset([Scope.READ_INVENTORY]),
    "inventoryItems":        frozenset([Scope.READ_INVENTORY]),
    "inventoryLevels":       frozenset([Scope.READ_INVENTORY]),
    "location":              frozenset([Scope.READ_LOCATIONS]),
    "locations":             frozenset([Scope.READ_LOCATIONS]),
    "discountNodes":         frozenset([Scope.READ_DISCOUNTS, Scope.READ_PRICE_RULES]),
    "metafields":            frozenset([Scope.READ_METAFIELDS]),
    "metaobjects":           frozenset([Scope.READ_METAOBJECTS]),
    # --- Mutations ---
    "productCreate":         frozenset([Scope.WRITE_PRODUCTS]),
    "productUpdate":         frozenset([Scope.WRITE_PRODUCTS]),
    "productSet":            frozenset([Scope.WRITE_PRODUCTS]),
    "productVariantUpdate":  frozenset([Scope.WRITE_PRODUCTS]),
    "inventoryAdjustQuantities": frozenset([Scope.WRITE_INVENTORY]),
    "inventoryItemUpdate":   frozenset([Scope.WRITE_INVENTORY]),
    "orderUpdate":           frozenset([Scope.WRITE_ORDERS]),
    "orderClose":            frozenset([Scope.WRITE_ORDERS]),
    "orderCancel":           frozenset([Scope.WRITE_ORDERS]),
    "fulfillmentCreateV2":   frozenset([Scope.WRITE_FULFILLMENTS]),
    "fulfillmentOrderAcceptFulfillmentRequest": frozenset([Scope.WRITE_FULFILLMENTS]),
    "customerCreate":        frozenset([Scope.WRITE_CUSTOMERS]),
    "customerUpdate":        frozenset([Scope.WRITE_CUSTOMERS]),
    "tagsAdd":               frozenset([Scope.WRITE_PRODUCTS, Scope.WRITE_ORDERS, Scope.WRITE_CUSTOMERS]),
    "tagsRemove":            frozenset([Scope.WRITE_PRODUCTS, Scope.WRITE_ORDERS, Scope.WRITE_CUSTOMERS]),
    "metafieldsSet":         frozenset([Scope.WRITE_METAFIELDS]),
    "refundCreate":          frozenset([Scope.WRITE_ORDERS]),
    "discountCodeBasicCreate": frozenset([Scope.WRITE_DISCOUNTS, Scope.WRITE_PRICE_RULES]),
    "discountCodeUpdate":    frozenset([Scope.WRITE_DISCOUNTS, Scope.WRITE_PRICE_RULES]),
    # Shipments (queried via fulfillment/tracking data)
    "shipments":             frozenset([Scope.READ_ORDERS, Scope.READ_FULFILLMENTS]),
    # Inventory reservation
    "inventoryReserveQuantities": frozenset([Scope.WRITE_INVENTORY]),
    # Returns (physical item returns, distinct from financial refunds)
    "returns":               frozenset([Scope.READ_ORDERS, Scope.READ_ALL_ORDERS]),
    "returnCreate":          frozenset([Scope.WRITE_ORDERS]),
}

# Predefined scope bundles agents can be granted (mirrors authority levels)
SCOPE_BUNDLES: Dict[str, List[str]] = {
    "read_only": [
        Scope.READ_PRODUCTS, Scope.READ_ORDERS, Scope.READ_CUSTOMERS,
        Scope.READ_INVENTORY, Scope.READ_FULFILLMENTS, Scope.READ_DISCOUNTS,
        Scope.READ_LOCATIONS, Scope.READ_METAFIELDS, Scope.READ_METAOBJECTS,
    ],
    "support_operator": [
        Scope.READ_PRODUCTS, Scope.READ_ORDERS, Scope.READ_ALL_ORDERS,
        Scope.READ_CUSTOMERS, Scope.READ_INVENTORY, Scope.READ_FULFILLMENTS,
        Scope.READ_LOCATIONS, Scope.WRITE_ORDERS, Scope.WRITE_CUSTOMERS,
        Scope.READ_METAFIELDS, Scope.WRITE_METAFIELDS,
    ],
    "fulfillment_operator": [
        Scope.READ_PRODUCTS, Scope.READ_ORDERS, Scope.READ_ALL_ORDERS,
        Scope.READ_INVENTORY, Scope.READ_FULFILLMENTS, Scope.READ_LOCATIONS,
        Scope.WRITE_FULFILLMENTS, Scope.WRITE_INVENTORY, Scope.WRITE_ORDERS,
        Scope.READ_SHIPPING, Scope.WRITE_SHIPPING,
    ],
    "catalog_operator": [
        Scope.READ_PRODUCTS, Scope.WRITE_PRODUCTS,
        Scope.READ_INVENTORY, Scope.WRITE_INVENTORY,
        Scope.READ_METAFIELDS, Scope.WRITE_METAFIELDS,
        Scope.READ_METAOBJECTS, Scope.WRITE_METAOBJECTS,
        Scope.READ_LOCATIONS,
    ],
    "discount_operator": [
        Scope.READ_PRODUCTS, Scope.READ_ORDERS,
        Scope.READ_DISCOUNTS, Scope.WRITE_DISCOUNTS,
        Scope.READ_PRICE_RULES, Scope.WRITE_PRICE_RULES,
    ],
    "full_operator": [
        Scope.READ_PRODUCTS, Scope.WRITE_PRODUCTS,
        Scope.READ_ORDERS, Scope.WRITE_ORDERS, Scope.READ_ALL_ORDERS,
        Scope.READ_CUSTOMERS, Scope.WRITE_CUSTOMERS,
        Scope.READ_INVENTORY, Scope.WRITE_INVENTORY,
        Scope.READ_FULFILLMENTS, Scope.WRITE_FULFILLMENTS,
        Scope.READ_SHIPPING, Scope.WRITE_SHIPPING,
        Scope.READ_DISCOUNTS, Scope.WRITE_DISCOUNTS,
        Scope.READ_PRICE_RULES, Scope.WRITE_PRICE_RULES,
        Scope.READ_LOCATIONS,
        Scope.READ_METAFIELDS, Scope.WRITE_METAFIELDS,
        Scope.READ_METAOBJECTS, Scope.WRITE_METAOBJECTS,
    ],
}


# ---------------------------------------------------------------------------
# Enforcement helper
# ---------------------------------------------------------------------------

class ScopeError(Exception):
    """Raised when an operation is attempted without the required scope."""

    def __init__(self, operation: str, required: FrozenSet[str], granted: Set[str]):
        self.operation = operation
        self.required = required
        self.granted = granted
        super().__init__(
            f"Access denied for '{operation}': requires one of {sorted(required)}, "
            f"granted={sorted(granted)}"
        )


def check_scope(operation: str, granted_scopes: Set[str]) -> None:
    """
    Raise ScopeError if the operation cannot be performed with the
    granted scopes.

    For operations with multiple acceptable scopes, any single match is
    sufficient (OR semantics).  An empty required set means public access.
    """
    required = OPERATION_SCOPES.get(operation, frozenset())
    if not required:
        return
    if required & granted_scopes:
        return
    raise ScopeError(operation, required, granted_scopes)
