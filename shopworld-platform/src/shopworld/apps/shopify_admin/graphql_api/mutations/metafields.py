"""
Metafield mutations: metafieldsSet (upsert one or more metafields).

Shopify's metafieldsSet accepts up to 25 metafields in one call (250 with bulk).
Each entry identifies the owner by ownerType + ownerId, namespace, and key.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import List, Optional

import strawberry
from sqlmodel import Session, select
from strawberry.types import Info

from shopworld.apps.shopify_admin.models import Metafield
from shopworld.apps.shopify_admin.graphql_api.scopes import check_scope, ScopeError
from shopworld.apps.shopify_admin.graphql_api.queries.metafields import MetafieldType, _to_metafield_type
from shopworld.apps.shopify_admin.graphql_api.mutations.catalog import UserError


MAX_METAFIELDS_PER_CALL = 25


@strawberry.input
class MetafieldSetInput:
    owner_type: str      # "product", "customer", "order", etc.
    owner_id: str        # GID of the owning resource
    namespace: str
    key: str
    value: str
    type: str = "single_line_text_field"


@strawberry.type
class MetafieldsSetPayload:
    metafields: List[MetafieldType]
    user_errors: List[UserError]


def resolve_metafields_set(
    info: Info,
    metafields: List[MetafieldSetInput],
) -> MetafieldsSetPayload:
    try:
        check_scope("metafieldsSet", set(info.context.get("granted_scopes", [])))
    except ScopeError as e:
        return MetafieldsSetPayload(metafields=[], user_errors=[UserError(field=None, message=str(e))])

    if len(metafields) > MAX_METAFIELDS_PER_CALL:
        return MetafieldsSetPayload(
            metafields=[],
            user_errors=[
                UserError(
                    field=None,
                    message=f"Too many metafields. Maximum {MAX_METAFIELDS_PER_CALL} per call.",
                )
            ],
        )

    session: Session = info.context["session"]
    results: List[MetafieldType] = []

    for mf_input in metafields:
        existing = session.exec(
            select(Metafield).where(
                (Metafield.owner_type == mf_input.owner_type) &
                (Metafield.owner_id == mf_input.owner_id) &
                (Metafield.namespace == mf_input.namespace) &
                (Metafield.key == mf_input.key)
            )
        ).first()

        if existing:
            existing.value = mf_input.value
            existing.type = mf_input.type
            existing.updated_at = datetime.now(UTC)
            session.add(existing)
            session.flush()
            results.append(_to_metafield_type(existing))
        else:
            new_mf = Metafield(
                id=f"gid://shopify/Metafield/{uuid.uuid4().hex[:12]}",
                namespace=mf_input.namespace,
                key=mf_input.key,
                value=mf_input.value,
                type=mf_input.type,
                owner_type=mf_input.owner_type,
                owner_id=mf_input.owner_id,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(new_mf)
            session.flush()
            results.append(_to_metafield_type(new_mf))

    session.commit()
    return MetafieldsSetPayload(metafields=results, user_errors=[])
