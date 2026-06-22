"""Smoke tests for all 5 MVP scenario task families (README §10)."""

import pytest

from shopworld.environment import ShopWorldEnv, Action
from shopworld.tasks import (
    create_wismo_task,
    create_cancellation_task,
    create_address_change_task,
    create_refund_task,
    create_return_task,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_task_and_reply(task, seed: int = 1) -> dict:
    """Reset env, query the open ticket, send one reply, return evaluation."""
    env = ShopWorldEnv(task=task, max_steps=20)
    env.reset(seed=seed)

    tickets = env.api_surface.call("tickets.query", status="OPEN").data
    assert tickets, "No open ticket seeded"
    ticket_id = tickets[0]["id"]

    env.step(Action(
        tool_name="tickets.reply",
        arguments={"ticket_id": ticket_id, "body": "I am looking into this for you."},
    ))
    return env.evaluate()


# ---------------------------------------------------------------------------
# WISMO
# ---------------------------------------------------------------------------

def test_wismo_task_basic_reset_and_reply():
    result = run_task_and_reply(create_wismo_task(seed=1))
    assert "episode_id" in result


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fulfillment_state", ["UNFULFILLED", "FULFILLED"])
def test_cancellation_task_creates_ticket(fulfillment_state):
    task = create_cancellation_task(fulfillment_state=fulfillment_state, seed=2)
    env = ShopWorldEnv(task=task)
    _, info = env.reset(seed=2)
    tickets = env.api_surface.call("tickets.query", status="OPEN").data
    assert any(t["subject"] == "Cancel my order" for t in tickets)


def test_cancellation_unfulfilled_allows_cancel():
    task = create_cancellation_task(fulfillment_state="UNFULFILLED", seed=3)
    env = ShopWorldEnv(task=task)
    env.reset(seed=3)
    orders = env.api_surface.call("orders.query").data
    unfulfilled = [o for o in orders if o["fulfillment_status"] == "UNFULFILLED"]
    if not unfulfilled:
        return
    result = env.api_surface.call("orders.cancel", order_id=unfulfilled[0]["id"])
    assert result.ok
    assert result.data["financial_status"] == "VOIDED"


def test_cancellation_fulfilled_blocks_cancel():
    task = create_cancellation_task(fulfillment_state="FULFILLED", seed=4)
    env = ShopWorldEnv(task=task)
    env.reset(seed=4)
    orders = env.api_surface.call("orders.query").data
    fulfilled = [o for o in orders if o["fulfillment_status"] == "FULFILLED"]
    if not fulfilled:
        return
    result = env.api_surface.call("orders.cancel", order_id=fulfilled[0]["id"])
    assert not result.ok
    assert result.errors[0]["code"] == "policy_violation"


# ---------------------------------------------------------------------------
# Address change
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("state,label", [
    ("UNFULFILLED", False),
    ("UNFULFILLED", True),
    ("FULFILLED", False),
])
def test_address_change_task_seeds_ticket(state, label):
    task = create_address_change_task(fulfillment_state=state, label_created=label, seed=5)
    env = ShopWorldEnv(task=task)
    env.reset(seed=5)
    tickets = env.api_surface.call("tickets.query", status="OPEN").data
    assert any(t["subject"] == "Change my shipping address" for t in tickets)


def test_address_change_correct_outcome_in_hidden_state():
    task = create_address_change_task(fulfillment_state="UNFULFILLED", label_created=False, seed=6)
    env = ShopWorldEnv(task=task)
    env.reset(seed=6)
    assert env.hidden_state["address_change_valid"] is True

    task2 = create_address_change_task(fulfillment_state="FULFILLED", label_created=False, seed=6)
    env2 = ShopWorldEnv(task=task2)
    env2.reset(seed=6)
    assert env2.hidden_state["address_change_valid"] is False


# ---------------------------------------------------------------------------
# Refund
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("days,fraud", [
    (5, 0.1),    # in-window, low fraud → refund
    (45, 0.1),   # out-of-window, low fraud → escalate
    (5, 0.9),    # in-window, high fraud → flag
])
def test_refund_task_seeds_ticket(days, fraud):
    task = create_refund_task(days_since_delivery=days, fraud_risk=fraud, seed=7)
    env = ShopWorldEnv(task=task)
    env.reset(seed=7)
    tickets = env.api_surface.call("tickets.query", status="OPEN").data
    assert any(t["subject"] == "I want a refund" for t in tickets)


def test_refund_within_window_hides_fraud_risk():
    task = create_refund_task(days_since_delivery=5, fraud_risk=0.9, seed=8)
    env = ShopWorldEnv(task=task)
    env.reset(seed=8)
    # Fraud risk must stay in hidden state, not leak to agent-visible ticket
    tickets = env.api_surface.call("tickets.query", status="OPEN").data
    assert tickets
    assert "fraud_risk" not in tickets[0]
    # Hidden state does carry it
    assert env.hidden_state.get("high_fraud_risk") is True


# ---------------------------------------------------------------------------
# Return
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("days,final_sale", [
    (7, False),   # in-window, returnable → return_created
    (45, False),  # out-of-window → rejected
    (7, True),    # final sale → rejected
])
def test_return_task_seeds_ticket(days, final_sale):
    task = create_return_task(days_since_delivery=days, is_final_sale=final_sale, seed=9)
    env = ShopWorldEnv(task=task)
    env.reset(seed=9)
    tickets = env.api_surface.call("tickets.query", status="OPEN").data
    assert any(t["subject"] == "How do I return this?" for t in tickets)


def test_return_in_window_creates_return_via_tool():
    task = create_return_task(days_since_delivery=7, is_final_sale=False, seed=10)
    env = ShopWorldEnv(task=task)
    env.reset(seed=10)
    assert env.hidden_state["return_eligible"] is True

    # Mark an order as FULFILLED so returns.create will accept it
    orders = env.api_surface.call("orders.query").data
    if not orders:
        return

    from shopworld.apps.shopify_admin.models import Order as _Order
    order_id = orders[0]["id"]
    with env.db.session() as s:
        o = s.get(_Order, order_id)
        o.display_fulfillment_status = "FULFILLED"
        s.add(o)
        s.commit()

    result = env.api_surface.call(
        "returns.create", order_id=order_id, return_reason="DOESNT_FIT"
    )
    assert result.ok
    assert result.data["status"] == "REQUESTED"


def test_return_final_sale_hidden_not_agent_visible():
    task = create_return_task(days_since_delivery=7, is_final_sale=True, seed=11)
    env = ShopWorldEnv(task=task)
    env.reset(seed=11)
    # Final-sale flag must stay in hidden state
    tickets = env.api_surface.call("tickets.query", status="OPEN").data
    assert tickets
    assert "is_final_sale" not in tickets[0]
    assert env.hidden_state["is_final_sale"] is True
