"""
Order queries: orders, fulfillmentOrders, abandonedCheckouts.

Status:
  order(id)                      — implemented (with Connection upgrade)
  orders(first, after, query)    — Connection type
  fulfillmentOrder(id)           — TODO: implement
  fulfillmentOrders(first, after)— TODO: implement
  abandonedCheckouts(...)        — deferred (post-MVP model)
"""

from __future__ import annotations

from typing import List, Optional

import strawberry
from sqlmodel import Session, select
from strawberry.types import Info

from shopworld.apps.shopify_admin.models import (
    FulfillmentOrder,
    Order,
)
from shopworld.apps.shopify_admin.graphql_api.pagination import paginate, PageInfoType, encode_cursor
from shopworld.apps.shopify_admin.graphql_api.scopes import check_scope


# ---------------------------------------------------------------------------
# GQL types
# ---------------------------------------------------------------------------

@strawberry.type
class OrderLineItemType:
    id: str
    title: str
    variant_title: Optional[str]
    sku: Optional[str]
    quantity: int
    fulfillable_quantity: int
    fulfilled_quantity: int
    price: str


@strawberry.type
class OrderType:
    id: str
    name: str
    email: Optional[str]
    display_financial_status: str
    display_fulfillment_status: str
    total_price: str
    subtotal_price: str
    total_tax: str
    total_discounts: str
    currency_code: str
    risk_level: Optional[str]
    tags: List[str]
    note: Optional[str]
    created_at: str
    updated_at: str


@strawberry.type
class OrderEdge:
    node: OrderType
    cursor: str


@strawberry.type
class OrderConnection:
    edges: List[OrderEdge]
    page_info: PageInfoType


@strawberry.type
class FulfillmentOrderLineItemType:
    order_line_item_id: str


@strawberry.type
class FulfillmentOrderType:
    id: str
    order_id: str
    status: str
    request_status: Optional[str]
    fulfillment_service_handle: Optional[str]
    supported_actions: List[str]
    created_at: str
    updated_at: str


@strawberry.type
class FulfillmentOrderEdge:
    node: FulfillmentOrderType
    cursor: str


@strawberry.type
class FulfillmentOrderConnection:
    edges: List[FulfillmentOrderEdge]
    page_info: PageInfoType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_order_type(o: Order) -> OrderType:
    return OrderType(
        id=o.id,
        name=o.name,
        email=o.email,
        display_financial_status=o.display_financial_status,
        display_fulfillment_status=o.display_fulfillment_status,
        total_price=str(o.total_price),
        subtotal_price=str(o.subtotal_price),
        total_tax=str(o.total_tax),
        total_discounts=str(o.total_discounts),
        currency_code=o.currency_code,
        risk_level=o.risk_level,
        tags=list(o.tags or []),
        note=o.note,
        created_at=o.created_at.isoformat(),
        updated_at=o.updated_at.isoformat(),
    )


def _to_fulfillment_order_type(fo: FulfillmentOrder) -> FulfillmentOrderType:
    return FulfillmentOrderType(
        id=fo.id,
        order_id=fo.order_id,
        status=fo.status,
        request_status=fo.request_status,
        fulfillment_service_handle=fo.fulfillment_service_handle,
        supported_actions=list(fo.supported_actions or []),
        created_at=fo.created_at.isoformat(),
        updated_at=fo.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------

def resolve_order(info: Info, id: str) -> Optional[OrderType]:
    check_scope("order", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]
    o = session.exec(select(Order).where(Order.id == id)).first()
    return _to_order_type(o) if o else None


def resolve_orders(
    info: Info,
    first: int = 10,
    after: Optional[str] = None,
    query: Optional[str] = None,
    sort_key: Optional[str] = None,
    reverse: bool = False,
) -> OrderConnection:
    check_scope("orders", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]

    stmt = select(Order)
    if query:
        # Support simple filter expressions like "financial_status:paid"
        if ":" in query:
            field, value = query.split(":", 1)
            field = field.strip()
            value = value.strip()
            if field == "financial_status":
                stmt = stmt.where(Order.display_financial_status == value.upper())
            elif field == "fulfillment_status":
                stmt = stmt.where(Order.display_fulfillment_status == value.upper())
            elif field == "tag":
                pass  # TODO: JSON array containment query
        else:
            stmt = stmt.where(Order.name.contains(query))

    all_orders = session.exec(stmt).all()
    if reverse:
        all_orders = list(reversed(all_orders))

    page, page_info = paginate(all_orders, first, after, table="orders")
    edges = [
        OrderEdge(node=_to_order_type(o), cursor=encode_cursor("orders", o.id))
        for o in page
    ]
    return OrderConnection(
        edges=edges,
        page_info=PageInfoType(
            has_next_page=page_info.has_next_page,
            has_previous_page=page_info.has_previous_page,
            start_cursor=page_info.start_cursor,
            end_cursor=page_info.end_cursor,
        ),
    )


def resolve_fulfillment_order(info: Info, id: str) -> Optional[FulfillmentOrderType]:
    check_scope("fulfillmentOrder", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]
    fo = session.exec(select(FulfillmentOrder).where(FulfillmentOrder.id == id)).first()
    return _to_fulfillment_order_type(fo) if fo else None


def resolve_fulfillment_orders(
    info: Info,
    order_id: Optional[str] = None,
    first: int = 10,
    after: Optional[str] = None,
) -> FulfillmentOrderConnection:
    check_scope("fulfillmentOrders", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]

    stmt = select(FulfillmentOrder)
    if order_id:
        stmt = stmt.where(FulfillmentOrder.order_id == order_id)
    all_fos = session.exec(stmt).all()

    page, page_info = paginate(all_fos, first, after, table="fulfillment_orders")
    edges = [
        FulfillmentOrderEdge(
            node=_to_fulfillment_order_type(fo),
            cursor=encode_cursor("fulfillment_orders", fo.id),
        )
        for fo in page
    ]
    return FulfillmentOrderConnection(
        edges=edges,
        page_info=PageInfoType(
            has_next_page=page_info.has_next_page,
            has_previous_page=page_info.has_previous_page,
            start_cursor=page_info.start_cursor,
            end_cursor=page_info.end_cursor,
        ),
    )
