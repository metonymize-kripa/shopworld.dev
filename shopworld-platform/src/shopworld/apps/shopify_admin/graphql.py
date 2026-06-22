"""Removed: legacy single-file Shopify Admin GraphQL implementation.

The canonical GraphQL API is ``shopworld.apps.shopify_admin.graphql_api``
(``build_schema()`` / ``ShopWorldGraphQLV2``). The old duplicate schema that
lived here has been removed to eliminate two competing implementations
(see platform-rnd code review, issue C4). Importing the old symbols now raises
with a clear pointer instead of silently shadowing the canonical layer.
"""

from __future__ import annotations


def __getattr__(name: str):  # PEP 562 module-level attribute hook
    raise ImportError(
        f"shopworld.apps.shopify_admin.graphql.{name} was removed. "
        "Import from shopworld.apps.shopify_admin.graphql_api instead "
        "(build_schema / ShopWorldGraphQLV2)."
    )
