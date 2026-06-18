"""WISMO (Where Is My Order) task - customer asking about delayed shipment."""

from datetime import datetime, timedelta, UTC

from shopworld.task import Task
from shopworld.generate.stores import create_sample_store


def create_wismo_task(
    customer_type: str = "cooperative",
    days_delayed: int = 10,
    seed: int = 42,
) -> Task:
    """Create a WISMO scenario task.
    
    The agent must:
    1. Look up the order by customer email or order number
    2. Check fulfillment status
    3. Find tracking information
    4. Provide appropriate response to customer
    5. Potentially escalate if needed
    """
    
    # Generate store data
    store_data = create_sample_store(seed=seed)
    
    # Find or create a delayed order
    delayed_order = None
    for order in store_data["orders"]:
        if order.get("display_fulfillment_status") == "UNFULFILLED":
            # Make it delayed
            order["created_at"] = datetime.now(UTC) - timedelta(days=days_delayed)
            delayed_order = order
            break
    
    # If no unfulfilled order found, modify one
    if not delayed_order and store_data["orders"]:
        delayed_order = store_data["orders"][0]
        delayed_order["display_fulfillment_status"] = "UNFULFILLED"
        delayed_order["created_at"] = datetime.now(UTC) - timedelta(days=days_delayed)
    
    # Add support ticket for this order
    customer_id = delayed_order.get("customer_id") if delayed_order else None

    ticket = {
        "id": "ticket-wismo-001",
        "customer_id": customer_id,
        "order_id": delayed_order.get("id") if delayed_order else None,
        "subject": "Where is my order?",
        "description": f"I ordered {days_delayed} days ago and still haven't received my package. Can you check on it?",
        "category": "WISMO",
        "priority": "HIGH" if customer_type == "vip" else "MEDIUM",
        "status": "OPEN",
        "customer_sentiment": -0.4,
        "created_at": datetime.now(UTC) - timedelta(hours=2),
        "sla_deadline": datetime.now(UTC) + timedelta(hours=22),
    }
    store_data["support_tickets"].append(ticket)
    
    # Hidden state for customer behavior
    hidden_state = {
        "customer_profiles": {
            customer_id: {
                "type": customer_type,
                "patience": 0.5 if customer_type == "cooperative" else 0.3,
                "escalation_risk": 0.6 if customer_type == "angry" else 0.3,
                "satisfaction": -0.4,
            }
        } if customer_id else {},
        "expected_tracking_number": "1Z999888777666",
        "expected_carrier": "UPS",
    }
    
    # Success conditions
    success_conditions = [
        {
            "type": "exists",
            "table": "support_messages",
            "filters": {"ticket_id": "ticket-wismo-001"},
            "description": "Agent responded to customer ticket",
        },
        {
            "type": "exists",
            "table": "orders",
            "filters": {
                "id": delayed_order.get("id") if delayed_order else None,
            },
            "description": "Order was looked up",
        },
    ]
    
    return Task(
        id=f"wismo-{customer_type}-{days_delayed}",
        name=f"WISMO - {customer_type.title()} customer, {days_delayed} days delayed",
        description=f"A {customer_type} customer is asking about their order placed {days_delayed} days ago. Find the order, check status, and provide appropriate response.",
        difficulty=1,
        domain="support",
        initial_db_records=store_data,
        initial_hidden_state=hidden_state,
        allowed_scopes=[
            "read_orders",
            "read_customers",
            "read_fulfillments",
            "write_orders",  # For adding notes
        ],
        authority_level="supervised",
        success_conditions=success_conditions,
        max_steps=20,
        tags=["support", "wismo", customer_type, "single_query"],
    )
