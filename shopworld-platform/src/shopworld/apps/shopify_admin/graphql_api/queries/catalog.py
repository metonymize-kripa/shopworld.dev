"""
Catalog queries: products, productVariants, collections.

Status:
  products(first, after, query)  — TODO: upgrade to Connection type
  productVariants(first, after)  — TODO: implement
  collection(id)                 — TODO: implement
  collections(first, after)      — TODO: implement
"""

from __future__ import annotations

from typing import List, Optional

import strawberry
from sqlmodel import Session, select
from strawberry.types import Info

from shopworld.apps.shopify_admin.models import (
    Collection,
    CollectionProductLink,
    Product,
    ProductVariant,
)
from shopworld.apps.shopify_admin.graphql_api.pagination import paginate, PageInfoType, encode_cursor
from shopworld.apps.shopify_admin.graphql_api.scopes import check_scope


# ---------------------------------------------------------------------------
# GQL types
# ---------------------------------------------------------------------------

@strawberry.type
class ProductVariantType:
    id: str
    product_id: str
    sku: Optional[str]
    barcode: Optional[str]
    price: str
    compare_at_price: Optional[str]
    option1: Optional[str]
    option2: Optional[str]
    option3: Optional[str]
    inventory_quantity: int
    requires_shipping: bool
    taxable: bool


@strawberry.type
class ProductVariantEdge:
    node: ProductVariantType
    cursor: str


@strawberry.type
class ProductVariantConnection:
    edges: List[ProductVariantEdge]
    page_info: PageInfoType


@strawberry.type
class ProductType:
    id: str
    title: str
    handle: str
    description: Optional[str]
    product_type: Optional[str]
    vendor: Optional[str]
    status: str
    tags: List[str]
    created_at: str
    updated_at: str


@strawberry.type
class ProductEdge:
    node: ProductType
    cursor: str


@strawberry.type
class ProductConnection:
    edges: List[ProductEdge]
    page_info: PageInfoType


@strawberry.type
class CollectionType:
    id: str
    title: str
    handle: str
    description: Optional[str]
    collection_type: str
    sort_order: str
    updated_at: str


@strawberry.type
class CollectionEdge:
    node: CollectionType
    cursor: str


@strawberry.type
class CollectionConnection:
    edges: List[CollectionEdge]
    page_info: PageInfoType


# ---------------------------------------------------------------------------
# Resolver helpers
# ---------------------------------------------------------------------------

def _to_product_type(p: Product) -> ProductType:
    return ProductType(
        id=p.id,
        title=p.title,
        handle=p.handle,
        description=p.description,
        product_type=p.product_type,
        vendor=p.vendor,
        status=p.status,
        tags=list(p.tags or []),
        created_at=p.created_at.isoformat(),
        updated_at=p.updated_at.isoformat(),
    )


def _to_variant_type(v: ProductVariant) -> ProductVariantType:
    return ProductVariantType(
        id=v.id,
        product_id=v.product_id,
        sku=v.sku,
        barcode=v.barcode,
        price=str(v.price),
        compare_at_price=str(v.compare_at_price) if v.compare_at_price else None,
        option1=v.option1,
        option2=v.option2,
        option3=v.option3,
        inventory_quantity=0,  # TODO: sum from InventoryLevel
        requires_shipping=v.requires_shipping,
        taxable=v.taxable,
    )


def _to_collection_type(c: Collection) -> CollectionType:
    return CollectionType(
        id=c.id,
        title=c.title,
        handle=c.handle,
        description=c.description,
        collection_type=c.collection_type,
        sort_order=c.sort_order,
        updated_at=c.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Query resolvers (to be mixed into Query root)
# ---------------------------------------------------------------------------

def resolve_product(info: Info, id: str) -> Optional[ProductType]:
    check_scope("product", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]
    p = session.exec(select(Product).where(Product.id == id)).first()
    return _to_product_type(p) if p else None


def resolve_products(
    info: Info,
    first: int = 10,
    after: Optional[str] = None,
    query: Optional[str] = None,
) -> ProductConnection:
    check_scope("products", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]

    stmt = select(Product)
    if query:
        stmt = stmt.where(Product.title.contains(query))
    all_products = session.exec(stmt).all()

    page, page_info = paginate(all_products, first, after, table="products")

    edges = [
        ProductEdge(node=_to_product_type(p), cursor=encode_cursor("products", p.id))
        for p in page
    ]
    return ProductConnection(
        edges=edges,
        page_info=PageInfoType(
            has_next_page=page_info.has_next_page,
            has_previous_page=page_info.has_previous_page,
            start_cursor=page_info.start_cursor,
            end_cursor=page_info.end_cursor,
        ),
    )


def resolve_product_variants(
    info: Info,
    product_id: Optional[str] = None,
    first: int = 10,
    after: Optional[str] = None,
) -> ProductVariantConnection:
    check_scope("productVariants", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]

    stmt = select(ProductVariant)
    if product_id:
        stmt = stmt.where(ProductVariant.product_id == product_id)
    all_variants = session.exec(stmt).all()

    page, page_info = paginate(all_variants, first, after, table="product_variants")

    edges = [
        ProductVariantEdge(
            node=_to_variant_type(v),
            cursor=encode_cursor("product_variants", v.id),
        )
        for v in page
    ]
    return ProductVariantConnection(
        edges=edges,
        page_info=PageInfoType(
            has_next_page=page_info.has_next_page,
            has_previous_page=page_info.has_previous_page,
            start_cursor=page_info.start_cursor,
            end_cursor=page_info.end_cursor,
        ),
    )


def resolve_collection(info: Info, id: str) -> Optional[CollectionType]:
    check_scope("collection", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]
    c = session.exec(select(Collection).where(Collection.id == id)).first()
    return _to_collection_type(c) if c else None


def resolve_collections(
    info: Info,
    first: int = 10,
    after: Optional[str] = None,
) -> CollectionConnection:
    check_scope("collections", set(info.context.get("granted_scopes", [])))
    session: Session = info.context["session"]

    all_collections = session.exec(select(Collection)).all()
    page, page_info = paginate(all_collections, first, after, table="collections")

    edges = [
        CollectionEdge(
            node=_to_collection_type(c),
            cursor=encode_cursor("collections", c.id),
        )
        for c in page
    ]
    return CollectionConnection(
        edges=edges,
        page_info=PageInfoType(
            has_next_page=page_info.has_next_page,
            has_previous_page=page_info.has_previous_page,
            start_cursor=page_info.start_cursor,
            end_cursor=page_info.end_cursor,
        ),
    )
