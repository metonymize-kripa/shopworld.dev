from shopworld.api_surface import MerchantAPISurface
from shopworld.api_surface import MERCHANT_TOOL_AUTHORIZATIONS
from shopworld.apps.shopify_admin.graphql_api.scopes import OPERATION_SCOPES, ScopeError, check_scope
from shopworld.environment import ShopWorldEnv
from shopworld.tasks.wismo import create_wismo_task


def seeded_surface():
    env = ShopWorldEnv(task=create_wismo_task(seed=7))
    env.reset(seed=7)
    return MerchantAPISurface(env.db)


def test_tool_registry_matches_initial_merchant_api_contract():
    surface = seeded_surface()

    expected_tools = {
        "orders.query",
        "orders.cancel",
        "orders.update",
        "customers.query",
        "customers.update",
        "customers.tag",
        "fulfillments.query",
        "fulfillments.cancel",
        "shipments.query",
        "inventory.query",
        "inventory.adjust",
        "inventory.reserve",
        "refunds.create",
        "refunds.query",
        "returns.create",
        "returns.query",
        "products.query",
        "products.update",
        "discounts.create",
        "discounts.query",
        "tickets.query",
        "tickets.reply",
        "tickets.escalate",
        "policy.lookup",
        "policy.explain",
    }

    assert set(surface.tool_names) == expected_tools
    assert set(MERCHANT_TOOL_AUTHORIZATIONS) == expected_tools


def test_each_merchant_tool_authorization_maps_to_graphql_scope_registry():
    for tool_name, authorization in MERCHANT_TOOL_AUTHORIZATIONS.items():
        assert authorization.operation in OPERATION_SCOPES, tool_name
        assert authorization.required_scopes <= OPERATION_SCOPES[authorization.operation], tool_name
        assert authorization.access in {"read", "write"}, tool_name
        assert authorization.description, tool_name


def test_every_scoped_merchant_tool_allows_and_denies_by_documented_scope():
    for tool_name, authorization in MERCHANT_TOOL_AUTHORIZATIONS.items():
        if not authorization.required_scopes:
            check_scope(authorization.operation, set())
            continue

        granted_scope = next(iter(authorization.required_scopes))
        check_scope(authorization.operation, {granted_scope})

        try:
            check_scope(authorization.operation, set())
        except ScopeError:
            pass
        else:
            raise AssertionError(f"{tool_name} should be denied without a documented scope")


def test_environment_dotted_tool_scope_map_is_derived_from_authorization_table():
    for tool_name, authorization in MERCHANT_TOOL_AUTHORIZATIONS.items():
        assert ShopWorldEnv._TOOL_SCOPE_MAP[tool_name] == authorization.operation


def test_environment_enforces_tool_specific_scope_when_graphql_operation_is_broader():
    env = ShopWorldEnv(enable_tracing=True)
    env.reset(options={"scopes": ["write_orders"]})

    _, _, _, _, info = env.step(
        __import__("shopworld.environment", fromlist=["Action"]).Action(
            tool_name="customers.tag",
            arguments={"customer_id": "gid://shopify/Customer/missing", "tags": ["vip"]},
        )
    )

    assert any("SCOPE:" in violation for violation in info["violations"])


def test_ticket_reply_and_order_query_are_agent_visible_without_hidden_state():
    surface = seeded_surface()

    tickets = surface.call("tickets.query", status="OPEN").to_dict()
    assert tickets["ok"]
    ticket = tickets["data"][0]
    assert "expected_tracking_number" not in ticket

    reply = surface.call(
        "tickets.reply",
        ticket_id=ticket["id"],
        body="I checked your order and will keep monitoring the carrier status.",
    ).to_dict()

    assert reply["ok"]
    assert reply["data"]["message"]["sender_type"] == "AGENT"

    orders = surface.call("orders.query", id=ticket["order_id"]).to_dict()
    assert orders["ok"]
    assert orders["data"][0]["id"] == ticket["order_id"]


def test_cannot_cancel_fulfilled_order_through_merchant_tool():
    surface = seeded_surface()
    order = surface.call("orders.query").data[0]

    update = surface.call("orders.update", order_id=order["id"], note="looked up")
    assert update.ok

    # Direct setup for policy case: the Merchant API should reject this state.
    with surface.db.session() as session:
        db_order = session.get(
            __import__("shopworld.apps.shopify_admin.models", fromlist=["Order"]).Order, order["id"]
        )
        db_order.display_fulfillment_status = "FULFILLED"
        session.add(db_order)
        session.commit()

    cancelled = surface.call("orders.cancel", order_id=order["id"])
    assert not cancelled.ok
    assert cancelled.errors[0]["code"] == "policy_violation"


def test_environment_step_executes_dotted_merchant_api_tool():
    env = ShopWorldEnv(task=create_wismo_task(seed=9))
    env.reset(seed=9)
    ticket = env.api_surface.call("tickets.query", status="OPEN").data[0]

    env.step(
        __import__("shopworld.environment", fromlist=["Action"]).Action(
            tool_name="tickets.reply",
            arguments={"ticket_id": ticket["id"], "body": "I am checking this now."},
        )
    )

    messages = env._get_current_state()["support_messages"]
    assert any(message["ticket_id"] == ticket["id"] for message in messages)
    assert env.hidden_state["tool_results"][-1]["tool"] == "tickets.reply"


def test_shipments_query_returns_tracking_fields():
    surface = seeded_surface()
    result = surface.call("shipments.query")
    assert result.ok
    # Shipments view exposes tracking fields; verified on any present record
    for shipment in result.data:
        assert "tracking_number" in shipment
        assert "tracking_company" in shipment
        assert "display_status" in shipment
        assert "order_id" in shipment


def test_inventory_reserve_decrements_available_and_increments_reserved():
    surface = seeded_surface()
    levels = surface.call("inventory.query").data
    if not levels:
        return  # skip if seed has no inventory
    level = levels[0]
    item_id = level["inventory_item_id"]
    loc_id = level["location_id"]
    available_before = level["available"]
    reserved_before = level["reserved"] or 0

    result = surface.call("inventory.reserve", inventory_item_id=item_id, location_id=loc_id, quantity=1)
    assert result.ok
    assert result.data["available"] == available_before - 1
    assert result.data["reserved"] == reserved_before + 1


def test_inventory_reserve_rejects_quantity_exceeding_available():
    surface = seeded_surface()
    levels = surface.call("inventory.query").data
    if not levels:
        return
    level = levels[0]
    item_id = level["inventory_item_id"]
    loc_id = level["location_id"]
    huge = level["available"] + 9999

    result = surface.call("inventory.reserve", inventory_item_id=item_id, location_id=loc_id, quantity=huge)
    assert not result.ok
    assert result.errors[0]["code"] == "insufficient_inventory"


def test_returns_create_and_query():
    surface = seeded_surface()
    # Find a fulfilled order to return
    orders = surface.call("orders.query").data
    fulfilled = [o for o in orders if o["fulfillment_status"] == "FULFILLED"]
    if not fulfilled:
        # Seed has no fulfilled orders; mark one via DB to satisfy the guard
        from shopworld.apps.shopify_admin.models import Order as _Order
        order_id = orders[0]["id"]
        with surface.db.session() as s:
            o = s.get(_Order, order_id)
            o.display_fulfillment_status = "FULFILLED"
            s.add(o)
            s.commit()
    else:
        order_id = fulfilled[0]["id"]

    ret = surface.call("returns.create", order_id=order_id, return_reason="WRONG_ITEM")
    assert ret.ok
    assert ret.data["order_id"] == order_id
    assert ret.data["status"] == "REQUESTED"
    assert ret.data["return_reason"] == "WRONG_ITEM"

    listing = surface.call("returns.query", order_id=order_id)
    assert listing.ok
    assert any(r["id"] == ret.data["id"] for r in listing.data)


def test_returns_create_rejects_unfulfilled_order():
    surface = seeded_surface()
    orders = surface.call("orders.query").data
    unfulfilled = [o for o in orders if o["fulfillment_status"] not in ("FULFILLED", "PARTIAL")]
    if not unfulfilled:
        return  # all orders fulfilled in this seed; skip
    result = surface.call("returns.create", order_id=unfulfilled[0]["id"], return_reason="CUSTOMER_CHANGED_MIND")
    assert not result.ok
    assert result.errors[0]["code"] == "policy_violation"
