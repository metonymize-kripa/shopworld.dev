"""
Discount queries: discountNodes(first, after, query).

Shopify wraps all discount types under a polymorphic DiscountNode.
In ShopWorld we simplify to a single DiscountCodeNode type since we
only model basic code discounts in Phase 2.
"""

from __future__ import annotations

from typing import List, Optional

import strawberry
from sqlmodel import Session, select
from strawberry.types import Info

from shopworld.apps.shopify_admin.models import DiscountCode
from shopworld.apps.shopify_admin.graphql_api.pagination import paginate, PageInfoType, encode_cursor
from shopworld.apps.shopify_admin.graphql_api.scopes import check_scope


@strawberry.type
class DiscountNodeType:
    id: str
    code: str
    discount_type: str
    value: str
    status: str
    usage_limit: Optional[int]
    applies_once_per_customer: bool
    starts_at: Optional[str]
    ends_at: Optional[str]
    created_at: str


@strawberry.type
class DiscountNodeEdge:
    node: DiscountNodeType
    cursor: str


@strawberry.type
class DiscountNodeConnection:
    edges: List[DiscountNodeEdge]
    page_info: PageInfoType


def _to_discount_node(d: DiscountCode) -> DiscountNodeType:
    return DiscountNodeType(
        id=d.id,
        code=d.code,
        discount_type=d.discount_type,
        value=str(d.value),
        status=d.status,
        usage_limit=d.usage_limit,
        applies_once_per_customer=d.applies_once_per_customer,
        starts_at=d.starts_at.isoformat() if d.starts_at else None,
        ends_at=d.ends_at.isoformat() if d.ends_at else None,
        created_at=d.created_at.isoformat(),
    )


def resolve_discount_nodes(
    info: Info,
    first: int = 10,
    after: Optional[str] = None,
    query: Optional[str] = None,
) -> DiscountNodeConnection:
    check_scope("discountNodes", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]

    stmt = select(DiscountCode)
    if query:
        stmt = stmt.where(DiscountCode.code.contains(query))
    all_discounts = session.exec(stmt).all()

    page, page_info = paginate(all_discounts, first, after, table="discount_codes")
    edges = [
        DiscountNodeEdge(
            node=_to_discount_node(d),
            cursor=encode_cursor("discount_codes", d.id),
        )
        for d in page
    ]
    return DiscountNodeConnection(
        edges=edges,
        page_info=PageInfoType(
            has_next_page=page_info.has_next_page,
            has_previous_page=page_info.has_previous_page,
            start_cursor=page_info.start_cursor,
            end_cursor=page_info.end_cursor,
        ),
    )
