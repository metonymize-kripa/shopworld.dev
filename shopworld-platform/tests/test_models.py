"""Tests for SQLModel database models."""

import pytest
from decimal import Decimal
from datetime import datetime

from sqlmodel import Session, select

from shopworld.apps.lib.db import init_database
from shopworld.apps.shopify_admin.models import (
    Product, ProductVariant, Customer, Order, OrderLineItem,
    InventoryItem, InventoryLevel, Location, SupportTicket,
)


@pytest.fixture
def db():
    """Create in-memory database for tests."""
    db = init_database(":memory:")
    yield db


class TestProductModel:
    """Test Product model."""
    
    def test_create_product(self, db):
        """Test product can be created."""
        with db.session() as session:
            product = Product(
                id="gid://shopify/Product/1",
                title="Test Product",
                handle="test-product",
                description="A test product",
                price_range_min=Decimal("19.99"),
                price_range_max=Decimal("29.99"),
            )
            session.add(product)
            session.commit()
            
            # Query it back
            result = session.exec(select(Product).where(Product.id == "gid://shopify/Product/1")).first()
            assert result is not None
            assert result.title == "Test Product"
    
    def test_product_variants_relationship(self, db):
        """Test product-variant relationship."""
        with db.session() as session:
            product = Product(
                id="gid://shopify/Product/2",
                title="Shirt",
                handle="shirt",
            )
            
            variant = ProductVariant(
                id="gid://shopify/ProductVariant/1",
                product_id="gid://shopify/Product/2",
                sku="SHIRT-BLUE-M",
                option1="Blue",
                option2="M",
                price=Decimal("29.99"),
            )
            
            session.add(product)
            session.add(variant)
            session.commit()
            
            # Query with relationship
            result = session.exec(select(Product).where(Product.id == "gid://shopify/Product/2")).first()
            assert len(result.variants) == 1
            assert result.variants[0].sku == "SHIRT-BLUE-M"


class TestOrderModel:
    """Test Order model."""
    
    def test_create_order(self, db):
        """Test order can be created."""
        with db.session() as session:
            order = Order(
                id="gid://shopify/Order/1",
                name="#1001",
                email="customer@example.com",
                total_price=Decimal("99.99"),
                subtotal_price=Decimal("89.99"),
                total_tax=Decimal("10.00"),
            )
            session.add(order)
            session.commit()
            
            result = session.exec(select(Order).where(Order.id == "gid://shopify/Order/1")).first()
            assert result is not None
            assert result.name == "#1001"
    
    def test_order_line_items(self, db):
        """Test order with line items."""
        with db.session() as session:
            order = Order(
                id="gid://shopify/Order/2",
                name="#1002",
                total_price=Decimal("49.99"),
            )
            
            line_item = OrderLineItem(
                id="gid://shopify/OrderLineItem/1",
                order_id="gid://shopify/Order/2",
                title="Widget",
                quantity=2,
                price=Decimal("24.99"),
            )
            
            session.add(order)
            session.add(line_item)
            session.commit()
            
            result = session.exec(select(Order).where(Order.id == "gid://shopify/Order/2")).first()
            assert len(result.line_items) == 1
            assert result.line_items[0].quantity == 2


class TestInventoryModel:
    """Test Inventory models."""
    
    def test_inventory_levels(self, db):
        """Test inventory levels at locations."""
        with db.session() as session:
            location = Location(
                id="gid://shopify/Location/1",
                name="Warehouse",
                active=True,
            )
            
            inventory_item = InventoryItem(
                id="gid://shopify/InventoryItem/1",
                sku="SKU-001",
                tracked=True,
            )
            
            level = InventoryLevel(
                inventory_item_id="gid://shopify/InventoryItem/1",
                location_id="gid://shopify/Location/1",
                available=100,
                incoming=50,
                reserved=10,
            )
            
            session.add(location)
            session.add(inventory_item)
            session.add(level)
            session.commit()
            
            # Query level with relationships
            result = session.exec(
                select(InventoryLevel).where(
                    InventoryLevel.inventory_item_id == "gid://shopify/InventoryItem/1"
                )
            ).first()
            
            assert result is not None
            assert result.available == 100
            assert result.location.name == "Warehouse"


class TestSupportTicketModel:
    """Test SupportTicket model."""
    
    def test_create_ticket(self, db):
        """Test support ticket can be created."""
        with db.session() as session:
            ticket = SupportTicket(
                id="ticket-001",
                subject="Where is my order?",
                description="Customer asking about order #1001",
                category="ORDER_ISSUE",
                priority="HIGH",
                status="OPEN",
                customer_sentiment=-0.3,
            )
            session.add(ticket)
            session.commit()
            
            result = session.exec(select(SupportTicket).where(SupportTicket.id == "ticket-001")).first()
            assert result is not None
            assert result.category == "ORDER_ISSUE"
            assert result.customer_sentiment == -0.3


class TestCustomerModel:
    """Test Customer model."""
    
    def test_create_customer(self, db):
        """Test customer can be created."""
        with db.session() as session:
            customer = Customer(
                id="gid://shopify/Customer/1",
                email="test@example.com",
                first_name="John",
                last_name="Doe",
                total_spent=Decimal("499.99"),
                orders_count=5,
            )
            session.add(customer)
            session.commit()
            
            result = session.exec(select(Customer).where(Customer.id == "gid://shopify/Customer/1")).first()
            assert result is not None
            assert result.first_name == "John"
            assert result.total_spent == Decimal("499.99")
