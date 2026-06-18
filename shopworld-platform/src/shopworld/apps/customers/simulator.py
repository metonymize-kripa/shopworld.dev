"""Customer behavior simulator - generates support tickets and demand."""

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, UTC
from enum import Enum


class CustomerType(Enum):
    """Types of customers with different behaviors."""
    COOPERATIVE = "cooperative"
    CONFUSED = "confused"
    ANGRY = "angry"
    VIP = "vip"
    OPPORTUNISTIC = "opportunistic"
    ADVERSARIAL = "adversarial"


class TicketCategory(Enum):
    """Support ticket categories."""
    WISMO = "where_is_my_order"
    WRONG_ITEM = "wrong_item"
    DAMAGED = "damaged_product"
    DEFECTIVE = "defective_product"
    REFUND_REQUEST = "refund_request"
    RETURN_REQUEST = "return_request"
    PRICE_ADJUSTMENT = "price_adjustment"
    CANCELLATION = "cancellation_request"
    PRODUCT_QUESTION = "product_question"
    ACCOUNT_ISSUE = "account_issue"


@dataclass
class CustomerProfile:
    """Latent customer state driving behavior."""
    customer_id: str
    customer_type: CustomerType
    lifetime_value: float
    order_count: int
    satisfaction: float = 0.0  # -1 to 1
    patience: float = 0.5  # 0 to 1
    escalation_risk: float = 0.0  # 0 to 1
    refund_abuse_score: float = 0.0  # 0 to 1
    chargeback_probability: float = 0.0  # 0 to 1
    review_probability: float = 0.0  # 0 to 1
    price_sensitivity: float = 0.5  # 0 to 1


@dataclass
class SupportTicketEvent:
    """Generated support ticket event."""
    ticket_id: str
    customer_id: str
    order_id: Optional[str]
    category: TicketCategory
    subject: str
    description: str
    priority: str
    customer_sentiment: float
    sla_hours: int


class CustomerSimulator:
    """Simulates customer behavior and generates support events."""
    
    # Complaint templates by category
    COMPLAINT_TEMPLATES = {
        TicketCategory.WISMO: [
            "I ordered {days_ago} days ago and haven't received my package yet. Where is it?",
            "Tracking hasn't updated in days. What's going on with my order?",
            "My package was supposed to arrive yesterday. I need it urgently!",
        ],
        TicketCategory.WRONG_ITEM: [
            "You sent me the wrong item. I ordered {expected} but received {received}.",
            "This is not what I ordered. Please fix this immediately.",
            "Wrong product delivered. Need replacement ASAP.",
        ],
        TicketCategory.DAMAGED: [
            "My package arrived completely damaged. The box was crushed.",
            "Item arrived broken. Packaging was insufficient.",
            "Product damaged during shipping. Need replacement.",
        ],
        TicketCategory.DEFECTIVE: [
            "This product doesn't work as described. It's defective.",
            "Quality is terrible. Broke after one use.",
            "Manufacturing defect visible. Expected better quality.",
        ],
        TicketCategory.REFUND_REQUEST: [
            "I want a refund. This product is not what I expected.",
            "Please refund my order. Changed my mind.",
            "Not satisfied. Need full refund immediately.",
        ],
        TicketCategory.RETURN_REQUEST: [
            "How do I return this item? It doesn't fit.",
            "Need to return - wrong size. What's the process?",
            "Would like to exchange for different size if possible.",
        ],
        TicketCategory.PRICE_ADJUSTMENT: [
            "I bought this yesterday and now it's on sale. Can I get the difference?",
            "Price dropped right after I ordered. Not fair!",
            "Saw this cheaper elsewhere. Will you price match?",
        ],
    }
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.profiles: Dict[str, CustomerProfile] = {}
        self.active_tickets: Dict[str, SupportTicketEvent] = {}
        self.ticket_counter = 0
    
    def register_customer(
        self,
        customer_id: str,
        customer_type: CustomerType = CustomerType.COOPERATIVE,
        lifetime_value: float = 0.0,
        order_count: int = 0,
    ) -> CustomerProfile:
        """Register a customer with behavioral profile."""
        # Generate latent traits based on type
        if customer_type == CustomerType.COOPERATIVE:
            patience = self.rng.uniform(0.6, 0.9)
            escalation_risk = self.rng.uniform(0.0, 0.2)
            refund_abuse = self.rng.uniform(0.0, 0.1)
        elif customer_type == CustomerType.ANGRY:
            patience = self.rng.uniform(0.1, 0.3)
            escalation_risk = self.rng.uniform(0.5, 0.9)
            refund_abuse = self.rng.uniform(0.2, 0.4)
        elif customer_type == CustomerType.VIP:
            patience = self.rng.uniform(0.4, 0.7)
            escalation_risk = self.rng.uniform(0.3, 0.6)  # VIPs escalate if ignored
            lifetime_value = max(lifetime_value, 1000.0)
        elif customer_type == CustomerType.OPPORTUNISTIC:
            patience = self.rng.uniform(0.3, 0.6)
            refund_abuse = self.rng.uniform(0.4, 0.8)
            escalation_risk = self.rng.uniform(0.2, 0.5)
        elif customer_type == CustomerType.ADVERSARIAL:
            patience = self.rng.uniform(0.1, 0.4)
            escalation_risk = self.rng.uniform(0.6, 1.0)
            refund_abuse = self.rng.uniform(0.5, 0.9)
        else:  # CONFUSED
            patience = self.rng.uniform(0.4, 0.7)
            escalation_risk = self.rng.uniform(0.1, 0.3)
            refund_abuse = self.rng.uniform(0.0, 0.2)
        
        profile = CustomerProfile(
            customer_id=customer_id,
            customer_type=customer_type,
            lifetime_value=lifetime_value,
            order_count=order_count,
            satisfaction=self.rng.uniform(-0.2, 0.3),
            patience=patience,
            escalation_risk=escalation_risk,
            refund_abuse_score=refund_abuse,
            chargeback_probability=self.rng.uniform(0.0, 0.1),
            review_probability=self.rng.uniform(0.1, 0.4),
            price_sensitivity=self.rng.uniform(0.3, 0.7),
        )
        
        self.profiles[customer_id] = profile
        return profile
    
    def step(
        self,
        current_time: datetime,
        world_state: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate customer events for this time step."""
        events = []
        
        # Get trigger conditions from world state
        orders = world_state.get("orders", [])
        inventory = world_state.get("inventory", [])
        
        # Generate tickets based on fulfillment issues
        for order in orders:
            if self._should_generate_wismo(order, current_time):
                event = self._create_wismo_ticket(order, current_time)
                if event:
                    events.append({
                        "type": "support_ticket",
                        "ticket": event,
                    })
        
        # Generate tickets based on inventory/stockout issues
        for inv_item in inventory:
            if inv_item.get("backorder_triggered"):
                # Find affected orders
                for order in orders:
                    if self._order_affected_by_stockout(order, inv_item):
                        event = self._create_stockout_ticket(order, inv_item, current_time)
                        if event:
                            events.append({
                                "type": "support_ticket",
                                "ticket": event,
                            })
        
        # Generate random complaints (product quality, etc.)
        if self.rng.random() < 0.05:  # 5% chance per step
            event = self._create_random_quality_ticket(current_time, orders)
            if event:
                events.append({
                    "type": "support_ticket",
                    "ticket": event,
                })
        
        return events
    
    def process_agent_response(
        self,
        ticket_id: str,
        response_text: str,
        resolution_action: Optional[str],
        response_time_hours: float,
    ) -> Dict[str, Any]:
        """Process agent response and update customer state."""
        if ticket_id not in self.active_tickets:
            return {"error": "Ticket not found"}
        
        ticket = self.active_tickets[ticket_id]
        profile = self.profiles.get(ticket.customer_id)
        
        if not profile:
            return {"error": "Customer profile not found"}
        
        # Calculate satisfaction change
        satisfaction_delta = 0.0
        
        # Response time impact
        if response_time_hours < 1:
            satisfaction_delta += 0.3
        elif response_time_hours < 4:
            satisfaction_delta += 0.1
        elif response_time_hours < 24:
            satisfaction_delta += 0.0
        else:
            satisfaction_delta -= 0.2
        
        # Resolution impact
        if resolution_action:
            if "refund" in resolution_action.lower():
                satisfaction_delta += 0.4
            elif "replacement" in resolution_action.lower():
                satisfaction_delta += 0.3
            elif "tracking" in resolution_action.lower():
                satisfaction_delta += 0.2
        
        # Tone analysis (simplified)
        if any(word in response_text.lower() for word in ["sorry", "apologize"]):
            satisfaction_delta += 0.1
        
        # Update profile
        profile.satisfaction = max(-1.0, min(1.0, profile.satisfaction + satisfaction_delta))
        
        # Determine escalation
        escalated = False
        if profile.satisfaction < -0.5 and profile.escalation_risk > 0.5:
            escalated = True
        
        # Determine chargeback risk
        chargeback_prob = profile.chargeback_probability
        if profile.satisfaction < -0.7 and ticket.category in [
            TicketCategory.WISMO, TicketCategory.WRONG_ITEM, TicketCategory.DAMAGED
        ]:
            chargeback_prob = min(1.0, chargeback_prob + 0.3)
        
        # Review probability
        review_prob = profile.review_probability
        if abs(profile.satisfaction) > 0.5:
            review_prob = min(1.0, review_prob + 0.2)
        
        return {
            "satisfaction_delta": satisfaction_delta,
            "new_satisfaction": profile.satisfaction,
            "escalated": escalated,
            "chargeback_probability": chargeback_prob,
            "review_probability": review_prob,
            "ticket_resolved": resolution_action is not None,
        }
    
    def _should_generate_wismo(self, order: Dict[str, Any], current_time: datetime) -> bool:
        """Check if WISMO ticket should be generated."""
        # Check if order is late
        created_at = order.get("created_at")
        if not created_at:
            return False
        
        if isinstance(created_at, str):
            from dateutil import parser
            created_at = parser.parse(created_at)
        
        days_since_order = (current_time - created_at).days
        
        # Generate WISMO if:
        # - Order is 5+ days old and not fulfilled
        # - 30% chance per day after day 5
        if days_since_order >= 5 and order.get("display_fulfillment_status") != "FULFILLED":
            return self.rng.random() < 0.3
        
        return False
    
    def _create_wismo_ticket(
        self,
        order: Dict[str, Any],
        current_time: datetime,
    ) -> Optional[SupportTicketEvent]:
        """Create WISMO (Where Is My Order) ticket."""
        customer_id = order.get("customer_id", "unknown")
        profile = self.profiles.get(customer_id)
        
        if not profile:
            return None
        
        self.ticket_counter += 1
        template = self.rng.choice(self.COMPLAINT_TEMPLATES[TicketCategory.WISMO])
        
        # Calculate days since order
        created_at = order.get("created_at")
        if isinstance(created_at, str):
            from dateutil import parser
            created_at = parser.parse(created_at)
        days_ago = (current_time - created_at).days if created_at else 5
        
        description = template.format(days_ago=days_ago)
        
        # Priority based on customer type and delay
        if profile.customer_type == CustomerType.VIP:
            priority = "URGENT"
            sla_hours = 2
        elif days_ago > 10:
            priority = "HIGH"
            sla_hours = 4
        else:
            priority = "MEDIUM"
            sla_hours = 24
        
        event = SupportTicketEvent(
            ticket_id=f"ticket-{self.ticket_counter}",
            customer_id=customer_id,
            order_id=order.get("id"),
            category=TicketCategory.WISMO,
            subject="Where is my order?",
            description=description,
            priority=priority,
            customer_sentiment=max(-1.0, profile.satisfaction - 0.2),
            sla_hours=sla_hours,
        )
        
        self.active_tickets[event.ticket_id] = event
        return event
    
    def _order_affected_by_stockout(
        self,
        order: Dict[str, Any],
        inv_item: Dict[str, Any],
    ) -> bool:
        """Check if order contains affected SKU."""
        line_items = order.get("line_items", [])
        return any(
            item.get("sku") == inv_item.get("sku") 
            for item in line_items
        )
    
    def _create_stockout_ticket(
        self,
        order: Dict[str, Any],
        inv_item: Dict[str, Any],
        current_time: datetime,
    ) -> Optional[SupportTicketEvent]:
        """Create ticket for stockout affecting order."""
        customer_id = order.get("customer_id", "unknown")
        profile = self.profiles.get(customer_id)
        
        if not profile:
            return None
        
        self.ticket_counter += 1
        
        event = SupportTicketEvent(
            ticket_id=f"ticket-{self.ticket_counter}",
            customer_id=customer_id,
            order_id=order.get("id"),
            category=TicketCategory.WISMO,
            subject="Item out of stock",
            description=f"Your order contains {inv_item.get('sku')} which is now out of stock. Expected restock: 5-7 days.",
            priority="HIGH" if profile.customer_type == CustomerType.VIP else "MEDIUM",
            customer_sentiment=max(-1.0, profile.satisfaction - 0.3),
            sla_hours=12,
        )
        
        self.active_tickets[event.ticket_id] = event
        return event
    
    def _create_random_quality_ticket(
        self,
        current_time: datetime,
        orders: List[Dict[str, Any]],
    ) -> Optional[SupportTicketEvent]:
        """Create random quality-related ticket."""
        if not orders:
            return None
        
        # Pick random recent order
        order = self.rng.choice(orders)
        customer_id = order.get("customer_id", "unknown")
        profile = self.profiles.get(customer_id)
        
        if not profile:
            return None
        
        self.ticket_counter += 1
        
        # Pick random category
        category = self.rng.choice([
            TicketCategory.DAMAGED,
            TicketCategory.DEFECTIVE,
            TicketCategory.WRONG_ITEM,
        ])
        
        template = self.rng.choice(self.COMPLAINT_TEMPLATES.get(category, ["Issue with my order"]))
        
        event = SupportTicketEvent(
            ticket_id=f"ticket-{self.ticket_counter}",
            customer_id=customer_id,
            order_id=order.get("id"),
            category=category,
            subject=category.value.replace("_", " ").title(),
            description=template.format(expected="expected item", received="received item"),
            priority="MEDIUM",
            customer_sentiment=max(-1.0, profile.satisfaction - 0.3),
            sla_hours=24,
        )
        
        self.active_tickets[event.ticket_id] = event
        return event


class SupportTicketGenerator:
    """High-level interface for generating support scenarios."""
    
    def __init__(self, simulator: CustomerSimulator):
        self.simulator = simulator
    
    def create_wismo_scenario(
        self,
        customer_type: CustomerType = CustomerType.COOPERATIVE,
        days_delayed: int = 7,
    ) -> Dict[str, Any]:
        """Create a WISMO scenario with seeded state."""
        customer_id = f"cust-{random.randint(1000, 9999)}"
        order_id = f"order-{random.randint(1000, 9999)}"
        
        self.simulator.register_customer(
            customer_id=customer_id,
            customer_type=customer_type,
            lifetime_value=random.uniform(100, 500),
            order_count=random.randint(1, 5),
        )
        
        # Calculate order date
        order_date = datetime.now(UTC) - timedelta(days=days_delayed)
        
        return {
            "initial_db_records": {
                "customers": [
                    {
                        "id": customer_id,
                        "email": f"{customer_id}@example.com",
                        "first_name": "Test",
                        "last_name": "Customer",
                    }
                ],
                "orders": [
                    {
                        "id": order_id,
                        "name": f"#{random.randint(1000, 9999)}",
                        "customer_id": customer_id,
                        "display_fulfillment_status": "UNFULFILLED",
                        "created_at": order_date.isoformat(),
                        "total_price": "99.99",
                    }
                ],
            },
            "initial_hidden_state": {
                "customer_profiles": {
                    customer_id: {
                        "type": customer_type.value,
                        "patience": 0.5,
                        "escalation_risk": 0.3,
                    }
                }
            },
            "scheduled_event": {
                "type": "support_ticket",
                "trigger": "immediate",
                "category": "wismo",
            },
        }
