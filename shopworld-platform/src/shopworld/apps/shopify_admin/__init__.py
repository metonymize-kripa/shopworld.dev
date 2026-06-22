"""Shopify Admin simulator — models and canonical GraphQL schema.

The canonical GraphQL implementation lives in ``graphql_api``:

    from shopworld.apps.shopify_admin.graphql_api.schema import build_schema, ShopWorldGraphQLV2

``ShopWorldGraphQL`` (the original single-file implementation) is still
importable for compatibility but will be removed in a future release.
"""

from shopworld.apps.shopify_admin.models import (
    Product, ProductVariant, InventoryItem, InventoryLevel,
    Location, Customer, Order, OrderLineItem, FulfillmentOrder,
    Fulfillment, Refund, Return, DiscountCode, Metafield, Collection,
)
from shopworld.apps.shopify_admin.graphql_api.schema import build_schema, ShopWorldGraphQLV2

__all__ = [
    "Product", "ProductVariant", "InventoryItem", "InventoryLevel",
    "Location", "Customer", "Order", "OrderLineItem",
    "FulfillmentOrder", "Fulfillment", "Refund", "Return", "DiscountCode",
    "Metafield", "Collection",
    "build_schema", "ShopWorldGraphQLV2",
]
