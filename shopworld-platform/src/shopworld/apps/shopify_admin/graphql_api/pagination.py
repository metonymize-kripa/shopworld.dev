"""
Shopify-style cursor-based pagination helpers.

Shopify Admin GraphQL uses the Relay Connection spec:
  { edges { node { ... } cursor } pageInfo { hasNextPage endCursor } }

All query resolvers that return lists should return a Connection type
rather than a plain List so agents develop the correct pagination habits.

Cursor encoding: base64(tablename:id) — matches Shopify's opaque cursor
convention closely enough for simulator purposes.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Generic, List, Optional, TypeVar

import strawberry

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Cursor helpers
# ---------------------------------------------------------------------------

def encode_cursor(table: str, row_id: str | int) -> str:
    """Encode an opaque cursor from a table name and row identifier."""
    raw = f"{table}:{row_id}"
    return base64.b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[str, str]:
    """Decode cursor → (table, row_id). Raises ValueError on bad input."""
    try:
        raw = base64.b64decode(cursor.encode()).decode()
        table, row_id = raw.split(":", 1)
        return table, row_id
    except Exception as exc:
        raise ValueError(f"Invalid cursor: {cursor!r}") from exc


# ---------------------------------------------------------------------------
# Generic Strawberry connection types
#
# Strawberry does not support generic types directly in schema generation, so
# concrete subtypes must be declared per-resource.  This module provides the
# dataclass building blocks; each query module declares its own concrete types
# by subclassing or repeating the pattern.
# ---------------------------------------------------------------------------

@dataclass
class PageInfo:
    has_next_page: bool
    has_previous_page: bool
    start_cursor: Optional[str]
    end_cursor: Optional[str]


@strawberry.type
class PageInfoType:
    has_next_page: bool
    has_previous_page: bool
    start_cursor: Optional[str]
    end_cursor: Optional[str]


@dataclass
class EdgeBase(Generic[T]):
    node: T
    cursor: str


@dataclass
class ConnectionBase(Generic[T]):
    edges: List[EdgeBase[T]]
    page_info: PageInfo

    @property
    def nodes(self) -> List[T]:
        return [e.node for e in self.edges]


# ---------------------------------------------------------------------------
# Pagination helper
# ---------------------------------------------------------------------------

def paginate(
    items: List,
    first: Optional[int],
    after: Optional[str],
    table: str,
    id_attr: str = "id",
) -> tuple[List, PageInfo]:
    """
    Apply cursor-based forward pagination to a pre-fetched list.

    Returns (page_items, page_info).

    Args:
        items:    Full ordered list of ORM objects.
        first:    Maximum items to return (Shopify cap: 250).
        after:    Opaque cursor; items after this cursor are returned.
        table:    Table name used to encode cursors.
        id_attr:  Attribute on each item used as the row identifier.
    """
    limit = min(first or 10, 250)

    start_index = 0
    if after:
        _, after_id = decode_cursor(after)
        for i, item in enumerate(items):
            if str(getattr(item, id_attr)) == after_id:
                start_index = i + 1
                break

    page = items[start_index : start_index + limit]
    has_next = (start_index + limit) < len(items)
    has_prev = start_index > 0

    start_cursor = encode_cursor(table, getattr(page[0], id_attr)) if page else None
    end_cursor = encode_cursor(table, getattr(page[-1], id_attr)) if page else None

    return page, PageInfo(
        has_next_page=has_next,
        has_previous_page=has_prev,
        start_cursor=start_cursor,
        end_cursor=end_cursor,
    )
