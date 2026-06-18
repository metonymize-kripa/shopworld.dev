"""
Assembles the full expanded Shopify Admin GraphQL schema.

Usage:
    from shopworld.apps.shopify_admin.graphql_api.schema import build_schema
    schema = build_schema()
    result = await schema.execute(query, context_value={
        "session": db_session,
        "granted_scopes": {"read_orders", "write_orders"},
        "throttle": throttle_state,  # optional ThrottleState instance
    })

The schema wires together all query and mutation resolvers from the
graphql_api.queries.* and graphql_api.mutations.* submodules.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

import strawberry
from strawberry import Schema
from strawberry.types import Info

from shopworld.apps.shopify_admin.graphql_api.cost import ThrottleState
from shopworld.apps.shopify_admin.graphql_api.queries.catalog import (
    ProductType, ProductConnection, ProductVariantConnection, CollectionType, CollectionConnection,
    resolve_product, resolve_products, resolve_product_variants,
    resolve_collection, resolve_collections,
)
from shopworld.apps.shopify_admin.graphql_api.queries.inventory import (
    LocationType, LocationConnection, InventoryItemType, InventoryItemConnection,
    InventoryLevelConnection,
    resolve_location, resolve_locations,
    resolve_inventory_item, resolve_inventory_items, resolve_inventory_levels,
)
from shopworld.apps.shopify_admin.graphql_api.queries.orders import (
    OrderType, OrderConnection, FulfillmentOrderType, FulfillmentOrderConnection,
    resolve_order, resolve_orders, resolve_fulfillment_order, resolve_fulfillment_orders,
)
from shopworld.apps.shopify_admin.graphql_api.queries.customers import (
    CustomerType, CustomerConnection,
    resolve_customer, resolve_customers,
)
from shopworld.apps.shopify_admin.graphql_api.queries.discounts import (
    DiscountNodeConnection, resolve_discount_nodes,
)
from shopworld.apps.shopify_admin.graphql_api.queries.metafields import (
    MetafieldConnection, resolve_metafields,
)
from shopworld.apps.shopify_admin.graphql_api.mutations.catalog import (
    ProductCreateInput, ProductUpdateInput, ProductVariantUpdateInput,
    ProductCreatePayload, ProductUpdatePayload, ProductVariantUpdatePayload,
    resolve_product_create, resolve_product_update, resolve_product_variant_update,
)
from shopworld.apps.shopify_admin.graphql_api.mutations.inventory import (
    InventoryAdjustQuantityInput, InventoryItemUpdateInput,
    InventoryAdjustQuantitiesPayload, InventoryItemUpdatePayload,
    resolve_inventory_adjust_quantities, resolve_inventory_item_update,
)
from shopworld.apps.shopify_admin.graphql_api.mutations.orders import (
    OrderUpdateInput, OrderCancelInput, RefundCreateInput, FulfillmentCreateInput,
    OrderUpdatePayload, OrderClosePayload, OrderCancelPayload,
    RefundCreatePayload, FulfillmentCreatePayload,
    resolve_order_update, resolve_order_close, resolve_order_cancel,
    resolve_refund_create, resolve_fulfillment_create,
)
from shopworld.apps.shopify_admin.graphql_api.mutations.customers import (
    CustomerCreateInput, CustomerUpdateInput,
    CustomerCreatePayload, CustomerUpdatePayload, TagsAddPayload, TagsRemovePayload,
    resolve_customer_create, resolve_customer_update, resolve_tags_add, resolve_tags_remove,
)
from shopworld.apps.shopify_admin.graphql_api.mutations.metafields import (
    MetafieldSetInput, MetafieldsSetPayload, resolve_metafields_set,
)
from shopworld.apps.shopify_admin.graphql_api.mutations.discounts import (
    DiscountCodeBasicInput, DiscountCodeUpdateInput,
    DiscountCodeBasicCreatePayload, DiscountCodeUpdatePayload,
    resolve_discount_code_basic_create, resolve_discount_code_update,
)


# ---------------------------------------------------------------------------
# Shop type (static for now)
# ---------------------------------------------------------------------------

@strawberry.type
class ShopType:
    id: str
    name: str
    myshopify_domain: str
    currency_code: str
    timezone: str
    plan: str


# ---------------------------------------------------------------------------
# Query root
# ---------------------------------------------------------------------------

@strawberry.type
class Query:
    """ShopWorld — expanded Shopify Admin GraphQL queries."""

    @strawberry.field
    def shop(self) -> ShopType:
        return ShopType(
            id="gid://shopify/Shop/1",
            name="ShopWorld Simulated Store",
            myshopify_domain="shopworld-sim.myshopify.com",
            currency_code="USD",
            timezone="America/New_York",
            plan="shopify",
        )

    # -- Catalog --

    @strawberry.field
    def product(self, info: Info, id: str) -> Optional[ProductType]:
        return resolve_product(info, id)

    @strawberry.field
    def products(
        self, info: Info,
        first: int = 10, after: Optional[str] = None, query: Optional[str] = None,
    ) -> ProductConnection:
        return resolve_products(info, first, after, query)

    @strawberry.field
    def product_variants(
        self, info: Info,
        product_id: Optional[str] = None,
        first: int = 10, after: Optional[str] = None,
    ) -> ProductVariantConnection:
        return resolve_product_variants(info, product_id, first, after)

    @strawberry.field
    def collection(self, info: Info, id: str) -> Optional[CollectionType]:
        return resolve_collection(info, id)

    @strawberry.field
    def collections(
        self, info: Info, first: int = 10, after: Optional[str] = None,
    ) -> CollectionConnection:
        return resolve_collections(info, first, after)

    # -- Inventory --

    @strawberry.field
    def location(self, info: Info, id: str) -> Optional[LocationType]:
        return resolve_location(info, id)

    @strawberry.field
    def locations(
        self, info: Info,
        first: int = 10, after: Optional[str] = None, include_legacy: bool = False,
    ) -> LocationConnection:
        return resolve_locations(info, first, after, include_legacy)

    @strawberry.field
    def inventory_item(self, info: Info, id: str) -> Optional[InventoryItemType]:
        return resolve_inventory_item(info, id)

    @strawberry.field
    def inventory_items(
        self, info: Info,
        first: int = 10, after: Optional[str] = None, query: Optional[str] = None,
    ) -> InventoryItemConnection:
        return resolve_inventory_items(info, first, after, query)

    @strawberry.field
    def inventory_levels(
        self, info: Info,
        first: int = 10, after: Optional[str] = None,
        location_ids: Optional[List[str]] = None,
        inventory_item_ids: Optional[List[str]] = None,
    ) -> InventoryLevelConnection:
        return resolve_inventory_levels(info, first, after, location_ids, inventory_item_ids)

    # -- Orders --

    @strawberry.field
    def order(self, info: Info, id: str) -> Optional[OrderType]:
        return resolve_order(info, id)

    @strawberry.field
    def orders(
        self, info: Info,
        first: int = 10, after: Optional[str] = None,
        query: Optional[str] = None,
        sort_key: Optional[str] = None,
        reverse: bool = False,
    ) -> OrderConnection:
        return resolve_orders(info, first, after, query, sort_key, reverse)

    @strawberry.field
    def fulfillment_order(self, info: Info, id: str) -> Optional[FulfillmentOrderType]:
        return resolve_fulfillment_order(info, id)

    @strawberry.field
    def fulfillment_orders(
        self, info: Info,
        order_id: Optional[str] = None,
        first: int = 10, after: Optional[str] = None,
    ) -> FulfillmentOrderConnection:
        return resolve_fulfillment_orders(info, order_id, first, after)

    # -- Customers --

    @strawberry.field
    def customer(self, info: Info, id: str) -> Optional[CustomerType]:
        return resolve_customer(info, id)

    @strawberry.field
    def customers(
        self, info: Info,
        first: int = 10, after: Optional[str] = None, query: Optional[str] = None,
    ) -> CustomerConnection:
        return resolve_customers(info, first, after, query)

    # -- Discounts --

    @strawberry.field
    def discount_nodes(
        self, info: Info,
        first: int = 10, after: Optional[str] = None, query: Optional[str] = None,
    ) -> DiscountNodeConnection:
        return resolve_discount_nodes(info, first, after, query)

    # -- Metafields --

    @strawberry.field
    def metafields(
        self, info: Info,
        owner_type: Optional[str] = None,
        owner_id: Optional[str] = None,
        namespace: Optional[str] = None,
        first: int = 10, after: Optional[str] = None,
    ) -> MetafieldConnection:
        return resolve_metafields(info, owner_type, owner_id, namespace, first, after)


# ---------------------------------------------------------------------------
# Mutation root
# ---------------------------------------------------------------------------

@strawberry.type
class Mutation:
    """ShopWorld — expanded Shopify Admin GraphQL mutations."""

    # -- Catalog --

    @strawberry.mutation
    def product_create(self, info: Info, input: ProductCreateInput) -> ProductCreatePayload:
        return resolve_product_create(info, input)

    @strawberry.mutation
    def product_update(self, info: Info, input: ProductUpdateInput) -> ProductUpdatePayload:
        return resolve_product_update(info, input)

    @strawberry.mutation
    def product_variant_update(
        self, info: Info, input: ProductVariantUpdateInput,
    ) -> ProductVariantUpdatePayload:
        return resolve_product_variant_update(info, input)

    # -- Inventory --

    @strawberry.mutation
    def inventory_adjust_quantities(
        self, info: Info, input: List[InventoryAdjustQuantityInput],
    ) -> InventoryAdjustQuantitiesPayload:
        return resolve_inventory_adjust_quantities(info, input)

    @strawberry.mutation
    def inventory_item_update(
        self, info: Info, id: str, input: InventoryItemUpdateInput,
    ) -> InventoryItemUpdatePayload:
        return resolve_inventory_item_update(info, id, input)

    # -- Orders --

    @strawberry.mutation
    def order_update(self, info: Info, input: OrderUpdateInput) -> OrderUpdatePayload:
        return resolve_order_update(info, input)

    @strawberry.mutation
    def order_close(self, info: Info, id: str) -> OrderClosePayload:
        return resolve_order_close(info, id)

    @strawberry.mutation
    def order_cancel(self, info: Info, input: OrderCancelInput) -> OrderCancelPayload:
        return resolve_order_cancel(info, input)

    @strawberry.mutation
    def refund_create(self, info: Info, input: RefundCreateInput) -> RefundCreatePayload:
        return resolve_refund_create(info, input)

    @strawberry.mutation
    def fulfillment_create_v2(
        self, info: Info, input: FulfillmentCreateInput,
    ) -> FulfillmentCreatePayload:
        return resolve_fulfillment_create(info, input)

    # -- Customers --

    @strawberry.mutation
    def customer_create(self, info: Info, input: CustomerCreateInput) -> CustomerCreatePayload:
        return resolve_customer_create(info, input)

    @strawberry.mutation
    def customer_update(self, info: Info, input: CustomerUpdateInput) -> CustomerUpdatePayload:
        return resolve_customer_update(info, input)

    @strawberry.mutation
    def tags_add(self, info: Info, id: str, tags: List[str]) -> TagsAddPayload:
        return resolve_tags_add(info, id, tags)

    @strawberry.mutation
    def tags_remove(self, info: Info, id: str, tags: List[str]) -> TagsRemovePayload:
        return resolve_tags_remove(info, id, tags)

    # -- Metafields --

    @strawberry.mutation
    def metafields_set(
        self, info: Info, metafields: List[MetafieldSetInput],
    ) -> MetafieldsSetPayload:
        return resolve_metafields_set(info, metafields)

    # -- Discounts --

    @strawberry.mutation
    def discount_code_basic_create(
        self, info: Info, basic_code_discount: DiscountCodeBasicInput,
    ) -> DiscountCodeBasicCreatePayload:
        return resolve_discount_code_basic_create(info, basic_code_discount)

    @strawberry.mutation
    def discount_code_update(
        self, info: Info, id: str, code_discount: DiscountCodeUpdateInput,
    ) -> DiscountCodeUpdatePayload:
        return resolve_discount_code_update(info, id, code_discount)


# ---------------------------------------------------------------------------
# Schema factory
# ---------------------------------------------------------------------------

def build_schema() -> Schema:
    """Return the assembled Strawberry schema."""
    return strawberry.Schema(query=Query, mutation=Mutation)


class ShopWorldGraphQLV2:
    """
    Drop-in replacement for the original ShopWorldGraphQL wrapper,
    using the expanded schema with scope enforcement and cost tracking.
    """

    def __init__(
        self,
        session,
        granted_scopes: Optional[Set[str]] = None,
        throttle: Optional[ThrottleState] = None,
    ):
        self.session = session
        self.granted_scopes = granted_scopes or set()
        self.throttle = throttle
        self._schema = build_schema()

    async def execute(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        context = {
            "session": self.session,
            "granted_scopes": self.granted_scopes,
            "throttle": self.throttle,
        }
        result = await self._schema.execute(
            query,
            variable_values=variables,
            context_value=context,
            operation_name=operation_name,
        )

        if result.errors:
            return {"data": None, "errors": [str(e) for e in result.errors]}

        return {"data": result.data, "errors": None}
