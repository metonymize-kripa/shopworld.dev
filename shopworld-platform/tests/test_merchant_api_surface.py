from shopworld.api_surface import MerchantAPISurface
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

    assert expected_tools.issubset(set(surface.tool_names))


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
