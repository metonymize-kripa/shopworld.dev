"""Address-change scenario - customer asks to update their shipping address.

State-dependent correct behavior (README §8):
  Depends on label creation, fulfillment status, and carrier intercept availability.

Guard rule:
  - UNFULFILLED → address update is safe and should succeed.
  - Label created but not yet shipped → may require carrier intercept (escalate).
  - Already shipped → intercept may not be possible; must explain and escalate.
"""

from datetime import datetime, timedelta, timezone

from shopworld.task import Task
from shopworld.generate.stores import create_sample_store


def create_address_change_task(
    fulfillment_state: str = "UNFULFILLED",
    label_created: bool = False,
    seed: int = 42,
) -> Task:
    """Create an address-change scenario.

    Args:
        fulfillment_state: "UNFULFILLED", "PARTIAL", or "FULFILLED".
        label_created: Whether a shipping label has already been printed.
        seed: RNG seed.
    """
    store_data = create_sample_store(seed=seed)

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
        "id": "ticket-addr-001",
        "customer_id": customer_id,
        "order_id": order_id,
        "subject": "Change my shipping address",
        "description": "I moved. Please update my address to 123 New St, Springfield, 62701.",
        "category": "ADDRESS_CHANGE",
        "priority": "HIGH",
        "status": "OPEN",
        "customer_sentiment": -0.1,
        "created_at": datetime.now(timezone.utc) - timedelta(hours=3),
        "sla_deadline": datetime.now(timezone.utc) + timedelta(hours=21),
    }
    store_data["support_tickets"].append(ticket)

    # Determine what the correct outcome is
    safe_to_update = fulfillment_state == "UNFULFILLED" and not label_created
    needs_intercept = label_created and fulfillment_state != "FULFILLED"
    cannot_change = fulfillment_state == "FULFILLED"

    if safe_to_update:
        expected_outcome = "address_updated"
        difficulty = 1
    elif needs_intercept:
        expected_outcome = "escalated_for_intercept"
        difficulty = 2
    else:
        expected_outcome = "escalated_not_possible"
        difficulty = 2

    hidden_state = {
        "customer_profiles": {
            customer_id: {
                "type": "cooperative",
                "patience": 0.7,
                "escalation_risk": 0.2,
                "satisfaction": 0.0,
            }
        } if customer_id else {},
        "label_created": label_created,
        "expected_outcome": expected_outcome,
        "address_change_valid": safe_to_update,
    }

    success_conditions = [
        {
            "type": "exists",
            "table": "support_messages",
            "filters": {"ticket_id": "ticket-addr-001"},
            "description": "Agent responded to the address change request",
        },
    ]

    state_label = f"{fulfillment_state.lower()}_{'label' if label_created else 'nolabel'}"

    return Task(
        id=f"address-change-{state_label}-{seed}",
        name=f"Address change - {fulfillment_state}, label={label_created}",
        description=(
            f"Customer wants to update their shipping address for order {order_id}. "
            f"Fulfillment state: {fulfillment_state}, label created: {label_created}. "
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
        max_steps=15,
        tags=["support", "address_change", fulfillment_state.lower(), "state_dependent"],
    )
