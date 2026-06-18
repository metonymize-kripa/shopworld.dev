"""
Extended models for post-MVP Shopify API surface.

These are stubs that define the DB schema for features deferred past Phase 2.
They are included now so the schema and data generators can reference them
without requiring the full resolver implementation.

TODO items are marked with # TODO comments.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


# ---------------------------------------------------------------------------
# Returns (post-MVP)
# ---------------------------------------------------------------------------

class Return(SQLModel, table=True):
    """
    Shopify Return — initiated after delivery.
    Distinct from Refund (which is a financial event).
    """

    __tablename__ = "returns"

    id: str = Field(primary_key=True)   # gid://shopify/Return/...
    order_id: str = Field(foreign_key="orders.id", index=True)

    # Status: OPEN, CLOSED, DECLINED, CANCELED
    status: str = Field(default="OPEN")
    decline_reason: Optional[str] = None

    # Return reason codes: SIZE_TOO_SMALL, SIZE_TOO_LARGE, COLOR, STYLE,
    # DEFECTIVE, NOT_AS_DESCRIBED, OTHER, UNWANTED
    return_reason: Optional[str] = None
    customer_note: Optional[str] = None

    # Line items stored as JSON list of {line_item_id, quantity, reason}
    # TODO: normalize into a ReturnLineItem table
    line_items: List[dict] = Field(default_factory=list, sa_column=Column(JSON))

    # Restocking
    restock: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# AbandonedCheckout (post-MVP)
# ---------------------------------------------------------------------------

class AbandonedCheckout(SQLModel, table=True):
    """
    Shopify AbandonedCheckout — cart not converted to an order.
    Useful for training agents on recovery workflows.
    """

    __tablename__ = "abandoned_checkouts"

    id: str = Field(primary_key=True)   # gid://shopify/AbandonedCheckout/...
    customer_id: Optional[str] = Field(foreign_key="customers.id", nullable=True)
    email: Optional[str] = None

    # Cart value
    total_price: Optional[str] = None
    line_items: List[dict] = Field(default_factory=list, sa_column=Column(JSON))

    # Recovery state
    recovered: bool = Field(default=False)
    recovery_url: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    abandoned_checkout_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Metaobject (post-MVP)
# ---------------------------------------------------------------------------

class Metaobject(SQLModel, table=True):
    """
    Shopify Metaobject — structured custom content (e.g. FAQ, size guides).
    Metaobjects have a type definition and typed fields.
    """

    __tablename__ = "metaobjects"

    id: str = Field(primary_key=True)   # gid://shopify/Metaobject/...

    # Type handle defined in MetaobjectDefinition (not modeled yet)
    type: str = Field(index=True)       # e.g. "size_guide", "faq"
    handle: str = Field(index=True)

    # Fields stored as JSON: [{key, value, type}]
    # TODO: normalize into MetaobjectField table
    fields: List[dict] = Field(default_factory=list, sa_column=Column(JSON))

    # Status: ACTIVE, DRAFT
    status: str = Field(default="ACTIVE")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# PriceList (post-MVP — Markets / B2B)
# ---------------------------------------------------------------------------

class PriceList(SQLModel, table=True):
    """
    Shopify PriceList — fixed or percentage price adjustments for a market or
    B2B company.  Used in Markets and B2B workflows.
    """

    __tablename__ = "price_lists"

    id: str = Field(primary_key=True)   # gid://shopify/PriceList/...
    name: str
    currency: str = Field(default="USD")

    # Parent context
    parent_type: Optional[str] = None   # "market" | "company"
    parent_id: Optional[str] = None

    # Adjustment type: PERCENTAGE | FIXED
    adjustment_type: Optional[str] = None
    adjustment_value: Optional[str] = None  # stored as string for flexibility

    # Per-variant price overrides: [{variant_id, price, compare_at_price}]
    # TODO: normalize into PriceListPrice table
    prices: List[dict] = Field(default_factory=list, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
