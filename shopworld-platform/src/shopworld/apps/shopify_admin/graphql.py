"""Simulated Shopify Admin GraphQL API.

.. deprecated::
    This module is superseded by
    ``shopworld.apps.shopify_admin.graphql_api`` (``build_schema()`` /
    ``ShopWorldGraphQLV2``).  It is kept only for compatibility while the
    migration is finalised.  New code must import from ``graphql_api``
    instead.  This file will be removed in a future release.
"""

import warnings as _warnings
from typing import Any, Dict, List, Optional
from decimal import Decimal

import strawberry
from strawberry.types import Info
from sqlmodel import Session, select

from shopworld.apps.shopify_admin.models import (
    Product, Order, Customer, InventoryLevel,
    SupportTicket,
)

_warnings.warn(
    "shopworld.apps.shopify_admin.graphql is deprecated. "
    "Use shopworld.apps.shopify_admin.graphql_api (build_schema / ShopWorldGraphQLV2) instead.",
    DeprecationWarning,
    stacklevel=2,
)


# GraphQL Types

@strawberry.type
class ProductType:
    id: str
    title: str
    handle: str
    description: Optional[str]
    product_type: Optional[str]
    vendor: Optional[str]
    status: str
    created_at: str
    updated_at: str


@strawberry.type
class ProductVariantType:
    id: str
    product_id: str
    sku: Optional[str]
    barcode: Optional[str]
    price: str  # Decimal as string
    compare_at_price: Optional[str]
    inventory_quantity: int


@strawberry.type
class OrderType:
    id: str
    name: str
    email: Optional[str]
    display_financial_status: str
    display_fulfillment_status: str
    total_price: str
    created_at: str
    updated_at: str


@strawberry.type
class CustomerType:
    id: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    orders_count: int
    total_spent: str
    state: str


@strawberry.type
class InventoryLevelType:
    id: int
    inventory_item_id: str
    location_id: str
    available: int
    incoming: int
    reserved: int


@strawberry.type
class SupportTicketType:
    id: str
    subject: str
    status: str
    priority: str
    category: str
    customer_sentiment: float
    created_at: str


@strawberry.type
class ShopType:
    """Shop information."""
    id: str
    name: str
    myshopify_domain: str
    currency_code: str
    timezone: str


@strawberry.type
class Query:
    """Shopify Admin GraphQL Queries."""
    
    @strawberry.field
    def shop(self) -> ShopType:
        """Get shop information."""
        return ShopType(
            id="gid://shopify/Shop/1",
            name="Test Shop",
            myshopify_domain="test-shop.myshopify.com",
            currency_code="USD",
            timezone="America/New_York",
        )
    
    @strawberry.field
    def product(self, info: Info, id: str) -> Optional[ProductType]:
        """Get product by ID."""
        session: Session = info.context["session"]
        product = session.exec(select(Product).where(Product.id == id)).first()
        if product:
            return ProductType(
                id=product.id,
                title=product.title,
                handle=product.handle,
                description=product.description,
                product_type=product.product_type,
                vendor=product.vendor,
                status=product.status,
                created_at=product.created_at.isoformat(),
                updated_at=product.updated_at.isoformat(),
            )
        return None
    
    @strawberry.field
    def products(
        self,
        info: Info,
        first: int = 10,
        after: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[ProductType]:
        """Get paginated list of products."""
        session: Session = info.context["session"]
        
        statement = select(Product).limit(min(first, 250))  # Shopify limit
        if query:
            statement = statement.where(Product.title.contains(query))
        
        products = session.exec(statement).all()
        return [
            ProductType(
                id=p.id,
                title=p.title,
                handle=p.handle,
                description=p.description,
                product_type=p.product_type,
                vendor=p.vendor,
                status=p.status,
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat(),
            )
            for p in products
        ]
    
    @strawberry.field
    def order(self, info: Info, id: str) -> Optional[OrderType]:
        """Get order by ID."""
        session: Session = info.context["session"]
        order = session.exec(select(Order).where(Order.id == id)).first()
        if order:
            return OrderType(
                id=order.id,
                name=order.name,
                email=order.email,
                display_financial_status=order.display_financial_status,
                display_fulfillment_status=order.display_fulfillment_status,
                total_price=str(order.total_price),
                created_at=order.created_at.isoformat(),
                updated_at=order.updated_at.isoformat(),
            )
        return None
    
    @strawberry.field
    def orders(
        self,
        info: Info,
        first: int = 10,
        after: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[OrderType]:
        """Get paginated list of orders."""
        session: Session = info.context["session"]
        
        statement = select(Order).limit(min(first, 250))
        if query:
            statement = statement.where(Order.name.contains(query))
        
        orders = session.exec(statement).all()
        return [
            OrderType(
                id=o.id,
                name=o.name,
                email=o.email,
                display_financial_status=o.display_financial_status,
                display_fulfillment_status=o.display_fulfillment_status,
                total_price=str(o.total_price),
                created_at=o.created_at.isoformat(),
                updated_at=o.updated_at.isoformat(),
            )
            for o in orders
        ]
    
    @strawberry.field
    def customer(self, info: Info, id: str) -> Optional[CustomerType]:
        """Get customer by ID."""
        session: Session = info.context["session"]
        customer = session.exec(select(Customer).where(Customer.id == id)).first()
        if customer:
            return CustomerType(
                id=customer.id,
                email=customer.email,
                first_name=customer.first_name,
                last_name=customer.last_name,
                orders_count=customer.orders_count,
                total_spent=str(customer.total_spent),
                state=customer.state,
            )
        return None
    
    @strawberry.field
    def customers(
        self,
        info: Info,
        first: int = 10,
        after: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[CustomerType]:
        """Get paginated list of customers."""
        session: Session = info.context["session"]
        
        statement = select(Customer).limit(min(first, 250))
        if query:
            statement = statement.where(
                (Customer.email.contains(query)) | 
                (Customer.first_name.contains(query))
            )
        
        customers = session.exec(statement).all()
        return [
            CustomerType(
                id=c.id,
                email=c.email,
                first_name=c.first_name,
                last_name=c.last_name,
                orders_count=c.orders_count,
                total_spent=str(c.total_spent),
                state=c.state,
            )
            for c in customers
        ]
    
    @strawberry.field
    def inventory_levels(
        self,
        info: Info,
        first: int = 10,
        location_ids: Optional[List[str]] = None,
    ) -> List[InventoryLevelType]:
        """Get inventory levels, optionally filtered by location."""
        session: Session = info.context["session"]
        
        statement = select(InventoryLevel).limit(min(first, 250))
        if location_ids:
            statement = statement.where(InventoryLevel.location_id.in_(location_ids))
        
        levels = session.exec(statement).all()
        return [
            InventoryLevelType(
                id=lvl.id,
                inventory_item_id=lvl.inventory_item_id,
                location_id=lvl.location_id,
                available=lvl.available,
                incoming=lvl.incoming,
                reserved=lvl.reserved,
            )
            for lvl in levels
        ]
    
    @strawberry.field
    def support_tickets(
        self,
        info: Info,
        first: int = 10,
        status: Optional[str] = None,
    ) -> List[SupportTicketType]:
        """Get support tickets (ShopWorld-specific)."""
        session: Session = info.context["session"]
        
        statement = select(SupportTicket).limit(min(first, 250))
        if status:
            statement = statement.where(SupportTicket.status == status)
        
        tickets = session.exec(statement).all()
        return [
            SupportTicketType(
                id=t.id,
                subject=t.subject,
                status=t.status,
                priority=t.priority,
                category=t.category,
                customer_sentiment=t.customer_sentiment,
                created_at=t.created_at.isoformat(),
            )
            for t in tickets
        ]


# Mutations

@strawberry.input
class ProductUpdateInput:
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


@strawberry.input
class InventoryAdjustInput:
    inventory_item_id: str
    location_id: str
    delta: int


@strawberry.input
class RefundCreateInput:
    order_id: str
    amount: str
    reason: Optional[str] = None
    notify: bool = True


@strawberry.type
class ProductUpdatePayload:
    product: Optional[ProductType]
    user_errors: List[str]


@strawberry.type
class InventoryAdjustPayload:
    inventory_level: Optional[InventoryLevelType]
    user_errors: List[str]


@strawberry.type
class RefundCreatePayload:
    refund_id: Optional[str]
    success: bool
    user_errors: List[str]


@strawberry.type
class Mutation:
    """Shopify Admin GraphQL Mutations."""
    
    @strawberry.mutation
    def product_update(
        self,
        info: Info,
        input: ProductUpdateInput,
    ) -> ProductUpdatePayload:
        """Update a product."""
        session: Session = info.context["session"]
        
        product = session.exec(select(Product).where(Product.id == input.id)).first()
        if not product:
            return ProductUpdatePayload(product=None, user_errors=["Product not found"])
        
        # Update fields
        if input.title:
            product.title = input.title
        if input.description is not None:
            product.description = input.description
        if input.status:
            product.status = input.status
        
        session.add(product)
        session.commit()
        
        return ProductUpdatePayload(
            product=ProductType(
                id=product.id,
                title=product.title,
                handle=product.handle,
                description=product.description,
                product_type=product.product_type,
                vendor=product.vendor,
                status=product.status,
                created_at=product.created_at.isoformat(),
                updated_at=product.updated_at.isoformat(),
            ),
            user_errors=[],
        )
    
    @strawberry.mutation
    def inventory_adjust_quantities(
        self,
        info: Info,
        inputs: List[InventoryAdjustInput],
    ) -> List[InventoryAdjustPayload]:
        """Adjust inventory quantities."""
        session: Session = info.context["session"]
        results = []
        
        for input in inputs:
            level = session.exec(
                select(InventoryLevel).where(
                    (InventoryLevel.inventory_item_id == input.inventory_item_id) &
                    (InventoryLevel.location_id == input.location_id)
                )
            ).first()
            
            if not level:
                results.append(InventoryAdjustPayload(
                    inventory_level=None,
                    user_errors=["Inventory level not found"],
                ))
                continue
            
            # Apply delta
            new_available = level.available + input.delta
            if new_available < 0:
                results.append(InventoryAdjustPayload(
                    inventory_level=None,
                    user_errors=["Insufficient inventory"],
                ))
                continue
            
            level.available = new_available
            session.add(level)
            
            results.append(InventoryAdjustPayload(
                inventory_level=InventoryLevelType(
                    id=level.id,
                    inventory_item_id=level.inventory_item_id,
                    location_id=level.location_id,
                    available=level.available,
                    incoming=level.incoming,
                    reserved=level.reserved,
                ),
                user_errors=[],
            ))
        
        session.commit()
        return results
    
    @strawberry.mutation
    def refund_create(
        self,
        info: Info,
        input: RefundCreateInput,
    ) -> RefundCreatePayload:
        """Create a refund for an order."""
        session: Session = info.context["session"]
        
        # Verify order exists
        order = session.exec(select(Order).where(Order.id == input.order_id)).first()
        if not order:
            return RefundCreatePayload(
                refund_id=None,
                success=False,
                user_errors=["Order not found"],
            )
        
        # Check if refund amount exceeds order total
        refund_amount = Decimal(input.amount)
        if refund_amount > order.total_price:
            return RefundCreatePayload(
                refund_id=None,
                success=False,
                user_errors=["Refund amount exceeds order total"],
            )
        
        # Create refund
        from shopworld.apps.shopify_admin.models import Refund as RefundModel
        
        refund = RefundModel(
            id=f"gid://shopify/Refund/{order.id.split('/')[-1]}",
            order_id=input.order_id,
            total_refunded=refund_amount,
            note=input.reason,
        )
        
        session.add(refund)
        
        # Update order financial status
        order.display_financial_status = "PARTIALLY_REFUNDED" if refund_amount < order.total_price else "REFUNDED"
        session.add(order)
        
        session.commit()
        
        return RefundCreatePayload(
            refund_id=refund.id,
            success=True,
            user_errors=[],
        )


# Create schema
schema = strawberry.Schema(query=Query, mutation=Mutation)


class ShopWorldGraphQL:
    """Wrapper for GraphQL execution with ShopWorld context."""
    
    def __init__(self, session: Session):
        self.session = session
    
    async def execute(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute GraphQL query/mutation."""
        context = {"session": self.session}
        result = await schema.execute(query, variable_values=variables, context_value=context)
        
        if result.errors:
            return {
                "data": None,
                "errors": [str(e) for e in result.errors],
            }
        
        return {
            "data": result.data,
            "errors": None,
        }
