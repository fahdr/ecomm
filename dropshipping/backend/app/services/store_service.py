"""Store business logic.

Handles CRUD operations for stores with tenant isolation — each user
can only access their own stores.

**For Developers:**
    All functions take ``user_id`` to enforce ownership. Soft-delete sets
    ``status`` to ``deleted`` rather than removing the row.

**For QA Engineers:**
    - ``create_store`` generates a unique slug from the store name.
    - ``list_stores`` excludes soft-deleted stores by default.
    - ``get_store`` raises ``ValueError`` if the store doesn't exist or
      belongs to another user.
    - ``delete_store`` performs a soft-delete (sets status to ``deleted``).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store, StoreStatus
from app.services.theme_service import seed_preset_themes
from app.utils.slug import generate_unique_slug


async def create_store(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    niche: str,
    description: str | None = None,
) -> Store:
    """Create a new store for a user.

    Generates a unique slug from the store name and persists the store.

    Args:
        db: Async database session.
        user_id: The owner's UUID.
        name: Display name of the store.
        niche: Product niche or category.
        description: Optional description text.

    Returns:
        The newly created Store ORM instance.
    """
    slug = await generate_unique_slug(db, Store, name)
    store = Store(
        user_id=user_id,
        name=name,
        slug=slug,
        niche=niche,
        description=description,
    )
    db.add(store)
    await db.flush()

    # Seed preset themes so the store has a default appearance.
    await seed_preset_themes(db, store.id)

    return store


async def list_stores(db: AsyncSession, user_id: uuid.UUID) -> list[Store]:
    """List all non-deleted stores belonging to a user.

    Args:
        db: Async database session.
        user_id: The owner's UUID.

    Returns:
        A list of Store ORM instances ordered by creation date (newest first).
    """
    result = await db.execute(
        select(Store)
        .where(Store.user_id == user_id, Store.status != StoreStatus.deleted)
        .order_by(Store.created_at.desc())
    )
    return list(result.scalars().all())


async def get_store(
    db: AsyncSession, user_id: uuid.UUID, store_id: uuid.UUID
) -> Store:
    """Retrieve a single store, verifying ownership.

    Args:
        db: Async database session.
        user_id: The requesting user's UUID (for ownership check).
        store_id: The UUID of the store to retrieve.

    Returns:
        The Store ORM instance.

    Raises:
        ValueError: If the store does not exist, is deleted, or belongs
            to a different user.
    """
    result = await db.execute(
        select(Store).where(Store.id == store_id)
    )
    store = result.scalar_one_or_none()
    if store is None or store.status == StoreStatus.deleted:
        raise ValueError("Store not found")
    if store.user_id != user_id:
        raise ValueError("Store not found")
    return store


async def update_store(
    db: AsyncSession,
    user_id: uuid.UUID,
    store_id: uuid.UUID,
    **fields,
) -> Store:
    """Update a store's fields (partial update).

    Only provided (non-None) fields are updated. The slug is regenerated
    if the name changes.

    Args:
        db: Async database session.
        user_id: The requesting user's UUID (for ownership check).
        store_id: The UUID of the store to update.
        **fields: Keyword arguments for fields to update (name, niche,
            description, status).

    Returns:
        The updated Store ORM instance.

    Raises:
        ValueError: If the store does not exist or belongs to another user.
    """
    store = await get_store(db, user_id, store_id)

    for key, value in fields.items():
        if value is not None:
            setattr(store, key, value)

    # Regenerate slug if name changed.
    if "name" in fields and fields["name"] is not None:
        store.slug = await generate_unique_slug(
            db, Store, fields["name"], exclude_id=store.id
        )

    await db.flush()
    await db.refresh(store)
    return store


async def delete_store(
    db: AsyncSession, user_id: uuid.UUID, store_id: uuid.UUID
) -> Store:
    """Soft-delete a store by setting its status to ``deleted``.

    Args:
        db: Async database session.
        user_id: The requesting user's UUID (for ownership check).
        store_id: The UUID of the store to delete.

    Returns:
        The soft-deleted Store ORM instance.

    Raises:
        ValueError: If the store does not exist or belongs to another user.
    """
    store = await get_store(db, user_id, store_id)
    store.status = StoreStatus.deleted
    await db.flush()
    await db.refresh(store)
    return store
