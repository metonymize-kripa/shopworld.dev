"""
Inventory queries: inventoryItems, inventoryLevels, locations.

Status:
  inventoryItem(id)              — TODO: implement
  inventoryItems(first, after)   — TODO: implement
  inventoryLevels(...)           — upgrade from flat list to Connection
  location(id)                   — TODO: implement
  locations(first, after)        — TODO: implement
"""

from __future__ import annotations

from typing import List, Optional

import strawberry
from sqlmodel import Session, select
from strawberry.types import Info

from shopworld.apps.shopify_admin.models import (
    InventoryItem,
    InventoryLevel,
    Location,
)
from shopworld.apps.shopify_admin.graphql_api.pagination import paginate, PageInfoType, encode_cursor
from shopworld.apps.shopify_admin.graphql_api.scopes import check_scope


# ---------------------------------------------------------------------------
# GQL types
# ---------------------------------------------------------------------------

@strawberry.type
class LocationType:
    id: str
    name: str
    address1: Optional[str]
    city: Optional[str]
    province: Optional[str]
    country: Optional[str]
    active: bool


@strawberry.type
class LocationEdge:
    node: LocationType
    cursor: str


@strawberry.type
class LocationConnection:
    edges: List[LocationEdge]
    page_info: PageInfoType


@strawberry.type
class InventoryItemType:
    id: str
    sku: Optional[str]
    tracked: bool
    country_code_of_origin: Optional[str]
    harmonized_system_code: Optional[str]


@strawberry.type
class InventoryItemEdge:
    node: InventoryItemType
    cursor: str


@strawberry.type
class InventoryItemConnection:
    edges: List[InventoryItemEdge]
    page_info: PageInfoType


@strawberry.type
class InventoryLevelType:
    id: int
    inventory_item_id: str
    location_id: str
    available: int
    incoming: int
    reserved: int
    committed: int
    damaged: int
    updated_at: str


@strawberry.type
class InventoryLevelEdge:
    node: InventoryLevelType
    cursor: str


@strawberry.type
class InventoryLevelConnection:
    edges: List[InventoryLevelEdge]
    page_info: PageInfoType


# ---------------------------------------------------------------------------
# Resolver helpers
# ---------------------------------------------------------------------------

def _to_location_type(loc: Location) -> LocationType:
    return LocationType(
        id=loc.id,
        name=loc.name,
        address1=loc.address1,
        city=loc.city,
        province=loc.province,
        country=loc.country,
        active=loc.active,
    )


def _to_inventory_item_type(item: InventoryItem) -> InventoryItemType:
    return InventoryItemType(
        id=item.id,
        sku=item.sku,
        tracked=item.tracked,
        country_code_of_origin=item.country_code_of_origin,
        harmonized_system_code=item.harmonized_system_code,
    )


def _to_inventory_level_type(lvl: InventoryLevel) -> InventoryLevelType:
    return InventoryLevelType(
        id=lvl.id,
        inventory_item_id=lvl.inventory_item_id,
        location_id=lvl.location_id,
        available=lvl.available,
        incoming=lvl.incoming,
        reserved=lvl.reserved,
        committed=lvl.committed,
        damaged=lvl.damaged,
        updated_at=lvl.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Query resolvers
# ---------------------------------------------------------------------------

def resolve_location(info: Info, id: str) -> Optional[LocationType]:
    check_scope("location", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]
    loc = session.exec(select(Location).where(Location.id == id)).first()
    return _to_location_type(loc) if loc else None


def resolve_locations(
    info: Info,
    first: int = 10,
    after: Optional[str] = None,
    include_legacy: bool = False,
) -> LocationConnection:
    check_scope("locations", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]

    stmt = select(Location)
    if not include_legacy:
        stmt = stmt.where(Location.active.is_(True))
    all_locs = session.exec(stmt).all()

    page, page_info = paginate(all_locs, first, after, table="locations")
    edges = [
        LocationEdge(node=_to_location_type(loc), cursor=encode_cursor("locations", loc.id))
        for loc in page
    ]
    return LocationConnection(
        edges=edges,
        page_info=PageInfoType(
            has_next_page=page_info.has_next_page,
            has_previous_page=page_info.has_previous_page,
            start_cursor=page_info.start_cursor,
            end_cursor=page_info.end_cursor,
        ),
    )


def resolve_inventory_item(info: Info, id: str) -> Optional[InventoryItemType]:
    check_scope("inventoryItem", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]
    item = session.exec(select(InventoryItem).where(InventoryItem.id == id)).first()
    return _to_inventory_item_type(item) if item else None


def resolve_inventory_items(
    info: Info,
    first: int = 10,
    after: Optional[str] = None,
    query: Optional[str] = None,
) -> InventoryItemConnection:
    check_scope("inventoryItems", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]

    stmt = select(InventoryItem)
    if query:
        stmt = stmt.where(InventoryItem.sku.contains(query))
    all_items = session.exec(stmt).all()

    page, page_info = paginate(all_items, first, after, table="inventory_items")
    edges = [
        InventoryItemEdge(
            node=_to_inventory_item_type(item),
            cursor=encode_cursor("inventory_items", item.id),
        )
        for item in page
    ]
    return InventoryItemConnection(
        edges=edges,
        page_info=PageInfoType(
            has_next_page=page_info.has_next_page,
            has_previous_page=page_info.has_previous_page,
            start_cursor=page_info.start_cursor,
            end_cursor=page_info.end_cursor,
        ),
    )


def resolve_inventory_levels(
    info: Info,
    first: int = 10,
    after: Optional[str] = None,
    location_ids: Optional[List[str]] = None,
    inventory_item_ids: Optional[List[str]] = None,
) -> InventoryLevelConnection:
    check_scope("inventoryLevels", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]

    stmt = select(InventoryLevel)
    if location_ids:
        stmt = stmt.where(InventoryLevel.location_id.in_(location_ids))
    if inventory_item_ids:
        stmt = stmt.where(InventoryLevel.inventory_item_id.in_(inventory_item_ids))
    all_levels = session.exec(stmt).all()

    page, page_info = paginate(all_levels, first, after, table="inventory_levels", id_attr="id")
    edges = [
        InventoryLevelEdge(
            node=_to_inventory_level_type(lvl),
            cursor=encode_cursor("inventory_levels", lvl.id),
        )
        for lvl in page
    ]
    return InventoryLevelConnection(
        edges=edges,
        page_info=PageInfoType(
            has_next_page=page_info.has_next_page,
            has_previous_page=page_info.has_previous_page,
            start_cursor=page_info.start_cursor,
            end_cursor=page_info.end_cursor,
        ),
    )
