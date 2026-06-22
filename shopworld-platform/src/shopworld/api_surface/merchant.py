"""Shopify-like Merchant API tools exposed to evaluated agents.

This module is intentionally an API surface, not a simulator backdoor: every
method returns only merchant-visible records and never exposes hidden state,
scenario labels, evaluator assertions, or reward functions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from sqlmodel import select

from shopworld.backend.db import Database
from shopworld.apps.shopify_admin.graphql_api.scopes import Scope
from shopworld.apps.shopify_admin.models import (
    Customer,
    DiscountCode,
    Fulfillment,
    InventoryLevel,
    Order,
    Product,
    Refund,
    Return,
    SupportMessage,
    SupportTicket,
)


@dataclass(frozen=True)
class ToolAuthorization:
    """Documented authorization contract for a Merchant API tool.

    ``required_scopes`` uses OR semantics: an agent needs at least one listed
    scope. Empty sets represent public/merchant-policy lookups.
    """

    operation: str
    required_scopes: frozenset[str]
    access: str
    description: str


MERCHANT_TOOL_AUTHORIZATIONS: Dict[str, ToolAuthorization] = {
    "orders.query": ToolAuthorization(
        "orders", frozenset({Scope.READ_ORDERS, Scope.READ_ALL_ORDERS}), "read", "List orders"
    ),
    "orders.cancel": ToolAuthorization(
        "orderCancel", frozenset({Scope.WRITE_ORDERS}), "write", "Cancel an unfulfilled order"
    ),
    "orders.update": ToolAuthorization(
        "orderUpdate", frozenset({Scope.WRITE_ORDERS}), "write", "Update order notes or tags"
    ),
    "customers.query": ToolAuthorization(
        "customers", frozenset({Scope.READ_CUSTOMERS}), "read", "List customers"
    ),
    "customers.update": ToolAuthorization(
        "customerUpdate", frozenset({Scope.WRITE_CUSTOMERS}), "write", "Update customer fields"
    ),
    "customers.tag": ToolAuthorization(
        "tagsAdd", frozenset({Scope.WRITE_CUSTOMERS}), "write", "Tag a customer"
    ),
    "fulfillments.query": ToolAuthorization(
        "fulfillmentOrders",
        frozenset({Scope.READ_ORDERS, Scope.READ_FULFILLMENTS}),
        "read",
        "List fulfillments",
    ),
    "fulfillments.cancel": ToolAuthorization(
        "fulfillmentCreateV2",
        frozenset({Scope.WRITE_FULFILLMENTS}),
        "write",
        "Cancel a pending fulfillment",
    ),
    "inventory.query": ToolAuthorization(
        "inventoryLevels", frozenset({Scope.READ_INVENTORY}), "read", "List inventory levels"
    ),
    "inventory.adjust": ToolAuthorization(
        "inventoryAdjustQuantities",
        frozenset({Scope.WRITE_INVENTORY}),
        "write",
        "Adjust inventory quantities",
    ),
    "refunds.create": ToolAuthorization(
        "refundCreate", frozenset({Scope.WRITE_ORDERS}), "write", "Create an order refund"
    ),
    "refunds.query": ToolAuthorization(
        "orders", frozenset({Scope.READ_ORDERS, Scope.READ_ALL_ORDERS}), "read", "List refunds"
    ),
    "products.query": ToolAuthorization(
        "products", frozenset({Scope.READ_PRODUCTS}), "read", "List products"
    ),
    "products.update": ToolAuthorization(
        "productUpdate", frozenset({Scope.WRITE_PRODUCTS}), "write", "Update product fields"
    ),
    "discounts.create": ToolAuthorization(
        "discountCodeBasicCreate",
        frozenset({Scope.WRITE_DISCOUNTS, Scope.WRITE_PRICE_RULES}),
        "write",
        "Create a discount code",
    ),
    "discounts.query": ToolAuthorization(
        "discountNodes",
        frozenset({Scope.READ_DISCOUNTS, Scope.READ_PRICE_RULES}),
        "read",
        "List discounts",
    ),
    "tickets.query": ToolAuthorization(
        "orders",
        frozenset({Scope.READ_ORDERS, Scope.READ_ALL_ORDERS}),
        "read",
        "List support tickets visible to support operators",
    ),
    "tickets.reply": ToolAuthorization(
        "orderUpdate",
        frozenset({Scope.WRITE_ORDERS}),
        "write",
        "Reply to a support ticket",
    ),
    "tickets.escalate": ToolAuthorization(
        "orderUpdate",
        frozenset({Scope.WRITE_ORDERS}),
        "write",
        "Escalate a support ticket",
    ),
    "policy.lookup": ToolAuthorization(
        "shop", frozenset(), "read", "Search merchant policy snippets"
    ),
    "policy.explain": ToolAuthorization(
        "shop", frozenset(), "read", "Explain merchant policy snippets"
    ),
    # Shipments (tracking view of fulfillments)
    "shipments.query": ToolAuthorization(
        "shipments",
        frozenset({Scope.READ_ORDERS, Scope.READ_FULFILLMENTS}),
        "read",
        "Query shipment tracking status for fulfillments",
    ),
    # Inventory reservation
    "inventory.reserve": ToolAuthorization(
        "inventoryReserveQuantities",
        frozenset({Scope.WRITE_INVENTORY}),
        "write",
        "Reserve inventory quantity to prevent overselling",
    ),
    # Physical item returns (distinct from financial refunds)
    "returns.create": ToolAuthorization(
        "returnCreate",
        frozenset({Scope.WRITE_ORDERS}),
        "write",
        "Create a return request for an order line item",
    ),
    "returns.query": ToolAuthorization(
        "returns",
        frozenset({Scope.READ_ORDERS, Scope.READ_ALL_ORDERS}),
        "read",
        "List return requests",
    ),
}


@dataclass
class ToolResult:
    """Normalized return value for Merchant API tools."""

    ok: bool
    data: Any = None
    errors: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"ok": self.ok, "data": self.data, "errors": self.errors}


class MerchantAPISurface:
    """Constrained agent-visible tools for merchant operations."""

    def __init__(self, db: Database):
        self.db = db
        self._tools: Dict[str, Callable[..., ToolResult]] = {
            "orders.query": self.orders_query,
            "orders.cancel": self.orders_cancel,
            "orders.update": self.orders_update,
            "customers.query": self.customers_query,
            "customers.update": self.customers_update,
            "customers.tag": self.customers_tag,
            "fulfillments.query": self.fulfillments_query,
            "fulfillments.cancel": self.fulfillments_cancel,
            "inventory.query": self.inventory_query,
            "inventory.adjust": self.inventory_adjust,
            "refunds.create": self.refunds_create,
            "refunds.query": self.refunds_query,
            "products.query": self.products_query,
            "products.update": self.products_update,
            "discounts.create": self.discounts_create,
            "discounts.query": self.discounts_query,
            "tickets.query": self.tickets_query,
            "tickets.reply": self.tickets_reply,
            "tickets.escalate": self.tickets_escalate,
            "policy.lookup": self.policy_lookup,
            "policy.explain": self.policy_lookup,
            "shipments.query": self.shipments_query,
            "inventory.reserve": self.inventory_reserve,
            "returns.create": self.returns_create,
            "returns.query": self.returns_query,
        }

    @property
    def tool_names(self) -> List[str]:
        return sorted(self._tools)

    def call(self, name: str, **kwargs: Any) -> ToolResult:
        tool = self._tools.get(name)
        if not tool:
            return self._error("unknown_tool", f"Unknown Merchant API tool: {name}")
        return tool(**kwargs)

    def orders_query(
        self,
        id: Optional[str] = None,
        customer_id: Optional[str] = None,
        name: Optional[str] = None,
        limit: int = 20,
    ) -> ToolResult:
        with self.db.session() as session:
            stmt = select(Order)
            if id:
                stmt = stmt.where(Order.id == id)
            if customer_id:
                stmt = stmt.where(Order.customer_id == customer_id)
            if name:
                stmt = stmt.where(Order.name == name)
            return ToolResult(True, [self._order(o) for o in session.exec(stmt.limit(limit)).all()])

    def orders_update(
        self, order_id: str, note: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> ToolResult:
        with self.db.session() as session:
            order = session.get(Order, order_id)
            if not order:
                return self._error("not_found", f"Order not found: {order_id}")
            if note is not None:
                order.note = note
            if tags is not None:
                order.tags = tags
            order.updated_at = datetime.now(timezone.utc)
            session.add(order)
            session.commit()
            session.refresh(order)
            return ToolResult(True, self._order(order))

    def orders_cancel(self, order_id: str, reason: str = "customer") -> ToolResult:
        with self.db.session() as session:
            order = session.get(Order, order_id)
            if not order:
                return self._error("not_found", f"Order not found: {order_id}")
            if order.display_fulfillment_status == "FULFILLED":
                return self._error(
                    "policy_violation", "Fulfilled orders cannot be cancelled through this tool"
                )
            order.cancelled_at = datetime.now(timezone.utc)
            order.cancel_reason = reason
            order.display_financial_status = "VOIDED"
            order.updated_at = datetime.now(timezone.utc)
            session.add(order)
            session.commit()
            session.refresh(order)
            return ToolResult(True, self._order(order))

    def customers_query(
        self, id: Optional[str] = None, email: Optional[str] = None, limit: int = 20
    ) -> ToolResult:
        with self.db.session() as session:
            stmt = select(Customer)
            if id:
                stmt = stmt.where(Customer.id == id)
            if email:
                stmt = stmt.where(Customer.email == email)
            return ToolResult(
                True, [self._customer(c) for c in session.exec(stmt.limit(limit)).all()]
            )

    def customers_update(
        self, customer_id: str, note: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> ToolResult:
        with self.db.session() as session:
            customer = session.get(Customer, customer_id)
            if not customer:
                return self._error("not_found", f"Customer not found: {customer_id}")
            if note is not None:
                customer.note = note
            if tags is not None:
                customer.tags = tags
            customer.updated_at = datetime.now(timezone.utc)
            session.add(customer)
            session.commit()
            session.refresh(customer)
            return ToolResult(True, self._customer(customer))

    def customers_tag(self, customer_id: str, tags: List[str]) -> ToolResult:
        with self.db.session() as session:
            customer = session.get(Customer, customer_id)
            if not customer:
                return self._error("not_found", f"Customer not found: {customer_id}")
            customer.tags = sorted(set(customer.tags or []).union(tags))
            session.add(customer)
            session.commit()
            session.refresh(customer)
            return ToolResult(True, self._customer(customer))

    def fulfillments_query(self, order_id: Optional[str] = None, limit: int = 20) -> ToolResult:
        with self.db.session() as session:
            stmt = select(Fulfillment)
            if order_id:
                stmt = stmt.where(Fulfillment.order_id == order_id)
            return ToolResult(
                True, [self._fulfillment(f) for f in session.exec(stmt.limit(limit)).all()]
            )

    def fulfillments_cancel(self, fulfillment_id: str) -> ToolResult:
        with self.db.session() as session:
            fulfillment = session.get(Fulfillment, fulfillment_id)
            if not fulfillment:
                return self._error("not_found", f"Fulfillment not found: {fulfillment_id}")
            if fulfillment.status == "SUCCESS":
                return self._error(
                    "policy_violation", "Delivered/successful fulfillments cannot be cancelled"
                )
            fulfillment.status = "CANCELLED"
            fulfillment.updated_at = datetime.now(timezone.utc)
            session.add(fulfillment)
            session.commit()
            session.refresh(fulfillment)
            return ToolResult(True, self._fulfillment(fulfillment))

    def inventory_query(
        self,
        inventory_item_id: Optional[str] = None,
        location_id: Optional[str] = None,
        limit: int = 50,
    ) -> ToolResult:
        with self.db.session() as session:
            stmt = select(InventoryLevel)
            if inventory_item_id:
                stmt = stmt.where(InventoryLevel.inventory_item_id == inventory_item_id)
            if location_id:
                stmt = stmt.where(InventoryLevel.location_id == location_id)
            return ToolResult(
                True, [self._inventory_level(i) for i in session.exec(stmt.limit(limit)).all()]
            )

    def inventory_adjust(self, inventory_item_id: str, location_id: str, delta: int) -> ToolResult:
        with self.db.session() as session:
            level = session.exec(
                select(InventoryLevel).where(
                    InventoryLevel.inventory_item_id == inventory_item_id,
                    InventoryLevel.location_id == location_id,
                )
            ).first()
            if not level:
                return self._error("not_found", "Inventory level not found")
            level.available = max(0, level.available + int(delta))
            level.updated_at = datetime.now(timezone.utc)
            session.add(level)
            session.commit()
            session.refresh(level)
            return ToolResult(True, self._inventory_level(level))

    def refunds_create(
        self,
        order_id: str,
        amount: str | float,
        reason: str = "requested_by_customer",
        note: Optional[str] = None,
        restock: bool = False,
    ) -> ToolResult:
        with self.db.session() as session:
            order = session.get(Order, order_id)
            if not order:
                return self._error("not_found", f"Order not found: {order_id}")
            refund = Refund(
                id=f"gid://shopify/Refund/{uuid.uuid4().hex[:10]}",
                order_id=order_id,
                total_refunded=Decimal(str(amount)),
                reason=reason,
                note=note,
                restock=restock,
            )
            order.display_financial_status = (
                "REFUNDED" if Decimal(str(amount)) >= order.total_price else "PARTIALLY_REFUNDED"
            )
            session.add(refund)
            session.add(order)
            session.commit()
            session.refresh(refund)
            return ToolResult(True, self._refund(refund))

    def refunds_query(self, order_id: Optional[str] = None, limit: int = 20) -> ToolResult:
        with self.db.session() as session:
            stmt = select(Refund)
            if order_id:
                stmt = stmt.where(Refund.order_id == order_id)
            return ToolResult(
                True, [self._refund(r) for r in session.exec(stmt.limit(limit)).all()]
            )

    def products_query(
        self, query: Optional[str] = None, id: Optional[str] = None, limit: int = 20
    ) -> ToolResult:
        with self.db.session() as session:
            stmt = select(Product)
            if id:
                stmt = stmt.where(Product.id == id)
            if query:
                stmt = stmt.where(Product.title.contains(query))
            return ToolResult(
                True, [self._product(p) for p in session.exec(stmt.limit(limit)).all()]
            )

    def products_update(
        self,
        product_id: str,
        title: Optional[str] = None,
        status: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ToolResult:
        with self.db.session() as session:
            product = session.get(Product, product_id)
            if not product:
                return self._error("not_found", f"Product not found: {product_id}")
            if title is not None:
                product.title = title
            if status is not None:
                product.status = status
            if description is not None:
                product.description = description
            product.updated_at = datetime.now(timezone.utc)
            session.add(product)
            session.commit()
            session.refresh(product)
            return ToolResult(True, self._product(product))

    def discounts_create(
        self, code: str, discount_type: str, value: str | float, **kwargs: Any
    ) -> ToolResult:
        with self.db.session() as session:
            discount = DiscountCode(
                id=f"gid://shopify/DiscountCode/{uuid.uuid4().hex[:10]}",
                code=code,
                discount_type=discount_type,
                value=Decimal(str(value)),
                **kwargs,
            )
            session.add(discount)
            session.commit()
            session.refresh(discount)
            return ToolResult(True, self._discount(discount))

    def discounts_query(self, code: Optional[str] = None, limit: int = 20) -> ToolResult:
        with self.db.session() as session:
            stmt = select(DiscountCode)
            if code:
                stmt = stmt.where(DiscountCode.code == code)
            return ToolResult(
                True, [self._discount(d) for d in session.exec(stmt.limit(limit)).all()]
            )

    def tickets_query(
        self, status: Optional[str] = None, customer_id: Optional[str] = None, limit: int = 20
    ) -> ToolResult:
        with self.db.session() as session:
            stmt = select(SupportTicket)
            if status:
                stmt = stmt.where(SupportTicket.status == status)
            if customer_id:
                stmt = stmt.where(SupportTicket.customer_id == customer_id)
            return ToolResult(
                True, [self._ticket(t) for t in session.exec(stmt.limit(limit)).all()]
            )

    def tickets_reply(self, ticket_id: str, body: str, internal: bool = False) -> ToolResult:
        with self.db.session() as session:
            ticket = session.get(SupportTicket, ticket_id)
            if not ticket:
                return self._error("not_found", f"Ticket not found: {ticket_id}")
            message = SupportMessage(
                id=f"msg-{uuid.uuid4().hex[:8]}",
                ticket_id=ticket_id,
                sender_type="AGENT",
                body=body,
                is_internal=internal,
            )
            if not internal and ticket.first_response_at is None:
                ticket.first_response_at = datetime.now(timezone.utc)
            ticket.updated_at = datetime.now(timezone.utc)
            session.add(message)
            session.add(ticket)
            session.commit()
            session.refresh(message)
            return ToolResult(
                True, {"message": self._message(message), "ticket": self._ticket(ticket)}
            )

    def tickets_escalate(self, ticket_id: str, reason: str) -> ToolResult:
        with self.db.session() as session:
            ticket = session.get(SupportTicket, ticket_id)
            if not ticket:
                return self._error("not_found", f"Ticket not found: {ticket_id}")
            ticket.priority = "URGENT"
            ticket.status = "PENDING"
            ticket.updated_at = datetime.now(timezone.utc)
            message = SupportMessage(
                id=f"msg-{uuid.uuid4().hex[:8]}",
                ticket_id=ticket_id,
                sender_type="SYSTEM",
                body=f"Escalated: {reason}",
                is_internal=True,
            )
            session.add(ticket)
            session.add(message)
            session.commit()
            session.refresh(ticket)
            return ToolResult(True, self._ticket(ticket))

    def policy_lookup(self, query: str, limit: int = 5) -> ToolResult:
        policies = [
            {
                "policy_type": "cancellation",
                "title": "Cancellation window",
                "body": "Orders can be cancelled before fulfillment succeeds.",
            },
            {
                "policy_type": "refund",
                "title": "Refund policy",
                "body": "Refunds require an order lookup and must not exceed paid order value.",
            },
            {
                "policy_type": "support",
                "title": "Escalation policy",
                "body": "Escalate fraud, threats, and unresolved carrier exceptions.",
            },
        ]
        needle = query.lower()
        return ToolResult(
            True,
            [
                p
                for p in policies
                if needle in (p["policy_type"] + " " + p["title"] + " " + p["body"]).lower()
            ][:limit],
        )

    def shipments_query(
        self, order_id: Optional[str] = None, tracking_number: Optional[str] = None, limit: int = 20
    ) -> ToolResult:
        """Return tracking-focused view of fulfillments (shipments)."""
        with self.db.session() as session:
            stmt = select(Fulfillment)
            if order_id:
                stmt = stmt.where(Fulfillment.order_id == order_id)
            if tracking_number:
                stmt = stmt.where(Fulfillment.tracking_number == tracking_number)
            return ToolResult(
                True, [self._shipment(f) for f in session.exec(stmt.limit(limit)).all()]
            )

    def inventory_reserve(
        self, inventory_item_id: str, location_id: str, quantity: int
    ) -> ToolResult:
        """Reserve inventory quantity, preventing it from being sold to other orders."""
        if quantity <= 0:
            return self._error("invalid_quantity", "Reserve quantity must be positive")
        with self.db.session() as session:
            level = session.exec(
                select(InventoryLevel).where(
                    InventoryLevel.inventory_item_id == inventory_item_id,
                    InventoryLevel.location_id == location_id,
                )
            ).first()
            if not level:
                return self._error("not_found", "Inventory level not found")
            if level.available < quantity:
                return self._error(
                    "insufficient_inventory",
                    f"Cannot reserve {quantity}: only {level.available} available",
                )
            level.available -= quantity
            level.reserved = (level.reserved or 0) + quantity
            level.updated_at = datetime.now(timezone.utc)
            session.add(level)
            session.commit()
            session.refresh(level)
            return ToolResult(True, self._inventory_level(level))

    def returns_create(
        self,
        order_id: str,
        return_reason: str,
        return_reason_note: Optional[str] = None,
    ) -> ToolResult:
        """Create a return request for an order. Guards final-sale restriction."""
        with self.db.session() as session:
            order = session.get(Order, order_id)
            if not order:
                return self._error("not_found", f"Order not found: {order_id}")
            if order.display_fulfillment_status not in ("FULFILLED", "PARTIAL"):
                return self._error(
                    "policy_violation",
                    "Returns can only be requested for fulfilled orders",
                )
            ret = Return(
                id=f"gid://shopify/Return/{uuid.uuid4().hex[:10]}",
                order_id=order_id,
                customer_id=order.customer_id,
                return_reason=return_reason,
                return_reason_note=return_reason_note,
                status="REQUESTED",
            )
            session.add(ret)
            session.commit()
            session.refresh(ret)
            return ToolResult(True, self._return(ret))

    def returns_query(self, order_id: Optional[str] = None, limit: int = 20) -> ToolResult:
        """List return requests, optionally filtered by order."""
        with self.db.session() as session:
            stmt = select(Return)
            if order_id:
                stmt = stmt.where(Return.order_id == order_id)
            return ToolResult(
                True, [self._return(r) for r in session.exec(stmt.limit(limit)).all()]
            )

    def _error(self, code: str, message: str) -> ToolResult:
        return ToolResult(False, errors=[{"code": code, "message": message}])

    def _order(self, o: Order) -> Dict[str, Any]:
        return {
            "id": o.id,
            "name": o.name,
            "customer_id": o.customer_id,
            "email": o.email,
            "financial_status": o.display_financial_status,
            "fulfillment_status": o.display_fulfillment_status,
            "total_price": str(o.total_price),
            "tags": o.tags or [],
            "note": o.note,
            "cancelled_at": o.cancelled_at.isoformat() if o.cancelled_at else None,
        }

    def _customer(self, c: Customer) -> Dict[str, Any]:
        return {
            "id": c.id,
            "email": c.email,
            "first_name": c.first_name,
            "last_name": c.last_name,
            "tags": c.tags or [],
            "note": c.note,
            "orders_count": c.orders_count,
            "total_spent": str(c.total_spent),
        }

    def _fulfillment(self, f: Fulfillment) -> Dict[str, Any]:
        return {
            "id": f.id,
            "order_id": f.order_id,
            "status": f.status,
            "tracking_number": f.tracking_number,
            "tracking_company": f.tracking_company,
            "delivered_at": f.delivered_at.isoformat() if f.delivered_at else None,
        }

    def _inventory_level(self, i: InventoryLevel) -> Dict[str, Any]:
        return {
            "inventory_item_id": i.inventory_item_id,
            "location_id": i.location_id,
            "available": i.available,
            "incoming": i.incoming,
            "reserved": i.reserved,
        }

    def _refund(self, r: Refund) -> Dict[str, Any]:
        return {
            "id": r.id,
            "order_id": r.order_id,
            "total_refunded": str(r.total_refunded),
            "reason": r.reason,
            "note": r.note,
            "restock": r.restock,
        }

    def _product(self, p: Product) -> Dict[str, Any]:
        return {
            "id": p.id,
            "title": p.title,
            "handle": p.handle,
            "description": p.description,
            "product_type": p.product_type,
            "vendor": p.vendor,
            "status": p.status,
            "tags": p.tags or [],
        }

    def _discount(self, d: DiscountCode) -> Dict[str, Any]:
        return {
            "id": d.id,
            "code": d.code,
            "discount_type": d.discount_type,
            "value": str(d.value),
            "status": d.status,
        }

    def _ticket(self, t: SupportTicket) -> Dict[str, Any]:
        return {
            "id": t.id,
            "customer_id": t.customer_id,
            "order_id": t.order_id,
            "subject": t.subject,
            "description": t.description,
            "category": t.category,
            "priority": t.priority,
            "status": t.status,
        }

    def _message(self, m: SupportMessage) -> Dict[str, Any]:
        return {
            "id": m.id,
            "ticket_id": m.ticket_id,
            "sender_type": m.sender_type,
            "body": m.body,
            "is_internal": m.is_internal,
        }

    def _shipment(self, f: Fulfillment) -> Dict[str, Any]:
        """Tracking-focused view of a Fulfillment record."""
        return {
            "id": f.id,
            "order_id": f.order_id,
            "status": f.status,
            "display_status": f.display_status,
            "tracking_number": f.tracking_number,
            "tracking_url": f.tracking_url,
            "tracking_company": f.tracking_company,
            "created_at": f.created_at.isoformat(),
            "delivered_at": f.delivered_at.isoformat() if f.delivered_at else None,
        }

    def _return(self, r: Return) -> Dict[str, Any]:
        return {
            "id": r.id,
            "order_id": r.order_id,
            "customer_id": r.customer_id,
            "status": r.status,
            "rma_number": r.rma_number,
            "return_reason": r.return_reason,
            "return_reason_note": r.return_reason_note,
            "is_final_sale": r.is_final_sale,
            "refund_id": r.refund_id,
            "created_at": r.created_at.isoformat(),
        }
