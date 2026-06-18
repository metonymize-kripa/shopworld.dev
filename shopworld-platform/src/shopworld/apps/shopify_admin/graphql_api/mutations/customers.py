"""
Customer mutations: customerCreate, customerUpdate, tagsAdd, tagsRemove.

tagsAdd / tagsRemove are polymorphic in the real Shopify API (they accept
any resource GID).  Here we implement them for Products, Orders, and
Customers — the three most common tag targets in operational workflows.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import List, Optional

import strawberry
from sqlmodel import Session, select
from strawberry.types import Info

from shopworld.apps.shopify_admin.models import Customer, Order, Product
from shopworld.apps.shopify_admin.graphql_api.scopes import check_scope, ScopeError
from shopworld.apps.shopify_admin.graphql_api.queries.customers import CustomerType, _to_customer_type
from shopworld.apps.shopify_admin.graphql_api.mutations.catalog import UserError


# ---------------------------------------------------------------------------
# Input types
# ---------------------------------------------------------------------------

@strawberry.input
class CustomerCreateInput:
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None


@strawberry.input
class CustomerUpdateInput:
    id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None
    state: Optional[str] = None


# ---------------------------------------------------------------------------
# Payload types
# ---------------------------------------------------------------------------

@strawberry.type
class CustomerCreatePayload:
    customer: Optional[CustomerType]
    user_errors: List[UserError]


@strawberry.type
class CustomerUpdatePayload:
    customer: Optional[CustomerType]
    user_errors: List[UserError]


@strawberry.type
class TagsAddPayload:
    node_id: Optional[str]
    tags: List[str]
    user_errors: List[UserError]


@strawberry.type
class TagsRemovePayload:
    node_id: Optional[str]
    tags: List[str]
    user_errors: List[UserError]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_customer_gid() -> str:
    return f"gid://shopify/Customer/{uuid.uuid4().hex[:12]}"


def _get_tags_owner(session: Session, node_id: str):
    """Return the ORM object for a taggable GID, or None."""
    if "/Product/" in node_id:
        return session.exec(select(Product).where(Product.id == node_id)).first()
    if "/Order/" in node_id:
        return session.exec(select(Order).where(Order.id == node_id)).first()
    if "/Customer/" in node_id:
        return session.exec(select(Customer).where(Customer.id == node_id)).first()
    return None


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------

def resolve_customer_create(
    info: Info,
    input: CustomerCreateInput,
) -> CustomerCreatePayload:
    try:
        check_scope("customerCreate", set(info.context.get("granted_scopes", [])))
    except ScopeError as e:
        return CustomerCreatePayload(customer=None, user_errors=[UserError(field=None, message=str(e))])

    session: Session = info.context["session"]

    if input.email:
        existing = session.exec(select(Customer).where(Customer.email == input.email)).first()
        if existing:
            return CustomerCreatePayload(
                customer=None,
                user_errors=[UserError(field=["email"], message="Email already exists")],
            )

    customer = Customer(
        id=_new_customer_gid(),
        email=input.email,
        phone=input.phone,
        first_name=input.first_name,
        last_name=input.last_name,
        tags=input.tags or [],
        note=input.note,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(customer)
    session.commit()
    session.refresh(customer)

    return CustomerCreatePayload(customer=_to_customer_type(customer), user_errors=[])


def resolve_customer_update(
    info: Info,
    input: CustomerUpdateInput,
) -> CustomerUpdatePayload:
    try:
        check_scope("customerUpdate", set(info.context.get("granted_scopes", [])))
    except ScopeError as e:
        return CustomerUpdatePayload(customer=None, user_errors=[UserError(field=None, message=str(e))])

    session: Session = info.context["session"]
    customer = session.exec(select(Customer).where(Customer.id == input.id)).first()
    if not customer:
        return CustomerUpdatePayload(
            customer=None,
            user_errors=[UserError(field=["id"], message="Customer not found")],
        )

    if input.email is not None:
        customer.email = input.email
    if input.phone is not None:
        customer.phone = input.phone
    if input.first_name is not None:
        customer.first_name = input.first_name
    if input.last_name is not None:
        customer.last_name = input.last_name
    if input.tags is not None:
        customer.tags = input.tags
    if input.note is not None:
        customer.note = input.note
    if input.state is not None:
        valid_states = ("ENABLED", "DISABLED", "INVITED", "DECLINED")
        if input.state not in valid_states:
            return CustomerUpdatePayload(
                customer=None,
                user_errors=[UserError(field=["state"], message=f"Invalid state. Must be one of {valid_states}")],
            )
        customer.state = input.state

    customer.updated_at = datetime.now(UTC)
    session.add(customer)
    session.commit()
    session.refresh(customer)

    return CustomerUpdatePayload(customer=_to_customer_type(customer), user_errors=[])


def resolve_tags_add(
    info: Info,
    id: str,
    tags: List[str],
) -> TagsAddPayload:
    try:
        check_scope("tagsAdd", set(info.context.get("granted_scopes", [])))
    except ScopeError as e:
        return TagsAddPayload(node_id=None, tags=[], user_errors=[UserError(field=None, message=str(e))])

    session: Session = info.context["session"]
    obj = _get_tags_owner(session, id)
    if obj is None:
        return TagsAddPayload(
            node_id=None,
            tags=[],
            user_errors=[UserError(field=["id"], message="Resource not found or not taggable")],
        )

    existing = list(obj.tags or [])
    new_tags = [t for t in tags if t not in existing]
    obj.tags = existing + new_tags
    obj.updated_at = datetime.now(UTC)
    session.add(obj)
    session.commit()

    return TagsAddPayload(node_id=id, tags=list(obj.tags), user_errors=[])


def resolve_tags_remove(
    info: Info,
    id: str,
    tags: List[str],
) -> TagsRemovePayload:
    try:
        check_scope("tagsRemove", set(info.context.get("granted_scopes", [])))
    except ScopeError as e:
        return TagsRemovePayload(node_id=None, tags=[], user_errors=[UserError(field=None, message=str(e))])

    session: Session = info.context["session"]
    obj = _get_tags_owner(session, id)
    if obj is None:
        return TagsRemovePayload(
            node_id=None,
            tags=[],
            user_errors=[UserError(field=["id"], message="Resource not found or not taggable")],
        )

    obj.tags = [t for t in (obj.tags or []) if t not in tags]
    obj.updated_at = datetime.now(UTC)
    session.add(obj)
    session.commit()

    return TagsRemovePayload(node_id=id, tags=list(obj.tags), user_errors=[])
