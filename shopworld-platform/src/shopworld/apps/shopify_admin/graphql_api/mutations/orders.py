"""
Order mutations: orderUpdate, orderClose, orderCancel, refundCreate,
fulfillmentCreateV2.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from decimal import Decimal, InvalidOperation
from typing import List, Optional

import strawberry
from sqlmodel import Session, select
from strawberry.types import Info

from shopworld.apps.shopify_admin.models import (
    Fulfillment,
    Order,
    Refund,
)
from shopworld.apps.shopify_admin.graphql_api.scopes import check_scope, ScopeError
from shopworld.apps.shopify_admin.graphql_api.queries.orders import OrderType, _to_order_type
from shopworld.apps.shopify_admin.graphql_api.mutations.catalog import UserError


# ---------------------------------------------------------------------------
# Input types
# ---------------------------------------------------------------------------

@strawberry.input
class OrderUpdateInput:
    id: str
    tags: Optional[List[str]] = None
    note: Optional[str] = None
    email: Optional[str] = None


@strawberry.input
class OrderCancelInput:
    id: str
    reason: Optional[str] = None    # CUSTOMER, DECLINED, FRAUD, INVENTORY, OTHER, STAFF
    restock: bool = False
    notify_customer: bool = True


@strawberry.input
class RefundLineItemInput:
    line_item_id: str
    quantity: int
    restock_type: str = "RETURN"    # RETURN, CANCEL, NO_RESTOCK, LEGACY_RESTOCK


@strawberry.input
class RefundCreateInput:
    order_id: str
    amount: Optional[str] = None    # if None, refund full remaining amount
    reason: Optional[str] = None
    note: Optional[str] = None
    notify: bool = True
    line_items: Optional[List[RefundLineItemInput]] = None
    restock: bool = False


@strawberry.input
class FulfillmentLineItemInput:
    id: str         # order_line_item_id
    quantity: int


@strawberry.input
class FulfillmentCreateInput:
    order_id: str
    fulfillment_order_id: Optional[str] = None
    location_id: Optional[str] = None
    tracking_number: Optional[str] = None
    tracking_company: Optional[str] = None
    tracking_url: Optional[str] = None
    notify_customer: bool = True


# ---------------------------------------------------------------------------
# Payload types
# ---------------------------------------------------------------------------

@strawberry.type
class FulfillmentType:
    id: str
    order_id: str
    status: str
    tracking_number: Optional[str]
    tracking_company: Optional[str]
    tracking_url: Optional[str]
    created_at: str


@strawberry.type
class OrderUpdatePayload:
    order: Optional[OrderType]
    user_errors: List[UserError]


@strawberry.type
class OrderClosePayload:
    order: Optional[OrderType]
    user_errors: List[UserError]


@strawberry.type
class OrderCancelPayload:
    order: Optional[OrderType]
    user_errors: List[UserError]


@strawberry.type
class RefundCreatePayload:
    refund_id: Optional[str]
    order: Optional[OrderType]
    user_errors: List[UserError]


@strawberry.type
class FulfillmentCreatePayload:
    fulfillment: Optional[FulfillmentType]
    user_errors: List[UserError]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_gid(resource: str) -> str:
    return f"gid://shopify/{resource}/{uuid.uuid4().hex[:12]}"


def _to_fulfillment_gql(f: Fulfillment) -> FulfillmentType:
    return FulfillmentType(
        id=f.id,
        order_id=f.order_id,
        status=f.status,
        tracking_number=f.tracking_number,
        tracking_company=f.tracking_company,
        tracking_url=f.tracking_url,
        created_at=f.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------

def resolve_order_update(
    info: Info,
    input: OrderUpdateInput,
) -> OrderUpdatePayload:
    try:
        check_scope("orderUpdate", set(info.context.get("granted_scopes", [])))
    except ScopeError as e:
        return OrderUpdatePayload(order=None, user_errors=[UserError(field=None, message=str(e))])

    session: Session = info.context["session"]
    order = session.exec(select(Order).where(Order.id == input.id)).first()
    if not order:
        return OrderUpdatePayload(
            order=None,
            user_errors=[UserError(field=["id"], message="Order not found")],
        )

    if input.tags is not None:
        order.tags = input.tags
    if input.note is not None:
        order.note = input.note
    if input.email is not None:
        order.email = input.email

    order.updated_at = datetime.now(UTC)
    session.add(order)
    session.commit()
    session.refresh(order)

    return OrderUpdatePayload(order=_to_order_type(order), user_errors=[])


def resolve_order_close(info: Info, id: str) -> OrderClosePayload:
    try:
        check_scope("orderClose", set(info.context.get("granted_scopes", [])))
    except ScopeError as e:
        return OrderClosePayload(order=None, user_errors=[UserError(field=None, message=str(e))])

    session: Session = info.context["session"]
    order = session.exec(select(Order).where(Order.id == id)).first()
    if not order:
        return OrderClosePayload(order=None, user_errors=[UserError(field=["id"], message="Order not found")])

    order.closed_at = datetime.now(UTC)
    order.updated_at = datetime.now(UTC)
    session.add(order)
    session.commit()
    session.refresh(order)

    return OrderClosePayload(order=_to_order_type(order), user_errors=[])


def resolve_order_cancel(
    info: Info,
    input: OrderCancelInput,
) -> OrderCancelPayload:
    try:
        check_scope("orderCancel", set(info.context.get("granted_scopes", [])))
    except ScopeError as e:
        return OrderCancelPayload(order=None, user_errors=[UserError(field=None, message=str(e))])

    session: Session = info.context["session"]
    order = session.exec(select(Order).where(Order.id == input.id)).first()
    if not order:
        return OrderCancelPayload(order=None, user_errors=[UserError(field=["id"], message="Order not found")])

    valid_reasons = ("CUSTOMER", "DECLINED", "FRAUD", "INVENTORY", "OTHER", "STAFF")
    if input.reason and input.reason not in valid_reasons:
        return OrderCancelPayload(
            order=None,
            user_errors=[UserError(field=["reason"], message=f"Invalid reason. Must be one of {valid_reasons}")],
        )

    if order.cancelled_at:
        return OrderCancelPayload(
            order=None,
            user_errors=[UserError(field=["id"], message="Order is already cancelled")],
        )

    order.cancelled_at = datetime.now(UTC)
    order.cancel_reason = input.reason
    order.display_financial_status = "VOIDED"
    order.display_fulfillment_status = "UNFULFILLED"
    order.updated_at = datetime.now(UTC)
    session.add(order)
    session.commit()
    session.refresh(order)

    return OrderCancelPayload(order=_to_order_type(order), user_errors=[])


def resolve_refund_create(
    info: Info,
    input: RefundCreateInput,
) -> RefundCreatePayload:
    try:
        check_scope("refundCreate", set(info.context.get("granted_scopes", [])))
    except ScopeError as e:
        return RefundCreatePayload(refund_id=None, order=None, user_errors=[UserError(field=None, message=str(e))])

    session: Session = info.context["session"]
    order = session.exec(select(Order).where(Order.id == input.order_id)).first()
    if not order:
        return RefundCreatePayload(
            refund_id=None, order=None,
            user_errors=[UserError(field=["orderId"], message="Order not found")],
        )

    # Determine refund amount
    if input.amount:
        try:
            refund_amount = Decimal(input.amount)
        except InvalidOperation:
            return RefundCreatePayload(
                refund_id=None, order=None,
                user_errors=[UserError(field=["amount"], message="Invalid amount")],
            )
        if refund_amount > order.total_price:
            return RefundCreatePayload(
                refund_id=None, order=None,
                user_errors=[UserError(field=["amount"], message="Refund amount exceeds order total")],
            )
    else:
        refund_amount = order.total_price

    refund = Refund(
        id=_new_gid("Refund"),
        order_id=input.order_id,
        total_refunded=refund_amount,
        note=input.note,
        reason=input.reason,
        restock=input.restock,
        created_at=datetime.now(UTC),
    )
    session.add(refund)

    order.display_financial_status = (
        "PARTIALLY_REFUNDED" if refund_amount < order.total_price else "REFUNDED"
    )
    order.updated_at = datetime.now(UTC)
    session.add(order)
    session.commit()
    session.refresh(order)

    return RefundCreatePayload(refund_id=refund.id, order=_to_order_type(order), user_errors=[])


def resolve_fulfillment_create(
    info: Info,
    input: FulfillmentCreateInput,
) -> FulfillmentCreatePayload:
    try:
        check_scope("fulfillmentCreateV2", set(info.context.get("granted_scopes", [])))
    except ScopeError as e:
        return FulfillmentCreatePayload(fulfillment=None, user_errors=[UserError(field=None, message=str(e))])

    session: Session = info.context["session"]
    order = session.exec(select(Order).where(Order.id == input.order_id)).first()
    if not order:
        return FulfillmentCreatePayload(
            fulfillment=None,
            user_errors=[UserError(field=["orderId"], message="Order not found")],
        )

    fulfillment = Fulfillment(
        id=_new_gid("Fulfillment"),
        order_id=input.order_id,
        location_id=input.location_id,
        fulfillment_order_id=input.fulfillment_order_id,
        tracking_number=input.tracking_number,
        tracking_company=input.tracking_company,
        tracking_url=input.tracking_url,
        status="SUCCESS" if input.tracking_number else "PENDING",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(fulfillment)

    # Update order fulfillment status
    order.display_fulfillment_status = "FULFILLED"
    order.updated_at = datetime.now(UTC)
    session.add(order)
    session.commit()
    session.refresh(fulfillment)

    return FulfillmentCreatePayload(fulfillment=_to_fulfillment_gql(fulfillment), user_errors=[])
