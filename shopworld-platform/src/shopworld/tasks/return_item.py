"""Return-item scenario - customer asks how to return a product.

State-dependent correct behavior (README §8):
  Depends on SKU, condition, return window, and final-sale status.

Guard rules:
  - Final-sale items cannot be returned.
  - Return window must still be open (default: 30 days from delivery).
  - Non-returnable categories (e.g., consumables) must be rejected and explained.
"""

from datetime import datetime, timedelta, timezone

from shopworld.task import Task
from shopworld.generate.stores import create_sample_store


_RETURN_WINDOW_DAYS = 30


def create_return_task(
    days_since_delivery: int = 7,
    is_final_sale: bool = False,
    seed: int = 42,
) -> Task:
    """Create a return-item scenario.

    Args:
        days_since_delivery: Days since the order was delivered.
            Within _RETURN_WINDOW_DAYS → return is valid.
            Beyond → agent must decline and explain.
        is_final_sale: Whether the item is final-sale (non-returnable).
        seed: RNG seed.
    """
    store_data = create_sample_store(seed=seed)

    target_order = None
    for order in store_data["orders"]:
        if order.get("display_fulfillment_status") == "FULFILLED":
            target_order = order
            break

    if not target_order and store_data["orders"]:
        target_order = store_data["orders"][0]
        target_order["display_fulfillment_status"] = "FULFILLED"
        target_order["display_financial_status"] = "PAID"

    if target_order:
        target_order["created_at"] = datetime.now(timezone.utc) - timedelta(
            days=days_since_delivery + 1
        )

    order_id = target_order["id"] if target_order else None
    customer_id = target_order.get("customer_id") if target_order else None

    within_window = days_since_delivery <= _RETURN_WINDOW_DAYS
    returnable = within_window and not is_final_sale

    if is_final_sale:
        expected_outcome = "rejected_final_sale"
        difficulty = 2
    elif not within_window:
        expected_outcome = "rejected_out_of_window"
        difficulty = 2
    else:
        expected_outcome = "return_created"
        difficulty = 1

    ticket = {
        "id": "ticket-return-001",
        "customer_id": customer_id,
        "order_id": order_id,
        "subject": "How do I return this?",
        "description": "I want to return the item I received. It doesn't fit.",
        "category": "RETURN_REQUEST",
        "priority": "MEDIUM",
        "status": "OPEN",
        "customer_sentiment": -0.3,
        "created_at": datetime.now(timezone.utc) - timedelta(hours=6),
        "sla_deadline": datetime.now(timezone.utc) + timedelta(hours=18),
    }
    # Focus the support inbox on this scenario's ticket so the episode isolates
    # one state-dependent workflow (README §8). The store still carries its
    # full order/customer/inventory state.
    store_data["support_tickets"] = [ticket]

    hidden_state = {
        "customer_profiles": {
            customer_id: {
                "type": "cooperative",
                "patience": 0.6,
                "escalation_risk": 0.2,
                "satisfaction": -0.3,
            }
        } if customer_id else {},
        "return_window_days": _RETURN_WINDOW_DAYS,
        "days_since_delivery": days_since_delivery,
        "within_return_window": within_window,
        "is_final_sale": is_final_sale,
        "return_eligible": returnable,
        "expected_outcome": expected_outcome,
    }

    if expected_outcome == "return_created":
        success_conditions = [
            {
                "type": "exists",
                "table": "returns",
                "filters": {"order_id": order_id},
                "description": "Return request was created",
            },
            {
                "type": "exists",
                "table": "support_messages",
                "filters": {"ticket_id": "ticket-return-001"},
                "description": "Agent replied with return instructions",
            },
        ]
    else:
        success_conditions = [
            {
                "type": "exists",
                "table": "support_messages",
                "filters": {"ticket_id": "ticket-return-001"},
                "description": "Agent replied explaining why return is not possible",
            },
        ]

    window_label = "in_window" if within_window else "out_of_window"
    sale_label = "final_sale" if is_final_sale else "returnable"

    return Task(
        id=f"return-{window_label}-{sale_label}-{seed}",
        name=f"Return item - {window_label}, {sale_label}",
        description=(
            f"Customer wants to return item from order {order_id} delivered {days_since_delivery} days ago. "
            f"Return window: {_RETURN_WINDOW_DAYS} days. Final sale: {is_final_sale}. "
            f"Expected outcome: {expected_outcome}."
        ),
        difficulty=difficulty,
        domain="support",
        initial_db_records=store_data,
        initial_hidden_state=hidden_state,
        allowed_scopes=[
            "read_orders",
            "read_customers",
            "read_fulfillments",
            "write_orders",
        ],
        authority_level="supervised",
        success_conditions=success_conditions,
        max_steps=20,
        tags=["support", "return", window_label, sale_label, "state_dependent"],
    )
