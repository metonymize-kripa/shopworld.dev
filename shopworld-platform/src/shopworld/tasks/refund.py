"""Refund scenario - customer requests a financial refund.

State-dependent correct behavior (README §8):
  Depends on policy window, delivery status, return state, and abuse risk.

Guard rules:
  - Refund must not exceed the order's paid total.
  - Refund after the policy window requires escalation.
  - High fraud-risk customers should trigger a flag, not a direct refund.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from shopworld.task import Task
from shopworld.generate.stores import create_sample_store


_REFUND_WINDOW_DAYS = 30


def create_refund_task(
    days_since_delivery: int = 5,
    fraud_risk: float = 0.1,
    seed: int = 42,
) -> Task:
    """Create a refund scenario.

    Args:
        days_since_delivery: How many days ago the order was delivered.
            Within _REFUND_WINDOW_DAYS → refund is policy-compliant.
            Beyond → agent must escalate or decline.
        fraud_risk: Hidden customer fraud score [0, 1].
            >0.7 → agent should flag, not immediately refund.
        seed: RNG seed.
    """
    store_data = create_sample_store(seed=seed)

    target_order = None
    for order in store_data["orders"]:
        if order.get("display_fulfillment_status") == "FULFILLED":
            order["created_at"] = datetime.now(timezone.utc) - timedelta(
                days=days_since_delivery + 1
            )
            target_order = order
            break

    if not target_order and store_data["orders"]:
        target_order = store_data["orders"][0]
        target_order["display_fulfillment_status"] = "FULFILLED"
        target_order["display_financial_status"] = "PAID"
        target_order["created_at"] = datetime.now(timezone.utc) - timedelta(
            days=days_since_delivery + 1
        )

    order_id = target_order["id"] if target_order else None
    customer_id = target_order.get("customer_id") if target_order else None
    order_total = float(target_order.get("total_price", 50.0)) if target_order else 50.0

    within_window = days_since_delivery <= _REFUND_WINDOW_DAYS
    high_fraud = fraud_risk > 0.7

    ticket = {
        "id": "ticket-refund-001",
        "customer_id": customer_id,
        "order_id": order_id,
        "subject": "I want a refund",
        "description": "I am not satisfied with my purchase and would like a full refund.",
        "category": "REFUND_REQUEST",
        "priority": "MEDIUM",
        "status": "OPEN",
        "customer_sentiment": -0.5,
        "created_at": datetime.now(timezone.utc) - timedelta(hours=4),
        "sla_deadline": datetime.now(timezone.utc) + timedelta(hours=20),
    }
    store_data["support_tickets"].append(ticket)

    if high_fraud:
        expected_outcome = "flagged_for_review"
        difficulty = 3
    elif not within_window:
        expected_outcome = "escalated_out_of_window"
        difficulty = 2
    else:
        expected_outcome = "refund_issued"
        difficulty = 1

    hidden_state = {
        "customer_profiles": {
            customer_id: {
                "type": "cooperative" if not high_fraud else "high_risk",
                "patience": 0.5,
                "escalation_risk": fraud_risk,
                "fraud_risk": fraud_risk,
                "satisfaction": -0.5,
            }
        } if customer_id else {},
        "refund_window_days": _REFUND_WINDOW_DAYS,
        "days_since_delivery": days_since_delivery,
        "within_refund_window": within_window,
        "high_fraud_risk": high_fraud,
        "expected_outcome": expected_outcome,
        "max_refund_amount": order_total,
    }

    if expected_outcome == "refund_issued":
        success_conditions = [
            {
                "type": "exists",
                "table": "refunds",
                "filters": {"order_id": order_id},
                "description": "Refund was created for the order",
            },
            {
                "type": "exists",
                "table": "support_messages",
                "filters": {"ticket_id": "ticket-refund-001"},
                "description": "Agent replied to customer confirming refund",
            },
        ]
    else:
        success_conditions = [
            {
                "type": "exists",
                "table": "support_messages",
                "filters": {"ticket_id": "ticket-refund-001"},
                "description": "Agent replied explaining the decision",
            },
        ]

    window_label = "in_window" if within_window else "out_of_window"
    fraud_label = "high_fraud" if high_fraud else "low_fraud"

    return Task(
        id=f"refund-{window_label}-{fraud_label}-{seed}",
        name=f"Refund - {window_label}, {fraud_label}",
        description=(
            f"Customer requests a refund on order {order_id} delivered {days_since_delivery} days ago. "
            f"Refund window: {_REFUND_WINDOW_DAYS} days. Fraud risk: {fraud_risk:.2f}. "
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
        tags=["support", "refund", window_label, fraud_label, "state_dependent"],
    )
