"""
Customer queries: customer(id), customers(first, after, query).
"""

from __future__ import annotations

from typing import List, Optional

import strawberry
from sqlmodel import Session, select
from strawberry.types import Info

from shopworld.apps.shopify_admin.models import Customer
from shopworld.apps.shopify_admin.graphql_api.pagination import paginate, PageInfoType, encode_cursor
from shopworld.apps.shopify_admin.graphql_api.scopes import check_scope


@strawberry.type
class CustomerType:
    id: str
    email: Optional[str]
    phone: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    state: str
    verified_email: bool
    orders_count: int
    total_spent: str
    tags: List[str]
    note: Optional[str]
    created_at: str
    updated_at: str


@strawberry.type
class CustomerEdge:
    node: CustomerType
    cursor: str


@strawberry.type
class CustomerConnection:
    edges: List[CustomerEdge]
    page_info: PageInfoType


def _to_customer_type(c: Customer) -> CustomerType:
    return CustomerType(
        id=c.id,
        email=c.email,
        phone=c.phone,
        first_name=c.first_name,
        last_name=c.last_name,
        state=c.state,
        verified_email=c.verified_email,
        orders_count=c.orders_count,
        total_spent=str(c.total_spent),
        tags=list(c.tags or []),
        note=c.note,
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )


def resolve_customer(info: Info, id: str) -> Optional[CustomerType]:
    check_scope("customer", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]
    c = session.exec(select(Customer).where(Customer.id == id)).first()
    return _to_customer_type(c) if c else None


def resolve_customers(
    info: Info,
    first: int = 10,
    after: Optional[str] = None,
    query: Optional[str] = None,
) -> CustomerConnection:
    check_scope("customers", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]

    stmt = select(Customer)
    if query:
        stmt = stmt.where(
            (Customer.email.contains(query)) |
            (Customer.first_name.contains(query)) |
            (Customer.last_name.contains(query))
        )
    all_customers = session.exec(stmt).all()

    page, page_info = paginate(all_customers, first, after, table="customers")
    edges = [
        CustomerEdge(node=_to_customer_type(c), cursor=encode_cursor("customers", c.id))
        for c in page
    ]
    return CustomerConnection(
        edges=edges,
        page_info=PageInfoType(
            has_next_page=page_info.has_next_page,
            has_previous_page=page_info.has_previous_page,
            start_cursor=page_info.start_cursor,
            end_cursor=page_info.end_cursor,
        ),
    )
