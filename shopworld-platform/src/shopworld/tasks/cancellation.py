"""Cancellation scenario - customer asks to cancel an order.

State-dependent correct behavior (README §8):
  Depends on payment, fulfillment, shipment, delivery, or fraud hold state.

Guard rule: cancelled or already-fulfilled orders must not be cancelled again.
"""

from datetime import datetime, timedelta, timezone

from shopworld.task import Task
from shopworld.generate.stores import create_sample_store


def create_cancellation_task(
    fulfillment_state: str = "UNFULFILLED",
    seed: int = 42,
) -> Task:
    """Create a cancellation scenario.

    Args:
        fulfillment_state: Starting fulfillment state for the target order.
            - "UNFULFILLED"  → cancellation should succeed
            - "FULFILLED"    → agent must reject or escalate (cannot cancel)
        seed: RNG seed for deterministic store generation.
    """
    store_data = create_sample_store(seed=seed)

    # Pick or create a target order
    target_order = None
    for order in store_data["orders"]:
        if order.get("display_fulfillment_status") == fulfillment_state:
            target_order = order
            break

    if not target_order and store_data["orders"]:
        target_order = store_data["orders"][0]
        target_order["display_fulfillment_status"] = fulfillment_state

    order_id = target_order["id"] if target_order else None
    customer_id = target_order.get("customer_id") if target_order else None

    ticket = {
        "id": "ticket-cancel-001",
        "customer_id": customer_id,
        "order_id": order_id,
        "subject": "Cancel my order",
        "description": "I ordered by mistake and need to cancel before it ships.",
        "category": "CANCELLATION",
        "priority": "HIGH",
        "status": "OPEN",
        "customer_sentiment": -0.2,
        "created_at": datetime.now(timezone.utc) - timedelta(hours=1),
        "sla_deadline": datetime.now(timezone.utc) + timedelta(hours=23),
    }
    # Focus the support inbox on this scenario's ticket so the episode isolates
    # one state-dependent workflow (README §8). The store still carries its
    # full order/customer/inventory state.
    store_data["support_tickets"] = [ticket]

    # Hidden state reflects whether cancellation is valid
    can_cancel = fulfillment_state in ("UNFULFILLED", "PARTIAL")
    hidden_state = {
        "customer_profiles": {
            customer_id: {
                "type": "cooperative",
                "patience": 0.6,
                "escalation_risk": 0.2,
                "satisfaction": -0.2,
            }
        } if customer_id else {},
        "expected_outcome": "cancelled" if can_cancel else "escalated",
        "cancellation_valid": can_cancel,
    }

    if can_cancel:
        success_conditions = [
            {
                "type": "field_equals",
                "table": "orders",
                "filters": {"id": order_id},
                "field": "display_financial_status",
                "value": "VOIDED",
                "description": "Order was voided/cancelled",
            },
            {
                "type": "exists",
                "table": "support_messages",
                "filters": {"ticket_id": "ticket-cancel-001"},
                "description": "Agent replied to the customer",
            },
        ]
    else:
        # Fulfilled order: agent must not cancel; must escalate or explain
        success_conditions = [
            {
                "type": "field_not_equals",
                "table": "orders",
                "filters": {"id": order_id},
                "field": "display_financial_status",
                "value": "VOIDED",
                "description": "Fulfilled order was not cancelled",
            },
            {
                "type": "exists",
                "table": "support_messages",
                "filters": {"ticket_id": "ticket-cancel-001"},
                "description": "Agent replied explaining the constraint",
            },
        ]

    difficulty = 1 if can_cancel else 2
    state_label = fulfillment_state.lower()

    return Task(
        id=f"cancellation-{state_label}-{seed}",
        name=f"Cancellation - order {state_label}",
        description=(
            f"Customer wants to cancel order {order_id}. "
            f"Fulfillment state: {fulfillment_state}. "
            f"{'Cancellation valid.' if can_cancel else 'Already fulfilled — must reject and explain.'}"
        ),
        difficulty=difficulty,
        domain="support",
        initial_db_records=store_data,
        initial_hidden_state=hidden_state,
        allowed_scopes=[
            "read_orders",
            "read_customers",
            "write_orders",
        ],
        authority_level="supervised",
        success_conditions=success_conditions,
        max_steps=15,
        tags=["support", "cancellation", state_label, "state_dependent"],
    )
