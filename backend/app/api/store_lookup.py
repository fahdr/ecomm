"""Shared store lookup helper for public API routes.

Provides a reusable function to resolve an active store by its URL slug.
Used by the public storefront API, customer auth, and customer account
routers.

**For Developers:**
    Import ``get_active_store`` in any router that needs to resolve a
    store from the URL slug. Raises 404 if the store is not found or
    not active.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store, StoreStatus


async def get_active_store(db: AsyncSession, slug: str) -> Store:
    """Retrieve an active store by slug or raise 404.

    Args:
        db: Async database session.
        slug: The store's URL slug.

    Returns:
        The Store ORM instance.

    Raises:
        HTTPException: 404 if the store does not exist or is not active.
    """
    result = await db.execute(
        select(Store).where(Store.slug == slug, Store.status == StoreStatus.active)
    )
    store = result.scalar_one_or_none()
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    return store
