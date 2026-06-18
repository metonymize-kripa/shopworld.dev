"""SQLModel definitions for Shopify commerce entities."""

from datetime import datetime, UTC
from typing import Optional, List
from decimal import Decimal

from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import String, Numeric, DateTime, JSON, Text, Enum
import enum


class OrderStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class FinancialStatus(str, enum.Enum):
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    REFUNDED = "REFUNDED"
    VOIDED = "VOIDED"


class FulfillmentStatus(str, enum.Enum):
    UNFULFILLED = "UNFULFILLED"
    PARTIAL = "PARTIAL"
    FULFILLED = "FULFILLED"
    RESTOCKED = "RESTOCKED"


# Product and Catalog

class Product(SQLModel, table=True):
    """Shopify Product entity."""
    
    __tablename__ = "products"
    
    id: str = Field(primary_key=True)  # gid://shopify/Product/...
    title: str = Field(index=True)
    handle: str = Field(index=True)
    description: Optional[str] = None
    product_type: Optional[str] = None
    vendor: Optional[str] = None
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    status: str = Field(default="ACTIVE")  # ACTIVE, ARCHIVED, DRAFT
    
    # Pricing
    price_range_min: Decimal = Field(sa_column=Column(Numeric(10, 2), default=0))
    price_range_max: Decimal = Field(sa_column=Column(Numeric(10, 2), default=0))
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    published_at: Optional[datetime] = None
    
    # Relationships
    variants: List["ProductVariant"] = Relationship(back_populates="product")
    metafields: List["Metafield"] = Relationship(back_populates="parent_product")
    collections: List["CollectionProductLink"] = Relationship(back_populates="product")


class ProductVariant(SQLModel, table=True):
    """Product variant (size, color, etc.)."""
    
    __tablename__ = "product_variants"
    
    id: str = Field(primary_key=True)
    product_id: str = Field(foreign_key="products.id", index=True)
    sku: Optional[str] = Field(index=True)
    barcode: Optional[str] = None
    
    # Variant options
    option1: Optional[str] = None
    option2: Optional[str] = None
    option3: Optional[str] = None
    
    # Pricing
    price: Decimal = Field(sa_column=Column(Numeric(10, 2), default=0))
    compare_at_price: Optional[Decimal] = Field(sa_column=Column(Numeric(10, 2), nullable=True))
    cost: Optional[Decimal] = Field(sa_column=Column(Numeric(10, 2), nullable=True))
    
    # Tax
    taxable: bool = Field(default=True)
    tax_code: Optional[str] = None
    
    # Shipping
    requires_shipping: bool = Field(default=True)
    weight: Optional[Decimal] = None
    weight_unit: Optional[str] = None
    
    # Inventory link
    inventory_item_id: Optional[str] = Field(foreign_key="inventory_items.id", nullable=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Relationships
    product: Product = Relationship(back_populates="variants")
    inventory_item: Optional["InventoryItem"] = Relationship(back_populates="variants")


# Inventory

class InventoryItem(SQLModel, table=True):
    """Inventory item (tracks quantity across locations)."""
    
    __tablename__ = "inventory_items"
    
    id: str = Field(primary_key=True)
    sku: Optional[str] = Field(index=True)
    tracked: bool = Field(default=True)
    
    # Settings
    country_code_of_origin: Optional[str] = None
    province_code_of_origin: Optional[str] = None
    harmonized_system_code: Optional[str] = None
    
    # Relationships
    variants: List[ProductVariant] = Relationship(back_populates="inventory_item")
    levels: List["InventoryLevel"] = Relationship(back_populates="inventory_item")


class Location(SQLModel, table=True):
    """Inventory location (warehouse, retail store)."""
    
    __tablename__ = "locations"
    
    id: str = Field(primary_key=True)
    name: str
    address1: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None
    zip: Optional[str] = None
    phone: Optional[str] = None
    
    # Status
    active: bool = Field(default=True)
    fulfillment_service_handle: Optional[str] = None
    
    # Relationships
    inventory_levels: List["InventoryLevel"] = Relationship(back_populates="location")
    location_fulfillments: List["Fulfillment"] = Relationship(back_populates="location")
    assigned_fulfillment_orders: List["FulfillmentOrder"] = Relationship(back_populates="assigned_location")


class InventoryLevel(SQLModel, table=True):
    """Inventory quantity at a specific location."""
    
    __tablename__ = "inventory_levels"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    inventory_item_id: str = Field(foreign_key="inventory_items.id", index=True)
    location_id: str = Field(foreign_key="locations.id", index=True)
    
    available: int = Field(default=0)
    incoming: int = Field(default=0)
    reserved: int = Field(default=0)
    committed: int = Field(default=0)
    damaged: int = Field(default=0)
    safety_stock: int = Field(default=0)
    quality_control: int = Field(default=0)
    
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Relationships
    inventory_item: InventoryItem = Relationship(back_populates="levels")
    location: Location = Relationship(back_populates="inventory_levels")


# Customers

class Customer(SQLModel, table=True):
    """Shopify Customer."""
    
    __tablename__ = "customers"
    
    id: str = Field(primary_key=True)
    email: Optional[str] = Field(index=True)
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    # Status
    state: str = Field(default="ENABLED")  # ENABLED, DISABLED, INVITED, DECLINED
    verified_email: bool = Field(default=False)
    tax_exempt: bool = Field(default=False)
    
    # Metrics
    orders_count: int = Field(default=0)
    total_spent: Decimal = Field(sa_column=Column(Numeric(10, 2), default=0))
    average_order_amount: Optional[Decimal] = Field(sa_column=Column(Numeric(10, 2), nullable=True))
    
    # Tags and notes
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    note: Optional[str] = None
    
    # Addresses (simplified - just primary)
    default_address_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Relationships
    orders: List["Order"] = Relationship(back_populates="customer")
    metafields: List["Metafield"] = Relationship(back_populates="parent_customer")


# Orders

class Order(SQLModel, table=True):
    """Shopify Order."""
    
    __tablename__ = "orders"
    
    id: str = Field(primary_key=True)
    name: str = Field(index=True)  # #1001, #1002, etc.
    
    # Customer
    customer_id: Optional[str] = Field(foreign_key="customers.id", index=True, nullable=True)
    email: Optional[str] = None
    phone: Optional[str] = None
    
    # Status
    display_financial_status: str = Field(default="PENDING")
    display_fulfillment_status: str = Field(default="UNFULFILLED")
    confirmed: bool = Field(default=False)
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    
    # Financial
    subtotal_price: Decimal = Field(sa_column=Column(Numeric(10, 2), default=0))
    total_tax: Decimal = Field(sa_column=Column(Numeric(10, 2), default=0))
    total_shipping: Decimal = Field(sa_column=Column(Numeric(10, 2), default=0))
    total_discounts: Decimal = Field(sa_column=Column(Numeric(10, 2), default=0))
    total_price: Decimal = Field(sa_column=Column(Numeric(10, 2), default=0))
    currency_code: str = Field(default="USD")
    
    # Payment
    payment_gateway_names: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    processing_method: Optional[str] = None
    
    # Risk
    risk_level: Optional[str] = None  # LOW, MEDIUM, HIGH
    
    # Source
    source_name: Optional[str] = None  # web, pos, iphone, etc.
    
    # Tags and notes
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    note: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    processed_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    # Relationships
    customer: Optional[Customer] = Relationship(back_populates="orders")
    line_items: List["OrderLineItem"] = Relationship(back_populates="order")
    fulfillments: List["Fulfillment"] = Relationship(back_populates="order")
    refunds: List["Refund"] = Relationship(back_populates="order")
    metafields: List["Metafield"] = Relationship(back_populates="parent_order")
    fulfillment_orders: List["FulfillmentOrder"] = Relationship(back_populates="order")


class OrderLineItem(SQLModel, table=True):
    """Line item within an order."""
    
    __tablename__ = "order_line_items"
    
    id: str = Field(primary_key=True)
    order_id: str = Field(foreign_key="orders.id", index=True)
    
    # Product reference
    product_id: Optional[str] = Field(foreign_key="products.id", nullable=True)
    variant_id: Optional[str] = Field(foreign_key="product_variants.id", nullable=True)
    
    # Line details
    title: str
    variant_title: Optional[str] = None
    sku: Optional[str] = None
    
    # Quantity
    quantity: int
    fulfillable_quantity: int = Field(default=0)
    fulfilled_quantity: int = Field(default=0)
    
    # Pricing
    price: Decimal = Field(sa_column=Column(Numeric(10, 2), default=0))
    discounted_price: Decimal = Field(sa_column=Column(Numeric(10, 2), default=0))
    total_discount: Decimal = Field(sa_column=Column(Numeric(10, 2), default=0))
    
    # Tax
    taxable: bool = Field(default=True)
    
    # Relationships
    order: Order = Relationship(back_populates="line_items")
    fulfillments: List["FulfillmentLineItem"] = Relationship(back_populates="order_line_item")


# Fulfillment

class FulfillmentOrder(SQLModel, table=True):
    """Fulfillment order - represents items to be fulfilled together."""
    
    __tablename__ = "fulfillment_orders"
    
    id: str = Field(primary_key=True)
    order_id: str = Field(foreign_key="orders.id", index=True)
    location_id: Optional[str] = Field(foreign_key="locations.id", nullable=True)
    
    # Status
    status: str = Field(default="OPEN")  # OPEN, CLOSED, CANCELLED
    request_status: Optional[str] = None  # UNSUBMITTED, SUBMITTED, ACCEPTED, REJECTED, CANCELLATION_REQUESTED, CANCELLATION_ACCEPTED, CANCELLATION_REJECTED, CLOSED
    
    # Support for fulfillment service
    fulfillment_service_handle: Optional[str] = None
    supported_actions: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    
    # Line items (simplified - just IDs)
    line_item_ids: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    
    # Destination
    destination: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Relationships
    order: Order = Relationship(back_populates="fulfillment_orders")
    assigned_location: Optional[Location] = Relationship(back_populates="assigned_fulfillment_orders")
    fulfillment_order_fulfillments: List["Fulfillment"] = Relationship(back_populates="fulfillment_order")


class Fulfillment(SQLModel, table=True):
    """Actual fulfillment (shipment)."""
    
    __tablename__ = "fulfillments"
    
    id: str = Field(primary_key=True)
    order_id: str = Field(foreign_key="orders.id", index=True)
    location_id: Optional[str] = Field(foreign_key="locations.id", nullable=True)
    fulfillment_order_id: Optional[str] = Field(foreign_key="fulfillment_orders.id", nullable=True)
    
    # Tracking
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    tracking_company: Optional[str] = None
    
    # Status
    status: str = Field(default="PENDING")  # PENDING, OPEN, SUCCESS, CANCELLED, ERROR, FAILURE
    display_status: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    delivered_at: Optional[datetime] = None
    
    # Relationships
    order: Order = Relationship(back_populates="fulfillments")
    location: Optional[Location] = Relationship(back_populates="location_fulfillments")
    fulfillment_order: Optional[FulfillmentOrder] = Relationship(back_populates="fulfillment_order_fulfillments")
    line_items: List["FulfillmentLineItem"] = Relationship(back_populates="fulfillment")


class FulfillmentLineItem(SQLModel, table=True):
    """Line items within a fulfillment."""
    
    __tablename__ = "fulfillment_line_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    fulfillment_id: str = Field(foreign_key="fulfillments.id", index=True)
    order_line_item_id: str = Field(foreign_key="order_line_items.id", index=True)
    quantity: int
    
    # Relationships
    fulfillment: Fulfillment = Relationship(back_populates="line_items")
    order_line_item: OrderLineItem = Relationship(back_populates="fulfillments")


# Refunds

class Refund(SQLModel, table=True):
    """Order refund."""
    
    __tablename__ = "refunds"
    
    id: str = Field(primary_key=True)
    order_id: str = Field(foreign_key="orders.id", index=True)
    
    # Amount
    total_refunded: Decimal = Field(sa_column=Column(Numeric(10, 2), default=0))
    
    # Reason
    note: Optional[str] = None
    reason: Optional[str] = None
    
    # Status
    restock: bool = Field(default=False)
    
    # Transactions (simplified)
    transactions: List[dict] = Field(default_factory=list, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Relationships
    order: Order = Relationship(back_populates="refunds")
    refund_line_items: List["RefundLineItem"] = Relationship(back_populates="refund")


class RefundLineItem(SQLModel, table=True):
    """Line items within a refund."""
    
    __tablename__ = "refund_line_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    refund_id: str = Field(foreign_key="refunds.id", index=True)
    order_line_item_id: str = Field(foreign_key="order_line_items.id", index=True)
    quantity: int
    restock_type: Optional[str] = None  # CANCEL, RETURN, NO_RESTOCK
    
    # Pricing
    price: Decimal = Field(sa_column=Column(Numeric(10, 2), default=0))
    subtotal: Decimal = Field(sa_column=Column(Numeric(10, 2), default=0))
    total_tax: Decimal = Field(sa_column=Column(Numeric(10, 2), default=0))
    
    # Relationships
    refund: Refund = Relationship(back_populates="refund_line_items")


# Discounts

class DiscountCode(SQLModel, table=True):
    """Discount code (percentage or fixed amount off)."""
    
    __tablename__ = "discount_codes"
    
    id: str = Field(primary_key=True)
    code: str = Field(index=True)
    
    # Type
    discount_type: str  # PERCENTAGE, FIXED_AMOUNT
    value: Decimal = Field(sa_column=Column(Numeric(10, 2), default=0))
    
    # Constraints
    minimum_requirement_amount: Optional[Decimal] = Field(sa_column=Column(Numeric(10, 2), nullable=True))
    minimum_requirement_quantity: Optional[int] = None
    usage_limit: Optional[int] = None
    applies_once_per_customer: bool = Field(default=False)
    
    # Target
    target_type: str = Field(default="LINE_ITEM")  # LINE_ITEM, SHIPPING_LINE
    target_selection: str = Field(default="ENTITLED")  # ALL, ENTITLED
    target_resources: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    
    # Status
    status: str = Field(default="ACTIVE")  # ACTIVE, EXPIRED, DISABLED
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


# Metafields

class Metafield(SQLModel, table=True):
    """Custom key-value data attached to resources."""
    
    __tablename__ = "metafields"
    
    id: str = Field(primary_key=True)
    namespace: str = Field(index=True)  # Custom grouping
    key: str = Field(index=True)
    value: str
    type: str = Field(default="single_line_text_field")
    
    # Owner reference (polymorphic via owner_type + owner_id)
    owner_type: str = Field(index=True)  # product, customer, order, etc.
    owner_id: str = Field(index=True)
    
    # Parent relationships (optional, for convenience)
    parent_product_id: Optional[str] = Field(foreign_key="products.id", nullable=True)
    parent_customer_id: Optional[str] = Field(foreign_key="customers.id", nullable=True)
    parent_order_id: Optional[str] = Field(foreign_key="orders.id", nullable=True)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Relationships
    parent_product: Optional[Product] = Relationship(back_populates="metafields")
    parent_customer: Optional[Customer] = Relationship(back_populates="metafields")
    parent_order: Optional[Order] = Relationship(back_populates="metafields")


# Collections

class Collection(SQLModel, table=True):
    """Product collection (manual or automatic)."""
    
    __tablename__ = "collections"
    
    id: str = Field(primary_key=True)
    title: str
    handle: str = Field(index=True)
    description: Optional[str] = None
    description_html: Optional[str] = None
    
    # Type
    collection_type: str = Field(default="CUSTOM")  # CUSTOM, SMART
    
    # Rules (for smart collections)
    rules: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    # Sorting
    sort_order: str = Field(default="MANUAL")
    
    # SEO
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    published_at: Optional[datetime] = None
    
    # Relationships
    products: List["CollectionProductLink"] = Relationship(back_populates="collection")


class CollectionProductLink(SQLModel, table=True):
    """Many-to-many link between collections and products."""
    
    __tablename__ = "collection_products"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    collection_id: str = Field(foreign_key="collections.id", index=True)
    product_id: str = Field(foreign_key="products.id", index=True)
    position: int = Field(default=0)
    
    # Relationships
    collection: Collection = Relationship(back_populates="products")
    product: Product = Relationship(back_populates="collections")


# Support Tickets (ShopWorld-specific, not native Shopify)

class SupportTicket(SQLModel, table=True):
    """Customer support ticket."""
    
    __tablename__ = "support_tickets"
    
    id: str = Field(primary_key=True)
    customer_id: Optional[str] = Field(foreign_key="customers.id", nullable=True)
    order_id: Optional[str] = Field(foreign_key="orders.id", nullable=True)
    
    # Issue
    subject: str
    description: Optional[str] = None
    category: str  # ORDER_ISSUE, PRODUCT_QUESTION, RETURN_REQUEST, etc.
    priority: str = Field(default="MEDIUM")  # LOW, MEDIUM, HIGH, URGENT
    
    # Status
    status: str = Field(default="OPEN")  # OPEN, PENDING, SOLVED, CLOSED
    
    # Assignment
    assignee_id: Optional[str] = None
    
    # SLA
    sla_deadline: Optional[datetime] = None
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Sentiment (simulated)
    customer_sentiment: float = Field(default=0.0)  # -1 to 1
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Relationships
    messages: List["SupportMessage"] = Relationship(back_populates="ticket")


class SupportMessage(SQLModel, table=True):
    """Message within a support ticket."""
    
    __tablename__ = "support_messages"
    
    id: str = Field(primary_key=True)
    ticket_id: str = Field(foreign_key="support_tickets.id", index=True)
    
    # Sender
    sender_type: str  # CUSTOMER, AGENT, SYSTEM
    sender_id: Optional[str] = None
    
    # Content
    body: str
    body_html: Optional[str] = None
    
    # Metadata
    is_internal: bool = Field(default=False)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Relationships
    ticket: SupportTicket = Relationship(back_populates="messages")
