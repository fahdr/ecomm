"""
Source configuration API endpoints for TrendScout.

Manages external data source credentials and settings. Each user can
configure multiple sources (AliExpress, TikTok, Google Trends, Reddit)
with their own API keys and preferences.

For Developers:
    Credentials are stored in the database but never returned in API
    responses. The `has_credentials` flag indicates whether credentials
    have been configured without exposing the values.

For QA Engineers:
    Test CRUD operations: create config, list configs, update credentials/
    settings/active state, delete config. Verify credentials are never
    leaked in responses.

For Project Managers:
    Source configs control which external APIs are available for research.
    Users need to configure at least one source before running research.

For End Users:
    Configure your data sources under the Sources tab. Each source needs
    API credentials (where applicable) and optional settings like
    region and language preferences.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.research import (
    SourceConfigCreate,
    SourceConfigListResponse,
    SourceConfigResponse,
    SourceConfigUpdate,
)
from app.services.research_service import (
    create_source_config,
    delete_source_config,
    get_source_configs,
    update_source_config,
)

router = APIRouter(prefix="/sources", tags=["sources"])


def _build_source_response(config) -> SourceConfigResponse:
    """
    Build a SourceConfigResponse from a SourceConfig ORM object.

    Redacts credentials — only reports whether they have been set.

    Args:
        config: SourceConfig ORM instance.

    Returns:
        SourceConfigResponse with has_credentials flag instead of raw creds.
    """
    return SourceConfigResponse(
        id=config.id,
        user_id=config.user_id,
        source_type=config.source_type,
        has_credentials=bool(config.credentials),
        settings=config.settings,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.post("", response_model=SourceConfigResponse, status_code=201)
async def create_config(
    body: SourceConfigCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a new source configuration.

    Each source type can only be configured once per user.

    Args:
        body: Source config creation data (source_type, credentials, settings).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        SourceConfigResponse with the new config (credentials redacted).

    Raises:
        HTTPException 400: If source_type is invalid.
    """
    valid_types = {"aliexpress", "tiktok", "google_trends", "reddit"}
    if body.source_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source type. Valid types: {', '.join(sorted(valid_types))}",
        )

    config = await create_source_config(
        db,
        user_id=current_user.id,
        source_type=body.source_type,
        credentials=body.credentials,
        settings=body.settings,
    )
    return _build_source_response(config)


@router.get("", response_model=SourceConfigListResponse)
async def list_configs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all source configurations for the authenticated user.

    Returns all configs ordered by source_type. Credentials are redacted.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        SourceConfigListResponse with all user configs.
    """
    configs = await get_source_configs(db, current_user.id)
    return SourceConfigListResponse(
        items=[_build_source_response(c) for c in configs],
    )


@router.patch("/{config_id}", response_model=SourceConfigResponse)
async def update_config(
    config_id: uuid.UUID,
    body: SourceConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a source configuration's credentials, settings, or active state.

    Only the owning user can update their configs. All fields are optional —
    only provided fields are updated.

    Args:
        config_id: The source config's UUID.
        body: Fields to update (credentials, settings, is_active — all optional).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        SourceConfigResponse with the updated config (credentials redacted).

    Raises:
        HTTPException 404: If config not found or not owned by user.
    """
    config = await update_source_config(
        db,
        config_id=config_id,
        user_id=current_user.id,
        credentials=body.credentials,
        settings=body.settings,
        is_active=body.is_active,
    )
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source configuration not found",
        )
    return _build_source_response(config)


@router.delete("/{config_id}", status_code=204)
async def delete_config(
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a source configuration.

    Removes the configuration and its stored credentials permanently.

    Args:
        config_id: The source config's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If config not found or not owned by user.
    """
    deleted = await delete_source_config(db, config_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source configuration not found",
        )
