"""Store theme API router for authenticated dashboard endpoints.

Provides CRUD operations for store themes, theme activation, and
font/block type metadata. All endpoints require authentication and
verify store ownership.

**For Developers:**
    The router is prefixed with ``/stores/{store_id}/themes``. Store ownership
    is verified by checking the store's ``user_id`` matches the current user.
    Use ``Depends(get_current_user)`` for authentication.

**For QA Engineers:**
    - All endpoints require a valid Bearer token.
    - Store ownership is enforced — users can only manage their own stores' themes.
    - Preset themes cannot be deleted.
    - Active themes cannot be deleted.
    - Only one theme per store can be active.
    - ``GET /meta/fonts`` and ``GET /meta/block-types`` are unauthenticated metadata endpoints.

**For End Users:**
    These endpoints power the theme editor in your dashboard. Choose from
    preset themes, create custom ones, and customize colors, fonts, and layout.

**For Project Managers:**
    This API is AI-ready — the structured JSON format for theme configs makes
    it easy for AI automation to create themes via ``POST /stores/{id}/themes``.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.constants.themes import BLOCK_TYPES, BODY_FONTS, HEADING_FONTS
from app.database import get_db
from app.models.store import Store, StoreStatus
from app.models.user import User
from app.schemas.theme import (
    CreateThemeRequest,
    ThemeResponse,
    UpdateThemeRequest,
)
from app.services import theme_service

router = APIRouter(prefix="/stores/{store_id}/themes", tags=["themes"])


async def _get_user_store(
    store_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Store:
    """Verify the store exists and belongs to the current user.

    Args:
        store_id: UUID of the store.
        current_user: The authenticated user.
        db: Async database session.

    Returns:
        The Store instance.

    Raises:
        HTTPException: 404 if store not found or doesn't belong to the user.
    """
    result = await db.execute(
        select(Store).where(
            Store.id == store_id,
            Store.user_id == current_user.id,
            Store.status != StoreStatus.deleted,
        )
    )
    store = result.scalar_one_or_none()
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    return store


@router.get("", response_model=list[ThemeResponse])
async def list_themes(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ThemeResponse]:
    """List all themes for a store.

    Returns preset themes first, then custom themes, sorted by name.

    Args:
        store_id: UUID of the store.
        current_user: Authenticated user (injected).
        db: Database session (injected).

    Returns:
        List of ThemeResponse objects.
    """
    await _get_user_store(store_id, current_user, db)
    themes = await theme_service.list_themes(db, store_id)
    return [ThemeResponse.model_validate(t) for t in themes]


@router.post("", response_model=ThemeResponse, status_code=status.HTTP_201_CREATED)
async def create_theme(
    store_id: uuid.UUID,
    body: CreateThemeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThemeResponse:
    """Create a new custom theme for a store.

    Optionally clones configuration from a named preset theme.

    Args:
        store_id: UUID of the store.
        body: Theme creation request with name and optional clone source.
        current_user: Authenticated user (injected).
        db: Database session (injected).

    Returns:
        The newly created ThemeResponse.
    """
    await _get_user_store(store_id, current_user, db)
    theme = await theme_service.create_theme(
        db, store_id, body.name, body.clone_from
    )
    return ThemeResponse.model_validate(theme)


@router.get("/{theme_id}", response_model=ThemeResponse)
async def get_theme(
    store_id: uuid.UUID,
    theme_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThemeResponse:
    """Get a single theme by ID.

    Args:
        store_id: UUID of the store.
        theme_id: UUID of the theme.
        current_user: Authenticated user (injected).
        db: Database session (injected).

    Returns:
        ThemeResponse for the requested theme.

    Raises:
        HTTPException: 404 if the theme is not found.
    """
    await _get_user_store(store_id, current_user, db)
    theme = await theme_service.get_theme(db, store_id, theme_id)
    if theme is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found",
        )
    return ThemeResponse.model_validate(theme)


@router.patch("/{theme_id}", response_model=ThemeResponse)
async def update_theme(
    store_id: uuid.UUID,
    theme_id: uuid.UUID,
    body: UpdateThemeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThemeResponse:
    """Update a theme's configuration (partial update).

    Only provided fields will be updated. Can update both preset and
    custom themes (presets create a modified copy in practice, but the
    API allows direct editing for flexibility).

    Args:
        store_id: UUID of the store.
        theme_id: UUID of the theme to update.
        body: Partial update request.
        current_user: Authenticated user (injected).
        db: Database session (injected).

    Returns:
        The updated ThemeResponse.

    Raises:
        HTTPException: 404 if the theme is not found.
    """
    await _get_user_store(store_id, current_user, db)
    theme = await theme_service.get_theme(db, store_id, theme_id)
    if theme is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found",
        )

    updates = body.model_dump(exclude_unset=True)
    theme = await theme_service.update_theme(db, theme, updates)
    return ThemeResponse.model_validate(theme)


@router.delete("/{theme_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_theme(
    store_id: uuid.UUID,
    theme_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a custom theme.

    Preset themes and the currently active theme cannot be deleted.

    Args:
        store_id: UUID of the store.
        theme_id: UUID of the theme to delete.
        current_user: Authenticated user (injected).
        db: Database session (injected).

    Raises:
        HTTPException: 404 if not found, 400 if preset or active.
    """
    await _get_user_store(store_id, current_user, db)
    theme = await theme_service.get_theme(db, store_id, theme_id)
    if theme is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found",
        )

    deleted = await theme_service.delete_theme(db, theme)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a preset theme or the active theme",
        )


@router.post("/{theme_id}/activate", response_model=ThemeResponse)
async def activate_theme(
    store_id: uuid.UUID,
    theme_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThemeResponse:
    """Activate a theme for the store's storefront.

    Deactivates the currently active theme and activates the specified one.

    Args:
        store_id: UUID of the store.
        theme_id: UUID of the theme to activate.
        current_user: Authenticated user (injected).
        db: Database session (injected).

    Returns:
        The newly activated ThemeResponse.

    Raises:
        HTTPException: 404 if the theme is not found.
    """
    await _get_user_store(store_id, current_user, db)
    theme = await theme_service.activate_theme(db, store_id, theme_id)
    if theme is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found",
        )
    return ThemeResponse.model_validate(theme)


# --- Metadata endpoints (no auth required) ---

meta_router = APIRouter(prefix="/themes/meta", tags=["themes"])


@meta_router.get("/fonts")
async def get_available_fonts() -> dict:
    """Get the curated list of available fonts for theme customization.

    Returns:
        Dict with ``heading_fonts`` and ``body_fonts`` lists.
    """
    return {
        "heading_fonts": HEADING_FONTS,
        "body_fonts": BODY_FONTS,
    }


@meta_router.get("/block-types")
async def get_block_types() -> dict:
    """Get the list of available block types for page composition.

    Returns:
        Dict with ``block_types`` list.
    """
    return {"block_types": BLOCK_TYPES}
