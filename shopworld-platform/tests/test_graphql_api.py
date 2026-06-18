"""
Tests for the expanded Shopify Admin GraphQL simulator.

Covers:
  - Pagination helpers (encode/decode cursors, paginate())
  - Cost model and ThrottleState
  - Scope enforcement (check_scope)
  - All query resolvers (products, variants, inventory, orders, customers,
    fulfillmentOrders, discounts, metafields, locations)
  - All mutation resolvers (productCreate/Update/variantUpdate,
    inventoryAdjustQuantities/itemUpdate, orderUpdate/close/cancel,
    refundCreate, fulfillmentCreateV2, customerCreate/Update,
    tagsAdd/Remove, metafieldsSet, discountCodeBasicCreate/Update)
  - Scope errors surfaced through userErrors
  - Cursor-based pagination (hasNextPage, endCursor, after)
"""

from __future__ import annotations

import pytest
from decimal import Decimal

from sqlmodel import Session

from shopworld.apps.lib.db import init_database
from shopworld.apps.shopify_admin.models import (
    Customer,
    DiscountCode,
    FulfillmentOrder,
    InventoryItem,
    InventoryLevel,
    Location,
    Metafield,
    Order,
    Product,
    ProductVariant,
)
from shopworld.apps.shopify_admin.graphql_api.pagination import (
    encode_cursor,
    decode_cursor,
    paginate,
)
from shopworld.apps.shopify_admin.graphql_api.cost import (
    ThrottleState,
    ShopifyPlan,
    estimate_cost,
    MAX_SINGLE_QUERY_COST,
)
from shopworld.apps.shopify_admin.graphql_api.scopes import (
    check_scope,
    ScopeError,
    SCOPE_BUNDLES,
    Scope,
)
from shopworld.apps.shopify_admin.graphql_api.schema import (
    ShopWorldGraphQLV2,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    """In-memory SQLite database, reset for each test."""
    db = init_database(":memory:")
    yield db


@pytest.fixture
def session(db):
    """Open session for direct DB setup in tests."""
    with db.session() as s:
        yield s


@pytest.fixture
def gql(db):
    """ShopWorldGraphQLV2 with full_operator scopes and a fresh DB."""
    with db.session() as s:
        yield ShopWorldGraphQLV2(
            session=s,
            granted_scopes=set(SCOPE_BUNDLES["full_operator"]),
        )


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def seed_product(session: Session, suffix: str = "1") -> Product:
    p = Product(
        id=f"gid://shopify/Product/{suffix}",
        title=f"Test Product {suffix}",
        handle=f"test-product-{suffix}",
        description="A test product",
        vendor="TestCo",
        product_type="Apparel",
        status="ACTIVE",
        tags=["summer", "sale"],
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def seed_variant(session: Session, product_id: str, suffix: str = "1") -> ProductVariant:
    item = InventoryItem(
        id=f"gid://shopify/InventoryItem/{suffix}",
        sku=f"SKU-{suffix}",
        tracked=True,
    )
    session.add(item)

    v = ProductVariant(
        id=f"gid://shopify/ProductVariant/{suffix}",
        product_id=product_id,
        sku=f"SKU-{suffix}",
        price=Decimal("29.99"),
        option1="Blue",
        option2="M",
        inventory_item_id=item.id,
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


def seed_location(session: Session, suffix: str = "1") -> Location:
    loc = Location(
        id=f"gid://shopify/Location/{suffix}",
        name=f"Warehouse {suffix}",
        active=True,
    )
    session.add(loc)
    session.commit()
    session.refresh(loc)
    return loc


def seed_inventory_level(
    session: Session, item_id: str, location_id: str, available: int = 50
) -> InventoryLevel:
    lvl = InventoryLevel(
        inventory_item_id=item_id,
        location_id=location_id,
        available=available,
        incoming=0,
        reserved=0,
        committed=0,
        damaged=0,
    )
    session.add(lvl)
    session.commit()
    session.refresh(lvl)
    return lvl


def seed_customer(session: Session, suffix: str = "1") -> Customer:
    c = Customer(
        id=f"gid://shopify/Customer/{suffix}",
        email=f"customer{suffix}@example.com",
        first_name="Alice",
        last_name="Smith",
        tags=[],
        orders_count=2,
        total_spent=Decimal("149.99"),
    )
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


def seed_order(session: Session, customer_id: str = None, suffix: str = "1") -> Order:
    o = Order(
        id=f"gid://shopify/Order/{suffix}",
        name=f"#{1000 + int(suffix)}",
        email="buyer@example.com",
        customer_id=customer_id,
        total_price=Decimal("79.99"),
        subtotal_price=Decimal("69.99"),
        total_tax=Decimal("10.00"),
        total_discounts=Decimal("0.00"),
        display_financial_status="PAID",
        display_fulfillment_status="UNFULFILLED",
    )
    session.add(o)
    session.commit()
    session.refresh(o)
    return o


def seed_fulfillment_order(session: Session, order_id: str, suffix: str = "1") -> FulfillmentOrder:
    fo = FulfillmentOrder(
        id=f"gid://shopify/FulfillmentOrder/{suffix}",
        order_id=order_id,
        status="OPEN",
        supported_actions=["CREATE_FULFILLMENT"],
    )
    session.add(fo)
    session.commit()
    session.refresh(fo)
    return fo


def seed_discount(session: Session, suffix: str = "1") -> DiscountCode:
    d = DiscountCode(
        id=f"gid://shopify/DiscountCode/{suffix}",
        code=f"SAVE{suffix}",
        discount_type="PERCENTAGE",
        value=Decimal("10"),
        status="ACTIVE",
    )
    session.add(d)
    session.commit()
    session.refresh(d)
    return d


def seed_metafield(session: Session, owner_id: str, suffix: str = "1") -> Metafield:
    m = Metafield(
        id=f"gid://shopify/Metafield/{suffix}",
        namespace="custom",
        key="size_guide",
        value="See chart",
        type="single_line_text_field",
        owner_type="product",
        owner_id=owner_id,
    )
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


# ---------------------------------------------------------------------------
# Pagination helpers
# ---------------------------------------------------------------------------

class TestPagination:

    def test_encode_decode_roundtrip(self):
        cursor = encode_cursor("products", "gid://shopify/Product/42")
        table, row_id = decode_cursor(cursor)
        assert table == "products"
        assert row_id == "gid://shopify/Product/42"

    def test_decode_bad_cursor_raises(self):
        with pytest.raises(ValueError):
            decode_cursor("not-valid-base64!!!")

    def test_paginate_first_page(self):
        class Obj:
            def __init__(self, id): self.id = id

        objs = [Obj(i) for i in range(20)]
        page, info = paginate(objs, first=5, after=None, table="t")
        assert len(page) == 5
        assert info.has_next_page is True
        assert info.has_previous_page is False

    def test_paginate_last_page(self):
        class Obj:
            def __init__(self, id): self.id = id

        objs = [Obj(i) for i in range(7)]
        page, info = paginate(objs, first=5, after=None, table="t")
        # first page of 7 → 5 items, hasNext=True
        assert info.has_next_page is True

        cursor = encode_cursor("t", objs[4].id)
        page2, info2 = paginate(objs, first=5, after=cursor, table="t")
        assert len(page2) == 2
        assert info2.has_next_page is False
        assert info2.has_previous_page is True

    def test_paginate_caps_at_250(self):
        class Obj:
            def __init__(self, id): self.id = id

        objs = [Obj(i) for i in range(300)]
        page, _ = paginate(objs, first=300, after=None, table="t")
        assert len(page) == 250

    def test_paginate_empty_list(self):
        page, info = paginate([], first=10, after=None, table="t")
        assert page == []
        assert info.start_cursor is None
        assert info.end_cursor is None
        assert info.has_next_page is False


# ---------------------------------------------------------------------------
# Cost model
# ---------------------------------------------------------------------------

class TestCostModel:

    def test_estimate_known_operation(self):
        cost = estimate_cost("orders", connection_size=10)
        assert cost == 2 + 10  # base + per_node

    def test_estimate_mutation(self):
        cost = estimate_cost("refundCreate")
        assert cost == 10

    def test_estimate_unknown_defaults(self):
        cost = estimate_cost("unknownField", connection_size=0)
        assert cost == 5

    def test_throttle_consume_ok(self):
        t = ThrottleState(plan=ShopifyPlan.SHOPIFY)
        ok, remaining = t.consume(100)
        assert ok is True
        assert remaining == 900.0

    def test_throttle_consume_insufficient(self):
        t = ThrottleState(plan=ShopifyPlan.SHOPIFY)
        t.available = 50
        ok, remaining = t.consume(100)
        assert ok is False

    def test_throttle_restores_over_time(self):
        t = ThrottleState(plan=ShopifyPlan.SHOPIFY)
        t.available = 0
        t.restore(elapsed_seconds=5)
        assert t.available == pytest.approx(500.0)  # 100 pts/sec × 5

    def test_throttle_restore_caps_at_max(self):
        t = ThrottleState(plan=ShopifyPlan.SHOPIFY)
        t.restore(elapsed_seconds=100)
        assert t.available == t.max_bucket

    def test_throttle_rejects_over_single_query_cap(self):
        t = ThrottleState(plan=ShopifyPlan.PLUS)
        ok, _ = t.consume(MAX_SINGLE_QUERY_COST + 1)
        assert ok is False

    def test_throttle_status_keys(self):
        t = ThrottleState(plan=ShopifyPlan.ADVANCED)
        status = t.throttle_status
        assert "maximumAvailable" in status
        assert "currentlyAvailable" in status
        assert "restoreRate" in status
        assert status["restoreRate"] == 200.0

    def test_plan_restore_rates(self):
        for plan, expected_rate in [
            (ShopifyPlan.SHOPIFY, 100.0),
            (ShopifyPlan.PLUS, 1000.0),
            (ShopifyPlan.ENTERPRISE, 2000.0),
        ]:
            t = ThrottleState(plan=plan)
            assert t.restore_rate == expected_rate


# ---------------------------------------------------------------------------
# Scope enforcement
# ---------------------------------------------------------------------------

class TestScopes:

    def test_public_operation_requires_no_scope(self):
        check_scope("shop", set())  # should not raise

    def test_read_operation_passes_with_scope(self):
        check_scope("orders", {Scope.READ_ORDERS})

    def test_read_operation_fails_without_scope(self):
        with pytest.raises(ScopeError):
            check_scope("orders", set())

    def test_write_operation_fails_with_read_only_scope(self):
        with pytest.raises(ScopeError):
            check_scope("productCreate", {Scope.READ_PRODUCTS})

    def test_write_operation_passes_with_write_scope(self):
        check_scope("productCreate", {Scope.WRITE_PRODUCTS})

    def test_scope_bundle_read_only_grants_no_writes(self):
        scopes = set(SCOPE_BUNDLES["read_only"])
        with pytest.raises(ScopeError):
            check_scope("productCreate", scopes)
        with pytest.raises(ScopeError):
            check_scope("refundCreate", scopes)

    def test_scope_bundle_full_operator_allows_everything(self):
        scopes = set(SCOPE_BUNDLES["full_operator"])
        for op in ("products", "orders", "customers", "refundCreate",
                   "productCreate", "customerUpdate", "metafieldsSet",
                   "discountCodeBasicCreate"):
            check_scope(op, scopes)  # none should raise

    def test_scope_error_message_is_informative(self):
        with pytest.raises(ScopeError) as exc_info:
            check_scope("refundCreate", {Scope.READ_ORDERS})
        assert "refundCreate" in str(exc_info.value)
        assert "write_orders" in str(exc_info.value)


# ---------------------------------------------------------------------------
# GraphQL query tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestQueryShop:

    async def test_shop_query(self, gql):
        result = await gql.execute("{ shop { id name currencyCode } }")
        assert result["errors"] is None
        shop = result["data"]["shop"]
        assert shop["id"] == "gid://shopify/Shop/1"
        assert shop["currencyCode"] == "USD"


@pytest.mark.asyncio
class TestQueryProducts:

    async def test_products_empty(self, gql):
        result = await gql.execute(
            "{ products(first: 10) { edges { node { id title } } pageInfo { hasNextPage } } }"
        )
        assert result["errors"] is None
        assert result["data"]["products"]["edges"] == []
        assert result["data"]["products"]["pageInfo"]["hasNextPage"] is False

    async def test_products_returns_seeded(self, gql, session):
        seed_product(session, "1")
        seed_product(session, "2")
        result = await gql.execute(
            "{ products(first: 10) { edges { node { id title status tags } } pageInfo { hasNextPage endCursor } } }"
        )
        assert result["errors"] is None
        edges = result["data"]["products"]["edges"]
        assert len(edges) == 2
        assert edges[0]["node"]["title"] == "Test Product 1"
        assert "summer" in edges[0]["node"]["tags"]

    async def test_products_pagination(self, gql, session):
        for i in range(1, 6):
            seed_product(session, str(i))

        page1 = await gql.execute(
            "{ products(first: 3) { edges { node { id } cursor } pageInfo { hasNextPage endCursor } } }"
        )
        assert page1["errors"] is None
        assert len(page1["data"]["products"]["edges"]) == 3
        assert page1["data"]["products"]["pageInfo"]["hasNextPage"] is True

        cursor = page1["data"]["products"]["pageInfo"]["endCursor"]
        page2 = await gql.execute(
            f'{{ products(first: 3, after: "{cursor}") {{ edges {{ node {{ id }} }} pageInfo {{ hasNextPage }} }} }}'
        )
        assert page2["errors"] is None
        assert len(page2["data"]["products"]["edges"]) == 2
        assert page2["data"]["products"]["pageInfo"]["hasNextPage"] is False

    async def test_product_by_id(self, gql, session):
        seed_product(session, "99")
        result = await gql.execute(
            '{ product(id: "gid://shopify/Product/99") { id title vendor } }'
        )
        assert result["errors"] is None
        assert result["data"]["product"]["title"] == "Test Product 99"
        assert result["data"]["product"]["vendor"] == "TestCo"

    async def test_product_not_found_returns_null(self, gql):
        result = await gql.execute('{ product(id: "gid://shopify/Product/nope") { id } }')
        assert result["errors"] is None
        assert result["data"]["product"] is None

    async def test_products_scope_error(self, db, session):
        seed_product(session, "1")
        gql_ro = ShopWorldGraphQLV2(session=session, granted_scopes=set())
        result = await gql_ro.execute(
            "{ products(first: 5) { edges { node { id } } } }"
        )
        assert result["errors"] is not None


@pytest.mark.asyncio
class TestQueryProductVariants:

    async def test_product_variants_for_product(self, gql, session):
        p = seed_product(session, "10")
        seed_variant(session, p.id, "10")
        seed_variant(session, p.id, "11")
        result = await gql.execute(
            '{ productVariants(productId: "gid://shopify/Product/10", first: 10) { edges { node { id sku price } } } }'
        )
        assert result["errors"] is None
        edges = result["data"]["productVariants"]["edges"]
        assert len(edges) == 2
        assert edges[0]["node"]["price"] == "29.99"

    async def test_product_variants_all(self, gql, session):
        p1 = seed_product(session, "20")
        p2 = seed_product(session, "21")
        seed_variant(session, p1.id, "20")
        seed_variant(session, p2.id, "21")
        result = await gql.execute(
            "{ productVariants(first: 10) { edges { node { id productId } } } }"
        )
        assert result["errors"] is None
        assert len(result["data"]["productVariants"]["edges"]) == 2


@pytest.mark.asyncio
class TestQueryInventory:

    async def test_locations_empty(self, gql):
        result = await gql.execute(
            "{ locations(first: 10) { edges { node { id name active } } } }"
        )
        assert result["errors"] is None
        assert result["data"]["locations"]["edges"] == []

    async def test_locations_returns_seeded(self, gql, session):
        seed_location(session, "1")
        seed_location(session, "2")
        result = await gql.execute(
            "{ locations(first: 10) { edges { node { id name } } } }"
        )
        assert result["errors"] is None
        assert len(result["data"]["locations"]["edges"]) == 2

    async def test_location_by_id(self, gql, session):
        seed_location(session, "5")
        result = await gql.execute(
            '{ location(id: "gid://shopify/Location/5") { id name active } }'
        )
        assert result["errors"] is None
        assert result["data"]["location"]["name"] == "Warehouse 5"

    async def test_inventory_items(self, gql, session):
        p = seed_product(session, "30")
        seed_variant(session, p.id, "30")
        result = await gql.execute(
            "{ inventoryItems(first: 10) { edges { node { id sku tracked } } } }"
        )
        assert result["errors"] is None
        assert len(result["data"]["inventoryItems"]["edges"]) == 1
        assert result["data"]["inventoryItems"]["edges"][0]["node"]["sku"] == "SKU-30"

    async def test_inventory_levels(self, gql, session):
        p = seed_product(session, "40")
        v = seed_variant(session, p.id, "40")
        loc = seed_location(session, "40")
        seed_inventory_level(session, v.inventory_item_id, loc.id, available=75)

        result = await gql.execute(
            "{ inventoryLevels(first: 10) { edges { node { available locationId } } } }"
        )
        assert result["errors"] is None
        lvl = result["data"]["inventoryLevels"]["edges"][0]["node"]
        assert lvl["available"] == 75
        assert lvl["locationId"] == loc.id

    async def test_inventory_levels_filter_by_location(self, gql, session):
        p = seed_product(session, "50")
        v = seed_variant(session, p.id, "50")
        loc1 = seed_location(session, "50")
        loc2 = seed_location(session, "51")
        seed_inventory_level(session, v.inventory_item_id, loc1.id, available=10)
        seed_inventory_level(session, v.inventory_item_id, loc2.id, available=20)

        result = await gql.execute(
            f'{{ inventoryLevels(first: 10, locationIds: ["{loc1.id}"]) {{ edges {{ node {{ available }} }} }} }}'
        )
        assert result["errors"] is None
        assert len(result["data"]["inventoryLevels"]["edges"]) == 1
        assert result["data"]["inventoryLevels"]["edges"][0]["node"]["available"] == 10


@pytest.mark.asyncio
class TestQueryOrders:

    async def test_orders_empty(self, gql):
        result = await gql.execute(
            "{ orders(first: 10) { edges { node { id name } } pageInfo { hasNextPage } } }"
        )
        assert result["errors"] is None
        assert result["data"]["orders"]["edges"] == []

    async def test_order_by_id(self, gql, session):
        seed_order(session, suffix="1")
        result = await gql.execute(
            '{ order(id: "gid://shopify/Order/1") { id name totalPrice displayFinancialStatus } }'
        )
        assert result["errors"] is None
        assert result["data"]["order"]["name"] == "#1001"
        assert result["data"]["order"]["displayFinancialStatus"] == "PAID"

    async def test_orders_filter_by_financial_status(self, gql, session):
        seed_order(session, suffix="1")
        o2 = seed_order(session, suffix="2")
        o2.display_financial_status = "REFUNDED"
        session.add(o2)
        session.commit()

        result = await gql.execute(
            '{ orders(first: 10, query: "financial_status:PAID") { edges { node { id } } } }'
        )
        assert result["errors"] is None
        assert len(result["data"]["orders"]["edges"]) == 1

    async def test_fulfillment_orders_for_order(self, gql, session):
        o = seed_order(session, suffix="10")
        seed_fulfillment_order(session, o.id, "10")
        result = await gql.execute(
            f'{{ fulfillmentOrders(orderId: "{o.id}", first: 10) {{ edges {{ node {{ id status }} }} }} }}'
        )
        assert result["errors"] is None
        fo = result["data"]["fulfillmentOrders"]["edges"][0]["node"]
        assert fo["status"] == "OPEN"

    async def test_fulfillment_order_by_id(self, gql, session):
        o = seed_order(session, suffix="11")
        fo = seed_fulfillment_order(session, o.id, "11")
        result = await gql.execute(
            f'{{ fulfillmentOrder(id: "{fo.id}") {{ id orderId status }} }}'
        )
        assert result["errors"] is None
        assert result["data"]["fulfillmentOrder"]["orderId"] == o.id


@pytest.mark.asyncio
class TestQueryCustomers:

    async def test_customer_by_id(self, gql, session):
        seed_customer(session, "1")
        result = await gql.execute(
            '{ customer(id: "gid://shopify/Customer/1") { id email firstName totalSpent } }'
        )
        assert result["errors"] is None
        c = result["data"]["customer"]
        assert c["email"] == "customer1@example.com"
        assert c["firstName"] == "Alice"

    async def test_customers_query_filter(self, gql, session):
        seed_customer(session, "1")
        seed_customer(session, "2")
        result = await gql.execute(
            '{ customers(first: 10, query: "Alice") { edges { node { id firstName } } } }'
        )
        assert result["errors"] is None
        assert len(result["data"]["customers"]["edges"]) == 2


@pytest.mark.asyncio
class TestQueryDiscounts:

    async def test_discount_nodes_empty(self, gql):
        result = await gql.execute(
            "{ discountNodes(first: 10) { edges { node { id code discountType } } } }"
        )
        assert result["errors"] is None
        assert result["data"]["discountNodes"]["edges"] == []

    async def test_discount_nodes_returns_seeded(self, gql, session):
        seed_discount(session, "1")
        seed_discount(session, "2")
        result = await gql.execute(
            "{ discountNodes(first: 10) { edges { node { id code value status } } } }"
        )
        assert result["errors"] is None
        edges = result["data"]["discountNodes"]["edges"]
        assert len(edges) == 2
        assert edges[0]["node"]["code"] == "SAVE1"


@pytest.mark.asyncio
class TestQueryMetafields:

    async def test_metafields_for_owner(self, gql, session):
        p = seed_product(session, "1")
        seed_metafield(session, p.id, "1")
        result = await gql.execute(
            f'{{ metafields(ownerType: "product", ownerId: "{p.id}", first: 10) '
            f'{{ edges {{ node {{ id namespace key value }} }} }} }}'
        )
        assert result["errors"] is None
        mf = result["data"]["metafields"]["edges"][0]["node"]
        assert mf["namespace"] == "custom"
        assert mf["key"] == "size_guide"
        assert mf["value"] == "See chart"


# ---------------------------------------------------------------------------
# GraphQL mutation tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMutationProductCreate:

    async def test_creates_product(self, gql):
        result = await gql.execute(
            """
            mutation {
              productCreate(input: {
                title: "New Dress"
                status: "ACTIVE"
                vendor: "StyleCo"
                tags: ["new", "dress"]
              }) {
                product { id title vendor tags status }
                userErrors { field message }
              }
            }
            """
        )
        assert result["errors"] is None
        payload = result["data"]["productCreate"]
        assert payload["userErrors"] == []
        p = payload["product"]
        assert p["title"] == "New Dress"
        assert p["vendor"] == "StyleCo"
        assert "dress" in p["tags"]
        assert p["id"].startswith("gid://shopify/Product/")

    async def test_scope_error_in_user_errors(self, db, session):
        gql_ro = ShopWorldGraphQLV2(session=session, granted_scopes={Scope.READ_PRODUCTS})
        result = await gql_ro.execute(
            'mutation { productCreate(input: { title: "X" }) { product { id } userErrors { message } } }'
        )
        assert result["errors"] is None
        assert len(result["data"]["productCreate"]["userErrors"]) > 0


@pytest.mark.asyncio
class TestMutationProductUpdate:

    async def test_updates_title_and_status(self, gql, session):
        seed_product(session, "1")
        result = await gql.execute(
            """
            mutation {
              productUpdate(input: {
                id: "gid://shopify/Product/1"
                title: "Updated Title"
                status: "ARCHIVED"
              }) {
                product { id title status }
                userErrors { field message }
              }
            }
            """
        )
        assert result["errors"] is None
        payload = result["data"]["productUpdate"]
        assert payload["userErrors"] == []
        assert payload["product"]["title"] == "Updated Title"
        assert payload["product"]["status"] == "ARCHIVED"

    async def test_not_found_returns_user_error(self, gql):
        result = await gql.execute(
            'mutation { productUpdate(input: { id: "gid://shopify/Product/nope" title: "X" }) { product { id } userErrors { field message } } }'
        )
        assert result["errors"] is None
        assert len(result["data"]["productUpdate"]["userErrors"]) > 0

    async def test_invalid_status_returns_user_error(self, gql, session):
        seed_product(session, "1")
        result = await gql.execute(
            'mutation { productUpdate(input: { id: "gid://shopify/Product/1" status: "INVALID" }) { product { id } userErrors { message } } }'
        )
        assert result["errors"] is None
        assert "Invalid status" in result["data"]["productUpdate"]["userErrors"][0]["message"]


@pytest.mark.asyncio
class TestMutationProductVariantUpdate:

    async def test_updates_price(self, gql, session):
        p = seed_product(session, "1")
        v = seed_variant(session, p.id, "1")
        result = await gql.execute(
            f"""
            mutation {{
              productVariantUpdate(input: {{
                id: "{v.id}"
                price: "49.99"
                sku: "NEW-SKU"
              }}) {{
                productVariant {{ id price sku }}
                userErrors {{ message }}
              }}
            }}
            """
        )
        assert result["errors"] is None
        payload = result["data"]["productVariantUpdate"]
        assert payload["userErrors"] == []
        assert payload["productVariant"]["price"] == "49.99"
        assert payload["productVariant"]["sku"] == "NEW-SKU"

    async def test_invalid_price_returns_user_error(self, gql, session):
        p = seed_product(session, "1")
        v = seed_variant(session, p.id, "1")
        result = await gql.execute(
            f'mutation {{ productVariantUpdate(input: {{ id: "{v.id}" price: "not-a-number" }}) {{ productVariant {{ id }} userErrors {{ field message }} }} }}'
        )
        assert result["errors"] is None
        assert len(result["data"]["productVariantUpdate"]["userErrors"]) > 0


@pytest.mark.asyncio
class TestMutationInventory:

    async def test_adjust_quantities(self, gql, session):
        p = seed_product(session, "1")
        v = seed_variant(session, p.id, "1")
        loc = seed_location(session, "1")
        seed_inventory_level(session, v.inventory_item_id, loc.id, available=50)

        result = await gql.execute(
            f"""
            mutation {{
              inventoryAdjustQuantities(input: [{{
                inventoryItemId: "{v.inventory_item_id}"
                locationId: "{loc.id}"
                delta: 10
              }}]) {{
                inventoryAdjustmentGroup {{ available locationId }}
                userErrors {{ message }}
              }}
            }}
            """
        )
        assert result["errors"] is None
        payload = result["data"]["inventoryAdjustQuantities"]
        assert payload["userErrors"] == []
        assert payload["inventoryAdjustmentGroup"][0]["available"] == 60

    async def test_negative_adjustment_prevented(self, gql, session):
        p = seed_product(session, "2")
        v = seed_variant(session, p.id, "2")
        loc = seed_location(session, "2")
        seed_inventory_level(session, v.inventory_item_id, loc.id, available=5)

        result = await gql.execute(
            f"""
            mutation {{
              inventoryAdjustQuantities(input: [{{
                inventoryItemId: "{v.inventory_item_id}"
                locationId: "{loc.id}"
                delta: -10
              }}]) {{
                inventoryAdjustmentGroup {{ available }}
                userErrors {{ message }}
              }}
            }}
            """
        )
        assert result["errors"] is None
        assert len(result["data"]["inventoryAdjustQuantities"]["userErrors"]) > 0
        assert "negative" in result["data"]["inventoryAdjustQuantities"]["userErrors"][0]["message"]

    async def test_inventory_item_update(self, gql, session):
        p = seed_product(session, "3")
        v = seed_variant(session, p.id, "3")

        result = await gql.execute(
            f"""
            mutation {{
              inventoryItemUpdate(
                id: "{v.inventory_item_id}"
                input: {{
                  id: "{v.inventory_item_id}"
                  tracked: false
                  harmonizedSystemCode: "6104.43"
                }}
              ) {{
                inventoryItem {{ id tracked harmonizedSystemCode }}
                userErrors {{ message }}
              }}
            }}
            """
        )
        assert result["errors"] is None
        payload = result["data"]["inventoryItemUpdate"]
        assert payload["userErrors"] == []
        assert payload["inventoryItem"]["tracked"] is False
        assert payload["inventoryItem"]["harmonizedSystemCode"] == "6104.43"


@pytest.mark.asyncio
class TestMutationOrders:

    async def test_order_update_tags_and_note(self, gql, session):
        seed_order(session, suffix="1")
        result = await gql.execute(
            """
            mutation {
              orderUpdate(input: {
                id: "gid://shopify/Order/1"
                tags: ["vip", "flagged"]
                note: "Handle with care"
              }) {
                order { id tags note }
                userErrors { message }
              }
            }
            """
        )
        assert result["errors"] is None
        payload = result["data"]["orderUpdate"]
        assert payload["userErrors"] == []
        assert "vip" in payload["order"]["tags"]
        assert payload["order"]["note"] == "Handle with care"

    async def test_order_close(self, gql, session):
        seed_order(session, suffix="2")
        result = await gql.execute(
            'mutation { orderClose(id: "gid://shopify/Order/2") { order { id } userErrors { message } } }'
        )
        assert result["errors"] is None
        assert result["data"]["orderClose"]["userErrors"] == []

    async def test_order_cancel(self, gql, session):
        seed_order(session, suffix="3")
        result = await gql.execute(
            """
            mutation {
              orderCancel(input: {
                id: "gid://shopify/Order/3"
                reason: "CUSTOMER"
                restock: false
              }) {
                order { id displayFinancialStatus }
                userErrors { message }
              }
            }
            """
        )
        assert result["errors"] is None
        payload = result["data"]["orderCancel"]
        assert payload["userErrors"] == []
        assert payload["order"]["displayFinancialStatus"] == "VOIDED"

    async def test_order_cancel_twice_returns_user_error(self, gql, session):
        seed_order(session, suffix="4")
        await gql.execute(
            'mutation { orderCancel(input: { id: "gid://shopify/Order/4" }) { order { id } userErrors { message } } }'
        )
        result = await gql.execute(
            'mutation { orderCancel(input: { id: "gid://shopify/Order/4" }) { order { id } userErrors { message } } }'
        )
        assert result["errors"] is None
        assert len(result["data"]["orderCancel"]["userErrors"]) > 0

    async def test_order_cancel_invalid_reason(self, gql, session):
        seed_order(session, suffix="5")
        result = await gql.execute(
            'mutation { orderCancel(input: { id: "gid://shopify/Order/5" reason: "BADVALUE" }) { order { id } userErrors { message } } }'
        )
        assert result["errors"] is None
        assert len(result["data"]["orderCancel"]["userErrors"]) > 0

    async def test_refund_create(self, gql, session):
        seed_order(session, suffix="6")
        result = await gql.execute(
            """
            mutation {
              refundCreate(input: {
                orderId: "gid://shopify/Order/6"
                amount: "20.00"
                reason: "Customer request"
                notify: true
              }) {
                refundId
                order { id displayFinancialStatus }
                userErrors { message }
              }
            }
            """
        )
        assert result["errors"] is None
        payload = result["data"]["refundCreate"]
        assert payload["userErrors"] == []
        assert payload["refundId"] is not None
        assert payload["order"]["displayFinancialStatus"] == "PARTIALLY_REFUNDED"

    async def test_refund_exceeds_total_returns_user_error(self, gql, session):
        seed_order(session, suffix="7")  # total_price = 79.99
        result = await gql.execute(
            """
            mutation {
              refundCreate(input: {
                orderId: "gid://shopify/Order/7"
                amount: "999.00"
              }) {
                refundId
                userErrors { message }
              }
            }
            """
        )
        assert result["errors"] is None
        assert len(result["data"]["refundCreate"]["userErrors"]) > 0
        assert "exceeds" in result["data"]["refundCreate"]["userErrors"][0]["message"]

    async def test_fulfillment_create(self, gql, session):
        o = seed_order(session, suffix="8")
        loc = seed_location(session, "8")
        result = await gql.execute(
            f"""
            mutation {{
              fulfillmentCreateV2(input: {{
                orderId: "{o.id}"
                locationId: "{loc.id}"
                trackingNumber: "1Z999AA10123456784"
                trackingCompany: "UPS"
              }}) {{
                fulfillment {{ id orderId status trackingNumber trackingCompany }}
                userErrors {{ message }}
              }}
            }}
            """
        )
        assert result["errors"] is None
        payload = result["data"]["fulfillmentCreateV2"]
        assert payload["userErrors"] == []
        f = payload["fulfillment"]
        assert f["status"] == "SUCCESS"
        assert f["trackingNumber"] == "1Z999AA10123456784"
        assert f["trackingCompany"] == "UPS"


@pytest.mark.asyncio
class TestMutationCustomers:

    async def test_customer_create(self, gql):
        result = await gql.execute(
            """
            mutation {
              customerCreate(input: {
                email: "new@example.com"
                firstName: "Bob"
                lastName: "Jones"
                tags: ["wholesale"]
              }) {
                customer { id email firstName tags }
                userErrors { message }
              }
            }
            """
        )
        assert result["errors"] is None
        payload = result["data"]["customerCreate"]
        assert payload["userErrors"] == []
        c = payload["customer"]
        assert c["email"] == "new@example.com"
        assert "wholesale" in c["tags"]

    async def test_customer_create_duplicate_email(self, gql, session):
        seed_customer(session, "1")
        result = await gql.execute(
            """
            mutation {
              customerCreate(input: { email: "customer1@example.com" }) {
                customer { id }
                userErrors { field message }
              }
            }
            """
        )
        assert result["errors"] is None
        assert len(result["data"]["customerCreate"]["userErrors"]) > 0
        assert "already exists" in result["data"]["customerCreate"]["userErrors"][0]["message"]

    async def test_customer_update(self, gql, session):
        seed_customer(session, "1")
        result = await gql.execute(
            """
            mutation {
              customerUpdate(input: {
                id: "gid://shopify/Customer/1"
                firstName: "Updated"
                note: "VIP customer"
              }) {
                customer { id firstName note }
                userErrors { message }
              }
            }
            """
        )
        assert result["errors"] is None
        payload = result["data"]["customerUpdate"]
        assert payload["userErrors"] == []
        assert payload["customer"]["firstName"] == "Updated"
        assert payload["customer"]["note"] == "VIP customer"

    async def test_customer_update_invalid_state(self, gql, session):
        seed_customer(session, "1")
        result = await gql.execute(
            'mutation { customerUpdate(input: { id: "gid://shopify/Customer/1" state: "BADSTATE" }) { customer { id } userErrors { message } } }'
        )
        assert result["errors"] is None
        assert len(result["data"]["customerUpdate"]["userErrors"]) > 0

    async def test_tags_add_to_product(self, gql, session):
        p = seed_product(session, "1")  # has tags: ["summer", "sale"]
        result = await gql.execute(
            f"""
            mutation {{
              tagsAdd(id: "{p.id}", tags: ["clearance", "summer"]) {{
                nodeId
                tags
                userErrors {{ message }}
              }}
            }}
            """
        )
        assert result["errors"] is None
        payload = result["data"]["tagsAdd"]
        assert payload["userErrors"] == []
        assert "clearance" in payload["tags"]
        assert payload["tags"].count("summer") == 1  # not duplicated

    async def test_tags_remove_from_order(self, gql, session):
        o = seed_order(session, suffix="1")
        o.tags = ["vip", "flagged"]
        session.add(o)
        session.commit()

        result = await gql.execute(
            f"""
            mutation {{
              tagsRemove(id: "{o.id}", tags: ["flagged"]) {{
                nodeId tags userErrors {{ message }}
              }}
            }}
            """
        )
        assert result["errors"] is None
        payload = result["data"]["tagsRemove"]
        assert payload["userErrors"] == []
        assert "flagged" not in payload["tags"]
        assert "vip" in payload["tags"]

    async def test_tags_add_unknown_resource_returns_user_error(self, gql):
        result = await gql.execute(
            'mutation { tagsAdd(id: "gid://shopify/Product/nonexistent", tags: ["x"]) { nodeId tags userErrors { message } } }'
        )
        assert result["errors"] is None
        assert len(result["data"]["tagsAdd"]["userErrors"]) > 0


@pytest.mark.asyncio
class TestMutationMetafields:

    async def test_metafields_set_creates_new(self, gql, session):
        p = seed_product(session, "1")
        result = await gql.execute(
            f"""
            mutation {{
              metafieldsSet(metafields: [{{
                ownerType: "product"
                ownerId: "{p.id}"
                namespace: "specs"
                key: "material"
                value: "Cotton 100%"
                type: "single_line_text_field"
              }}]) {{
                metafields {{ id namespace key value }}
                userErrors {{ message }}
              }}
            }}
            """
        )
        assert result["errors"] is None
        payload = result["data"]["metafieldsSet"]
        assert payload["userErrors"] == []
        mf = payload["metafields"][0]
        assert mf["namespace"] == "specs"
        assert mf["key"] == "material"
        assert mf["value"] == "Cotton 100%"

    async def test_metafields_set_upserts_existing(self, gql, session):
        p = seed_product(session, "1")
        seed_metafield(session, p.id, "1")  # namespace=custom, key=size_guide

        result = await gql.execute(
            f"""
            mutation {{
              metafieldsSet(metafields: [{{
                ownerType: "product"
                ownerId: "{p.id}"
                namespace: "custom"
                key: "size_guide"
                value: "Updated chart v2"
                type: "single_line_text_field"
              }}]) {{
                metafields {{ value }}
                userErrors {{ message }}
              }}
            }}
            """
        )
        assert result["errors"] is None
        assert result["data"]["metafieldsSet"]["userErrors"] == []
        assert result["data"]["metafieldsSet"]["metafields"][0]["value"] == "Updated chart v2"

    async def test_metafields_set_too_many_returns_user_error(self, gql):
        inputs = " ".join(
            f'{{ ownerType: "product" ownerId: "gid://shopify/Product/{i}" namespace: "ns" key: "k" value: "v" }}'
            for i in range(26)
        )
        result = await gql.execute(
            f"mutation {{ metafieldsSet(metafields: [{inputs}]) {{ metafields {{ id }} userErrors {{ message }} }} }}"
        )
        assert result["errors"] is None
        assert len(result["data"]["metafieldsSet"]["userErrors"]) > 0
        assert "Maximum" in result["data"]["metafieldsSet"]["userErrors"][0]["message"]


@pytest.mark.asyncio
class TestMutationDiscounts:

    async def test_discount_code_basic_create_percentage(self, gql):
        result = await gql.execute(
            """
            mutation {
              discountCodeBasicCreate(basicCodeDiscount: {
                title: "Summer Sale"
                code: "SUMMER20"
                discountType: "PERCENTAGE"
                value: "20"
                usageLimit: 100
                appliesOncePerCustomer: true
              }) {
                discountNode { id code discountType value status usageLimit appliesOncePerCustomer }
                userErrors { field message }
              }
            }
            """
        )
        assert result["errors"] is None
        payload = result["data"]["discountCodeBasicCreate"]
        assert payload["userErrors"] == []
        d = payload["discountNode"]
        assert d["code"] == "SUMMER20"
        assert d["discountType"] == "PERCENTAGE"
        assert Decimal(d["value"]) == Decimal("20")
        assert d["status"] == "ACTIVE"
        assert d["usageLimit"] == 100
        assert d["appliesOncePerCustomer"] is True

    async def test_discount_code_duplicate_returns_user_error(self, gql, session):
        seed_discount(session, "1")  # code=SAVE1
        result = await gql.execute(
            """
            mutation {
              discountCodeBasicCreate(basicCodeDiscount: {
                title: "Dupe"
                code: "SAVE1"
                discountType: "PERCENTAGE"
                value: "5"
              }) {
                discountNode { id }
                userErrors { field message }
              }
            }
            """
        )
        assert result["errors"] is None
        assert len(result["data"]["discountCodeBasicCreate"]["userErrors"]) > 0
        assert "already exists" in result["data"]["discountCodeBasicCreate"]["userErrors"][0]["message"]

    async def test_discount_code_percentage_over_100_returns_user_error(self, gql):
        result = await gql.execute(
            """
            mutation {
              discountCodeBasicCreate(basicCodeDiscount: {
                title: "Bad"
                code: "OVER100"
                discountType: "PERCENTAGE"
                value: "150"
              }) {
                discountNode { id }
                userErrors { message }
              }
            }
            """
        )
        assert result["errors"] is None
        assert len(result["data"]["discountCodeBasicCreate"]["userErrors"]) > 0

    async def test_discount_code_update(self, gql, session):
        d = seed_discount(session, "1")
        result = await gql.execute(
            f"""
            mutation {{
              discountCodeUpdate(
                id: "{d.id}"
                codeDiscount: {{
                  id: "{d.id}"
                  usageLimit: 50
                  status: "DISABLED"
                }}
              ) {{
                discountNode {{ id status usageLimit }}
                userErrors {{ message }}
              }}
            }}
            """
        )
        assert result["errors"] is None
        payload = result["data"]["discountCodeUpdate"]
        assert payload["userErrors"] == []
        assert payload["discountNode"]["status"] == "DISABLED"
        assert payload["discountNode"]["usageLimit"] == 50
