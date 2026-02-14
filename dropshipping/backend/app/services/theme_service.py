"""Business logic for store theme management.

Handles CRUD operations for store themes, preset seeding, theme activation,
and retrieving the active theme for public storefront rendering.

**For Developers:**
    All functions accept an ``AsyncSession`` and operate within the caller's
    transaction. The ``seed_preset_themes`` function should be called when
    a new store is created to populate it with all preset themes.

**For QA Engineers:**
    - ``seed_preset_themes`` creates all 7 presets with "Frosted" as active.
    - ``activate_theme`` deactivates the current active before activating the new one.
    - ``delete_theme`` refuses to delete preset themes or the active theme.
    - ``get_active_theme`` returns the active theme for a store, or None.

**For Project Managers:**
    The service layer separates business logic from API routing, making it
    testable and reusable (e.g., from Celery tasks or AI automation).
"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.themes import DEFAULT_THEME_NAME, PRESET_THEMES
from app.models.theme import StoreTheme


async def seed_preset_themes(db: AsyncSession, store_id: uuid.UUID) -> list[StoreTheme]:
    """Create all preset themes for a newly created store.

    Seeds the 7 built-in presets and activates the default ("Frosted") theme.

    Args:
        db: Async database session.
        store_id: UUID of the store to seed themes for.

    Returns:
        List of created StoreTheme instances.
    """
    themes = []
    for preset in PRESET_THEMES:
        theme = StoreTheme(
            store_id=store_id,
            name=preset["name"],
            is_active=(preset["name"] == DEFAULT_THEME_NAME),
            is_preset=True,
            colors=preset["colors"],
            typography=preset["typography"],
            styles=preset["styles"],
            blocks=preset["blocks"],
        )
        db.add(theme)
        themes.append(theme)
    await db.flush()
    return themes


async def list_themes(db: AsyncSession, store_id: uuid.UUID) -> list[StoreTheme]:
    """List all themes for a store, ordered by preset first then by name.

    Args:
        db: Async database session.
        store_id: UUID of the store.

    Returns:
        Ordered list of StoreTheme instances.
    """
    result = await db.execute(
        select(StoreTheme)
        .where(StoreTheme.store_id == store_id)
        .order_by(StoreTheme.is_preset.desc(), StoreTheme.name)
    )
    return list(result.scalars().all())


async def get_theme(
    db: AsyncSession, store_id: uuid.UUID, theme_id: uuid.UUID
) -> StoreTheme | None:
    """Get a single theme by ID, scoped to a store.

    Args:
        db: Async database session.
        store_id: UUID of the store.
        theme_id: UUID of the theme.

    Returns:
        The StoreTheme instance, or None if not found.
    """
    result = await db.execute(
        select(StoreTheme).where(
            StoreTheme.id == theme_id,
            StoreTheme.store_id == store_id,
        )
    )
    return result.scalar_one_or_none()


async def create_theme(
    db: AsyncSession,
    store_id: uuid.UUID,
    name: str,
    clone_from: str | None = None,
) -> StoreTheme:
    """Create a new custom theme, optionally cloning from a preset.

    If ``clone_from`` is provided, the new theme copies the preset's
    colors, typography, styles, and blocks. Otherwise it starts with
    the default "Frosted" configuration.

    Args:
        db: Async database session.
        store_id: UUID of the store.
        name: Display name for the new theme.
        clone_from: Optional preset name to clone from.

    Returns:
        The newly created StoreTheme instance.
    """
    # Find the source configuration to clone.
    source_config = None
    if clone_from:
        for preset in PRESET_THEMES:
            if preset["name"].lower() == clone_from.lower():
                source_config = preset
                break

    # Fall back to the default preset if clone_from didn't match.
    if source_config is None:
        for preset in PRESET_THEMES:
            if preset["name"] == DEFAULT_THEME_NAME:
                source_config = preset
                break

    theme = StoreTheme(
        store_id=store_id,
        name=name,
        is_active=False,
        is_preset=False,
        colors=source_config["colors"] if source_config else {},
        typography=source_config["typography"] if source_config else {},
        styles=source_config["styles"] if source_config else {},
        blocks=source_config["blocks"] if source_config else [],
    )
    db.add(theme)
    await db.flush()
    return theme


async def update_theme(
    db: AsyncSession,
    theme: StoreTheme,
    updates: dict,
) -> StoreTheme:
    """Update a theme's configuration fields.

    Only updates fields that are provided (not None) in the updates dict.

    Args:
        db: Async database session.
        theme: The StoreTheme instance to update.
        updates: Dict of field names to new values.

    Returns:
        The updated StoreTheme instance.
    """
    for field, value in updates.items():
        if value is not None:
            setattr(theme, field, value)
    await db.flush()
    await db.refresh(theme)
    return theme


async def delete_theme(
    db: AsyncSession, theme: StoreTheme
) -> bool:
    """Delete a custom theme.

    Preset themes and active themes cannot be deleted.

    Args:
        db: Async database session.
        theme: The StoreTheme instance to delete.

    Returns:
        True if deleted successfully, False if deletion was refused.
    """
    if theme.is_preset or theme.is_active:
        return False
    await db.delete(theme)
    await db.flush()
    return True


async def activate_theme(
    db: AsyncSession, store_id: uuid.UUID, theme_id: uuid.UUID
) -> StoreTheme | None:
    """Activate a theme for a store, deactivating the current active theme.

    Args:
        db: Async database session.
        store_id: UUID of the store.
        theme_id: UUID of the theme to activate.

    Returns:
        The newly activated StoreTheme, or None if the theme wasn't found.
    """
    # Deactivate all themes for this store.
    await db.execute(
        update(StoreTheme)
        .where(StoreTheme.store_id == store_id, StoreTheme.is_active == True)  # noqa: E712
        .values(is_active=False)
    )

    # Activate the specified theme.
    result = await db.execute(
        select(StoreTheme).where(
            StoreTheme.id == theme_id,
            StoreTheme.store_id == store_id,
        )
    )
    theme = result.scalar_one_or_none()
    if theme is None:
        return None

    theme.is_active = True
    await db.flush()
    await db.refresh(theme)
    return theme


async def get_active_theme(
    db: AsyncSession, store_id: uuid.UUID
) -> StoreTheme | None:
    """Get the currently active theme for a store.

    Args:
        db: Async database session.
        store_id: UUID of the store.

    Returns:
        The active StoreTheme, or None if no theme is active.
    """
    result = await db.execute(
        select(StoreTheme).where(
            StoreTheme.store_id == store_id,
            StoreTheme.is_active == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()
