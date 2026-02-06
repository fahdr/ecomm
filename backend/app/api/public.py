"""Public API router for unauthenticated storefront endpoints.

Provides read-only access to store data for the public-facing storefront.
No authentication is required — these endpoints are consumed by the
Next.js storefront app via server-side rendering.

**For Developers:**
    The router is prefixed with ``/public`` (full path:
    ``/api/v1/public/...``). Stores are looked up by slug, not UUID.

**For QA Engineers:**
    - Only stores with ``status == active`` are returned.
    - Paused and deleted stores return 404.
    - No ``user_id`` is exposed in the response.

**For End Users:**
    These endpoints power the public storefront. When you visit a store
    URL, the storefront fetches store data from here.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.store import Store, StoreStatus
from app.schemas.public import PublicStoreResponse

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/stores/{slug}", response_model=PublicStoreResponse)
async def get_public_store(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> PublicStoreResponse:
    """Retrieve a store by its slug for public display.

    Only active stores are returned. Paused or deleted stores will
    result in a 404 response.

    Args:
        slug: The URL-friendly store slug (e.g. ``my-awesome-store``).
        db: Async database session injected by FastAPI.

    Returns:
        PublicStoreResponse with the store's public-facing data.

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

    return PublicStoreResponse.model_validate(store)
