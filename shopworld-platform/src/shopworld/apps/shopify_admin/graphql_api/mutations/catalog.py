"""
Catalog mutations: productCreate, productUpdate, productSet, productVariantUpdate.

All mutations return Shopify-style payloads with a `userErrors` array.
Scope enforcement is checked before any DB write.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import List, Optional

import strawberry
from sqlmodel import Session, select
from strawberry.types import Info

from shopworld.apps.shopify_admin.models import Product, ProductVariant
from shopworld.apps.shopify_admin.graphql_api.scopes import check_scope, ScopeError
from shopworld.apps.shopify_admin.graphql_api.queries.catalog import ProductType, ProductVariantType, _to_product_type, _to_variant_type


# ---------------------------------------------------------------------------
# Input types
# ---------------------------------------------------------------------------

@strawberry.input
class ProductCreateInput:
    title: str
    handle: Optional[str] = None
    description: Optional[str] = None
    product_type: Optional[str] = None
    vendor: Optional[str] = None
    status: str = "ACTIVE"
    tags: Optional[List[str]] = None


@strawberry.input
class ProductUpdateInput:
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    vendor: Optional[str] = None
    product_type: Optional[str] = None


@strawberry.input
class ProductVariantUpdateInput:
    id: str
    price: Optional[str] = None
    compare_at_price: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    option1: Optional[str] = None
    option2: Optional[str] = None
    option3: Optional[str] = None
    taxable: Optional[bool] = None
    requires_shipping: Optional[bool] = None


# ---------------------------------------------------------------------------
# Payload types
# ---------------------------------------------------------------------------

@strawberry.type
class UserError:
    field: Optional[List[str]]
    message: str


@strawberry.type
class ProductCreatePayload:
    product: Optional[ProductType]
    user_errors: List[UserError]


@strawberry.type
class ProductUpdatePayload:
    product: Optional[ProductType]
    user_errors: List[UserError]


@strawberry.type
class ProductVariantUpdatePayload:
    product_variant: Optional[ProductVariantType]
    user_errors: List[UserError]


# ---------------------------------------------------------------------------
# Mutation resolvers
# ---------------------------------------------------------------------------

def _new_gid(resource: str) -> str:
    return f"gid://shopify/{resource}/{uuid.uuid4().hex[:12]}"


def resolve_product_create(
    info: Info,
    input: ProductCreateInput,
) -> ProductCreatePayload:
    try:
        check_scope("productCreate", set(info.context.get("granted_scopes", [])))
    except ScopeError as e:
        return ProductCreatePayload(product=None, user_errors=[UserError(field=None, message=str(e))])

    session: Session = info.context["session"]

    handle = (input.handle or input.title.lower().replace(" ", "-"))

    product = Product(
        id=_new_gid("Product"),
        title=input.title,
        handle=handle,
        description=input.description,
        product_type=input.product_type,
        vendor=input.vendor,
        status=input.status,
        tags=input.tags or [],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    return ProductCreatePayload(product=_to_product_type(product), user_errors=[])


def resolve_product_update(
    info: Info,
    input: ProductUpdateInput,
) -> ProductUpdatePayload:
    try:
        check_scope("productUpdate", set(info.context.get("granted_scopes", [])))
    except ScopeError as e:
        return ProductUpdatePayload(product=None, user_errors=[UserError(field=None, message=str(e))])

    session: Session = info.context["session"]
    product = session.exec(select(Product).where(Product.id == input.id)).first()
    if not product:
        return ProductUpdatePayload(
            product=None,
            user_errors=[UserError(field=["id"], message="Product not found")],
        )

    if input.title is not None:
        product.title = input.title
    if input.description is not None:
        product.description = input.description
    if input.status is not None:
        if input.status not in ("ACTIVE", "ARCHIVED", "DRAFT"):
            return ProductUpdatePayload(
                product=None,
                user_errors=[UserError(field=["status"], message="Invalid status value")],
            )
        product.status = input.status
    if input.tags is not None:
        product.tags = input.tags
    if input.vendor is not None:
        product.vendor = input.vendor
    if input.product_type is not None:
        product.product_type = input.product_type

    product.updated_at = datetime.now(timezone.utc)
    session.add(product)
    session.commit()
    session.refresh(product)

    return ProductUpdatePayload(product=_to_product_type(product), user_errors=[])


def resolve_product_variant_update(
    info: Info,
    input: ProductVariantUpdateInput,
) -> ProductVariantUpdatePayload:
    try:
        check_scope("productVariantUpdate", set(info.context.get("granted_scopes", [])))
    except ScopeError as e:
        return ProductVariantUpdatePayload(product_variant=None, user_errors=[UserError(field=None, message=str(e))])

    session: Session = info.context["session"]
    variant = session.exec(select(ProductVariant).where(ProductVariant.id == input.id)).first()
    if not variant:
        return ProductVariantUpdatePayload(
            product_variant=None,
            user_errors=[UserError(field=["id"], message="ProductVariant not found")],
        )

    if input.price is not None:
        try:
            variant.price = Decimal(input.price)
        except InvalidOperation:
            return ProductVariantUpdatePayload(
                product_variant=None,
                user_errors=[UserError(field=["price"], message="Invalid price value")],
            )
    if input.compare_at_price is not None:
        try:
            variant.compare_at_price = Decimal(input.compare_at_price)
        except InvalidOperation:
            return ProductVariantUpdatePayload(
                product_variant=None,
                user_errors=[UserError(field=["compareAtPrice"], message="Invalid compareAtPrice value")],
            )
    if input.sku is not None:
        variant.sku = input.sku
    if input.barcode is not None:
        variant.barcode = input.barcode
    if input.option1 is not None:
        variant.option1 = input.option1
    if input.option2 is not None:
        variant.option2 = input.option2
    if input.option3 is not None:
        variant.option3 = input.option3
    if input.taxable is not None:
        variant.taxable = input.taxable
    if input.requires_shipping is not None:
        variant.requires_shipping = input.requires_shipping

    variant.updated_at = datetime.now(timezone.utc)
    session.add(variant)
    session.commit()
    session.refresh(variant)

    return ProductVariantUpdatePayload(product_variant=_to_variant_type(variant), user_errors=[])
