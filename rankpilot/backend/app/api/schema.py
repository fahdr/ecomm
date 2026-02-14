"""
Schema markup (JSON-LD) API routes.

Provides CRUD endpoints for managing JSON-LD structured data configurations
and a preview endpoint that renders the JSON-LD as an embeddable script tag.

For Developers:
    Schema configs are scoped to a site. Each config represents a JSON-LD
    template for a specific page type. The preview endpoint returns the
    rendered <script> tag ready for HTML embedding.

For QA Engineers:
    Test CRUD for all page types (product, article, faq, breadcrumb, organization).
    Verify the preview endpoint returns valid JSON-LD in a script tag.
    Test with custom schema_json and with auto-generated defaults.

For Project Managers:
    Schema markup helps users get rich snippets in search results.
    This is a value-add feature available on all tiers.

For End Users:
    Generate JSON-LD structured data for your pages. Copy the rendered
    script tag and paste it into your page's HTML for rich search results.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.seo import SchemaConfigCreate, SchemaConfigResponse, SchemaConfigUpdate
from app.services.schema_service import (
    create_schema_config,
    delete_schema_config,
    get_schema_config,
    list_schema_configs,
    render_json_ld,
    update_schema_config,
)
from app.services.site_service import get_site

router = APIRouter(prefix="/schema", tags=["schema"])


@router.post("", response_model=SchemaConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_schema_config_endpoint(
    body: SchemaConfigCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new JSON-LD schema configuration.

    If no custom schema_json is provided, a default template is generated
    based on the page_type and the site's domain.

    Args:
        body: SchemaConfigCreate with site_id, page_type, optional schema_json.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly created SchemaConfigResponse.

    Raises:
        HTTPException 404: If the referenced site is not found.
    """
    site = await get_site(db, body.site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    config = await create_schema_config(
        db,
        body.site_id,
        body.page_type,
        body.schema_json,
        domain=site.domain,
    )
    return config


@router.get("", response_model=dict)
async def list_schema_configs_endpoint(
    site_id: uuid.UUID = Query(..., description="Site ID to list configs for"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List schema configurations for a site with pagination.

    Args:
        site_id: The site's UUID (required).
        page: Page number (1-indexed).
        per_page: Items per page (max 100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated response with items, total, page, and per_page.

    Raises:
        HTTPException 404: If the site is not found.
    """
    site = await get_site(db, site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    configs, total = await list_schema_configs(db, site_id, page, per_page)
    return {
        "items": [SchemaConfigResponse.model_validate(c) for c in configs],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{config_id}", response_model=SchemaConfigResponse)
async def get_schema_config_endpoint(
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single schema configuration by ID.

    Args:
        config_id: The schema config's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The SchemaConfigResponse.

    Raises:
        HTTPException 404: If the config is not found.
    """
    config = await get_schema_config(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Schema config not found")

    # Verify the user owns the site
    site = await get_site(db, config.site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Schema config not found")

    return config


@router.patch("/{config_id}", response_model=SchemaConfigResponse)
async def update_schema_config_endpoint(
    config_id: uuid.UUID,
    body: SchemaConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a schema configuration.

    Args:
        config_id: The schema config's UUID.
        body: SchemaConfigUpdate with optional schema_json and is_active.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated SchemaConfigResponse.

    Raises:
        HTTPException 404: If the config is not found.
    """
    config = await get_schema_config(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Schema config not found")

    site = await get_site(db, config.site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Schema config not found")

    updated = await update_schema_config(
        db, config, body.schema_json, body.is_active
    )
    return updated


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schema_config_endpoint(
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a schema configuration.

    Args:
        config_id: The schema config's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If the config is not found.
    """
    config = await get_schema_config(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Schema config not found")

    site = await get_site(db, config.site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Schema config not found")

    await delete_schema_config(db, config)


@router.get("/{config_id}/preview", response_class=PlainTextResponse)
async def preview_schema_endpoint(
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Preview the rendered JSON-LD script tag for a schema configuration.

    Returns the JSON-LD as a <script type="application/ld+json"> tag
    ready to be embedded in an HTML page.

    Args:
        config_id: The schema config's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Plain text containing the rendered HTML script tag.

    Raises:
        HTTPException 404: If the config is not found.
    """
    config = await get_schema_config(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Schema config not found")

    site = await get_site(db, config.site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Schema config not found")

    return render_json_ld(config.schema_json)
