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
        "inventory.query",
        "inventory.adjust",
        "refunds.create",
        "refunds.query",
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
