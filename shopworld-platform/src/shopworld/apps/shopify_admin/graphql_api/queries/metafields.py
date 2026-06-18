"""
Metafield queries: metafields(owner_type, owner_id, ...).

Shopify exposes metafields as a sub-connection on every resource node.
Here we provide a top-level query for convenience and to support agents
that query metafields directly.

metaobjects — stub only; deferred to post-MVP.
"""

from __future__ import annotations

from typing import List, Optional

import strawberry
from sqlmodel import Session, select
from strawberry.types import Info

from shopworld.apps.shopify_admin.models import Metafield
from shopworld.apps.shopify_admin.graphql_api.pagination import paginate, PageInfoType, encode_cursor
from shopworld.apps.shopify_admin.graphql_api.scopes import check_scope


@strawberry.type
class MetafieldType:
    id: str
    namespace: str
    key: str
    value: str
    type: str
    owner_type: str
    owner_id: str
    created_at: str
    updated_at: str


@strawberry.type
class MetafieldEdge:
    node: MetafieldType
    cursor: str


@strawberry.type
class MetafieldConnection:
    edges: List[MetafieldEdge]
    page_info: PageInfoType


def _to_metafield_type(m: Metafield) -> MetafieldType:
    return MetafieldType(
        id=m.id,
        namespace=m.namespace,
        key=m.key,
        value=m.value,
        type=m.type,
        owner_type=m.owner_type,
        owner_id=m.owner_id,
        created_at=m.created_at.isoformat(),
        updated_at=m.updated_at.isoformat(),
    )


def resolve_metafields(
    info: Info,
    owner_type: Optional[str] = None,
    owner_id: Optional[str] = None,
    namespace: Optional[str] = None,
    first: int = 10,
    after: Optional[str] = None,
) -> MetafieldConnection:
    check_scope("metafields", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]

    stmt = select(Metafield)
    if owner_type:
        stmt = stmt.where(Metafield.owner_type == owner_type)
    if owner_id:
        stmt = stmt.where(Metafield.owner_id == owner_id)
    if namespace:
        stmt = stmt.where(Metafield.namespace == namespace)

    all_metafields = session.exec(stmt).all()
    page, page_info = paginate(all_metafields, first, after, table="metafields")
    edges = [
        MetafieldEdge(
            node=_to_metafield_type(m),
            cursor=encode_cursor("metafields", m.id),
        )
        for m in page
    ]
    return MetafieldConnection(
        edges=edges,
        page_info=PageInfoType(
            has_next_page=page_info.has_next_page,
            has_previous_page=page_info.has_previous_page,
            start_cursor=page_info.start_cursor,
            end_cursor=page_info.end_cursor,
        ),
    )
