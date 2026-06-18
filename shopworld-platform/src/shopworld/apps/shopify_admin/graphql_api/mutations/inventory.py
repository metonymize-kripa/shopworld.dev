"""
Inventory mutations: inventoryAdjustQuantities, inventoryItemUpdate.

inventoryAdjustQuantities uses the "delta" style (add/subtract from available).
inventoryItemUpdate updates InventoryItem metadata (tracked, cost, HScode, etc.).
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import List, Optional

import strawberry
from sqlmodel import Session, select
from strawberry.types import Info

from shopworld.apps.shopify_admin.models import InventoryItem, InventoryLevel
from shopworld.apps.shopify_admin.graphql_api.scopes import check_scope, ScopeError
from shopworld.apps.shopify_admin.graphql_api.queries.inventory import (
    InventoryItemType,
    InventoryLevelType,
    _to_inventory_item_type,
    _to_inventory_level_type,
)
from shopworld.apps.shopify_admin.graphql_api.mutations.catalog import UserError


# ---------------------------------------------------------------------------
# Input types
# ---------------------------------------------------------------------------

@strawberry.input
class InventoryAdjustQuantityInput:
    inventory_item_id: str
    location_id: str
    delta: int
    reason: Optional[str] = None    # e.g. "correction", "received", "damaged"


@strawberry.input
class InventoryItemUpdateInput:
    id: str
    tracked: Optional[bool] = None
    country_code_of_origin: Optional[str] = None
    harmonized_system_code: Optional[str] = None
    province_code_of_origin: Optional[str] = None


# ---------------------------------------------------------------------------
# Payload types
# ---------------------------------------------------------------------------

@strawberry.type
class InventoryAdjustQuantitiesPayload:
    inventory_adjustment_group: Optional[List[InventoryLevelType]]
    user_errors: List[UserError]


@strawberry.type
class InventoryItemUpdatePayload:
    inventory_item: Optional[InventoryItemType]
    user_errors: List[UserError]


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------

def resolve_inventory_adjust_quantities(
    info: Info,
    input: List[InventoryAdjustQuantityInput],
) -> InventoryAdjustQuantitiesPayload:
    try:
        check_scope("inventoryAdjustQuantities", set(info.context.get("granted_scopes", [])))
    except ScopeError as e:
        return InventoryAdjustQuantitiesPayload(
            inventory_adjustment_group=None,
            user_errors=[UserError(field=None, message=str(e))],
        )

    if len(input) > 250:
        return InventoryAdjustQuantitiesPayload(
            inventory_adjustment_group=None,
            user_errors=[UserError(field=None, message="Maximum 250 adjustments per call")],
        )

    session: Session = info.context["session"]
    adjusted: List[InventoryLevelType] = []

    for adj in input:
        level = session.exec(
            select(InventoryLevel).where(
                (InventoryLevel.inventory_item_id == adj.inventory_item_id) &
                (InventoryLevel.location_id == adj.location_id)
            )
        ).first()

        if not level:
            return InventoryAdjustQuantitiesPayload(
                inventory_adjustment_group=None,
                user_errors=[
                    UserError(
                        field=["inventoryItemId", "locationId"],
                        message=f"InventoryLevel not found for item {adj.inventory_item_id} at {adj.location_id}",
                    )
                ],
            )

        new_qty = level.available + adj.delta
        if new_qty < 0:
            return InventoryAdjustQuantitiesPayload(
                inventory_adjustment_group=None,
                user_errors=[
                    UserError(
                        field=["delta"],
                        message=f"Adjustment would result in negative inventory ({new_qty})",
                    )
                ],
            )

        level.available = new_qty
        level.updated_at = datetime.now(UTC)
        session.add(level)
        adjusted.append(_to_inventory_level_type(level))

    session.commit()
    return InventoryAdjustQuantitiesPayload(inventory_adjustment_group=adjusted, user_errors=[])


def resolve_inventory_item_update(
    info: Info,
    id: str,
    input: InventoryItemUpdateInput,
) -> InventoryItemUpdatePayload:
    try:
        check_scope("inventoryItemUpdate", set(info.context.get("granted_scopes", [])))
    except ScopeError as e:
        return InventoryItemUpdatePayload(inventory_item=None, user_errors=[UserError(field=None, message=str(e))])

    session: Session = info.context["session"]
    item = session.exec(select(InventoryItem).where(InventoryItem.id == id)).first()
    if not item:
        return InventoryItemUpdatePayload(
            inventory_item=None,
            user_errors=[UserError(field=["id"], message="InventoryItem not found")],
        )

    if input.tracked is not None:
        item.tracked = input.tracked
    if input.country_code_of_origin is not None:
        item.country_code_of_origin = input.country_code_of_origin
    if input.harmonized_system_code is not None:
        item.harmonized_system_code = input.harmonized_system_code
    if input.province_code_of_origin is not None:
        item.province_code_of_origin = input.province_code_of_origin

    session.add(item)
    session.commit()
    session.refresh(item)

    return InventoryItemUpdatePayload(inventory_item=_to_inventory_item_type(item), user_errors=[])
