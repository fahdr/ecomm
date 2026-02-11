"""Customer wishlist API router.

Provides endpoints for customers to manage their product wishlist
from the storefront.

**For Developers:**
    The wishlist uses the existing ``CustomerWishlist`` junction table.
    Products are resolved to include title, slug, price, and image
    in the response.

**For QA Engineers:**
    - Adding the same product twice returns 409 Conflict.
    - Removing a non-existent wishlist item returns 404.
    - Wishlist items include product details (title, price, image).

**For End Users:**
    Save products you're interested in to your wishlist and find them
    later from your account page.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.customer import CustomerAccount, CustomerWishlist
from app.models.product import Product
from app.models.store import Store, StoreStatus
from app.api.deps import get_current_customer
from app.schemas.customer import WishlistItemResponse

router = APIRouter(
    prefix="/public/stores/{slug}/customers/me/wishlist",
    tags=["customer-wishlist"],
)


async def _get_active_store(db: AsyncSession, slug: str) -> Store:
    """Resolve an active store by slug."""
    result = await db.execute(
        select(Store).where(Store.slug == slug, Store.status == StoreStatus.active)
    )
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.get("", response_model=list[WishlistItemResponse])
async def list_wishlist(
    slug: str,
    customer: CustomerAccount = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """List all products in the customer's wishlist.

    Args:
        slug: The store's URL slug.
        customer: The authenticated customer.
        db: Async database session.

    Returns:
        List of wishlist items with product details.
    """
    await _get_active_store(db, slug)

    result = await db.execute(
        select(CustomerWishlist)
        .where(CustomerWishlist.customer_id == customer.id)
        .order_by(CustomerWishlist.added_at.desc())
    )
    items = result.scalars().all()

    response = []
    for item in items:
        product = item.product
        response.append(
            WishlistItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_title=product.title if product else None,
                product_slug=product.slug if product else None,
                product_price=product.price if product else None,
                product_image=product.images[0] if product and product.images else None,
                added_at=item.added_at,
            )
        )

    return response


@router.post("/{product_id}", status_code=status.HTTP_201_CREATED)
async def add_to_wishlist(
    slug: str,
    product_id: uuid.UUID,
    customer: CustomerAccount = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """Add a product to the customer's wishlist.

    Args:
        slug: The store's URL slug.
        product_id: The product's UUID.
        customer: The authenticated customer.
        db: Async database session.

    Returns:
        Success message with product ID.

    Raises:
        HTTPException: 404 if the product is not found.
        HTTPException: 409 if the product is already in the wishlist.
    """
    store = await _get_active_store(db, slug)

    # Verify product exists in this store
    prod_result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.store_id == store.id,
        )
    )
    if not prod_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")

    # Check for duplicate
    existing = await db.execute(
        select(CustomerWishlist).where(
            CustomerWishlist.customer_id == customer.id,
            CustomerWishlist.product_id == product_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Product already in wishlist")

    wishlist_item = CustomerWishlist(
        customer_id=customer.id,
        product_id=product_id,
    )
    db.add(wishlist_item)
    await db.commit()

    return {"message": "Added to wishlist", "product_id": str(product_id)}


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_wishlist(
    slug: str,
    product_id: uuid.UUID,
    customer: CustomerAccount = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """Remove a product from the customer's wishlist.

    Args:
        slug: The store's URL slug.
        product_id: The product's UUID.
        customer: The authenticated customer.
        db: Async database session.

    Raises:
        HTTPException: 404 if the product is not in the wishlist.
    """
    await _get_active_store(db, slug)

    result = await db.execute(
        select(CustomerWishlist).where(
            CustomerWishlist.customer_id == customer.id,
            CustomerWishlist.product_id == product_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Product not in wishlist")

    await db.delete(item)
    await db.commit()
