"""
Discount mutations: discountCodeBasicCreate, discountCodeUpdate.

Shopify's discountCodeBasicCreate creates a basic percentage or fixed-amount
discount code via the DiscountCodeBasicInput.  We model the subset of fields
most relevant to operational scenarios.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Optional

import strawberry
from sqlmodel import Session, select
from strawberry.types import Info

from shopworld.apps.shopify_admin.models import DiscountCode
from shopworld.apps.shopify_admin.graphql_api.scopes import check_scope, ScopeError
from shopworld.apps.shopify_admin.graphql_api.queries.discounts import DiscountNodeType, _to_discount_node
from shopworld.apps.shopify_admin.graphql_api.mutations.catalog import UserError


# ---------------------------------------------------------------------------
# Input types
# ---------------------------------------------------------------------------

@strawberry.input
class DiscountCodeBasicInput:
    title: str
    code: str
    discount_type: str          # "PERCENTAGE" | "FIXED_AMOUNT"
    value: str                  # e.g. "10" for 10% or "$10"
    usage_limit: Optional[int] = None
    applies_once_per_customer: bool = False
    starts_at: Optional[str] = None   # ISO datetime string
    ends_at: Optional[str] = None     # ISO datetime string
    minimum_subtotal: Optional[str] = None


@strawberry.input
class DiscountCodeUpdateInput:
    id: str
    code: Optional[str] = None
    usage_limit: Optional[int] = None
    ends_at: Optional[str] = None
    status: Optional[str] = None    # "ACTIVE" | "DISABLED"


# ---------------------------------------------------------------------------
# Payload types
# ---------------------------------------------------------------------------

@strawberry.type
class DiscountCodeBasicCreatePayload:
    discount_node: Optional[DiscountNodeType]
    user_errors: List[UserError]


@strawberry.type
class DiscountCodeUpdatePayload:
    discount_node: Optional[DiscountNodeType]
    user_errors: List[UserError]


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------

def resolve_discount_code_basic_create(
    info: Info,
    basic_code_discount: DiscountCodeBasicInput,
) -> DiscountCodeBasicCreatePayload:
    try:
        check_scope("discountCodeBasicCreate", set(info.context.get("granted_scopes", [])))
    except ScopeError as e:
        return DiscountCodeBasicCreatePayload(discount_node=None, user_errors=[UserError(field=None, message=str(e))])

    session: Session = info.context["session"]

    # Validate discount type
    if basic_code_discount.discount_type not in ("PERCENTAGE", "FIXED_AMOUNT"):
        return DiscountCodeBasicCreatePayload(
            discount_node=None,
            user_errors=[UserError(field=["discountType"], message="Must be PERCENTAGE or FIXED_AMOUNT")],
        )

    # Validate value
    try:
        value = Decimal(basic_code_discount.value)
        if value <= 0:
            raise ValueError("Value must be positive")
        if basic_code_discount.discount_type == "PERCENTAGE" and value > 100:
            raise ValueError("Percentage discount cannot exceed 100")
    except (InvalidOperation, ValueError) as e:
        return DiscountCodeBasicCreatePayload(
            discount_node=None,
            user_errors=[UserError(field=["value"], message=str(e))],
        )

    # Check for duplicate code
    existing = session.exec(
        select(DiscountCode).where(DiscountCode.code == basic_code_discount.code)
    ).first()
    if existing:
        return DiscountCodeBasicCreatePayload(
            discount_node=None,
            user_errors=[UserError(field=["code"], message="Discount code already exists")],
        )

    # Parse optional datetime strings
    starts_at = None
    ends_at = None
    try:
        if basic_code_discount.starts_at:
            starts_at = datetime.fromisoformat(basic_code_discount.starts_at)
        if basic_code_discount.ends_at:
            ends_at = datetime.fromisoformat(basic_code_discount.ends_at)
    except ValueError as e:
        return DiscountCodeBasicCreatePayload(
            discount_node=None,
            user_errors=[UserError(field=["startsAt/endsAt"], message=f"Invalid datetime: {e}")],
        )

    minimum_req = None
    if basic_code_discount.minimum_subtotal:
        try:
            minimum_req = Decimal(basic_code_discount.minimum_subtotal)
        except InvalidOperation:
            pass

    discount = DiscountCode(
        id=f"gid://shopify/DiscountCode/{uuid.uuid4().hex[:12]}",
        code=basic_code_discount.code,
        discount_type=basic_code_discount.discount_type,
        value=value,
        usage_limit=basic_code_discount.usage_limit,
        applies_once_per_customer=basic_code_discount.applies_once_per_customer,
        minimum_requirement_amount=minimum_req,
        status="ACTIVE",
        starts_at=starts_at,
        ends_at=ends_at,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(discount)
    session.commit()
    session.refresh(discount)

    return DiscountCodeBasicCreatePayload(discount_node=_to_discount_node(discount), user_errors=[])


def resolve_discount_code_update(
    info: Info,
    id: str,
    code_discount: DiscountCodeUpdateInput,
) -> DiscountCodeUpdatePayload:
    try:
        check_scope("discountCodeUpdate", set(info.context.get("granted_scopes", [])))
    except ScopeError as e:
        return DiscountCodeUpdatePayload(discount_node=None, user_errors=[UserError(field=None, message=str(e))])

    session: Session = info.context["session"]
    discount = session.exec(select(DiscountCode).where(DiscountCode.id == id)).first()
    if not discount:
        return DiscountCodeUpdatePayload(
            discount_node=None,
            user_errors=[UserError(field=["id"], message="Discount code not found")],
        )

    if code_discount.code is not None:
        discount.code = code_discount.code
    if code_discount.usage_limit is not None:
        discount.usage_limit = code_discount.usage_limit
    if code_discount.ends_at is not None:
        try:
            discount.ends_at = datetime.fromisoformat(code_discount.ends_at)
        except ValueError as e:
            return DiscountCodeUpdatePayload(
                discount_node=None,
                user_errors=[UserError(field=["endsAt"], message=str(e))],
            )
    if code_discount.status is not None:
        if code_discount.status not in ("ACTIVE", "DISABLED", "EXPIRED"):
            return DiscountCodeUpdatePayload(
                discount_node=None,
                user_errors=[UserError(field=["status"], message="Invalid status")],
            )
        discount.status = code_discount.status

    discount.updated_at = datetime.utcnow()
    session.add(discount)
    session.commit()
    session.refresh(discount)

    return DiscountCodeUpdatePayload(discount_node=_to_discount_node(discount), user_errors=[])
