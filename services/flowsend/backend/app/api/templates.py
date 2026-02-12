"""
Email template API endpoints.

Provides CRUD for custom and system email templates, with category filtering.

For Developers:
    Users can read system templates but cannot create/update/delete them.
    Custom templates are scoped to the authenticated user.

For QA Engineers:
    Test: create custom template, list (includes system), get by ID,
    update custom, delete custom, reject update/delete on system templates.

For Project Managers:
    Templates reduce email creation time and ensure brand consistency.

For End Users:
    Browse templates to find a starting point, then customize or
    create your own from scratch.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.email import (
    EmailTemplateCreate,
    EmailTemplateResponse,
    EmailTemplateUpdate,
    PaginatedResponse,
)
from app.services.template_service import (
    create_template,
    delete_template,
    get_template,
    get_templates,
    update_template,
)

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("", response_model=EmailTemplateResponse, status_code=201)
async def create_template_endpoint(
    body: EmailTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new custom email template.

    Args:
        body: Template creation data (name, subject, html_content, category).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly created template.
    """
    template = await create_template(
        db, current_user, body.name, body.subject,
        body.html_content, text_content=body.text_content,
        category=body.category,
    )
    return template


@router.get("", response_model=PaginatedResponse[EmailTemplateResponse])
async def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    category: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List email templates (user's custom + system templates).

    Args:
        page: Page number.
        page_size: Items per page.
        category: Optional category filter.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated list of templates.
    """
    templates, total = await get_templates(
        db, current_user.id, page=page, page_size=page_size,
        category=category,
    )
    return PaginatedResponse(
        items=templates, total=total, page=page, page_size=page_size
    )


@router.get("/{template_id}", response_model=EmailTemplateResponse)
async def get_template_endpoint(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single template by ID (user's own or system template).

    Args:
        template_id: The template's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The template data.

    Raises:
        HTTPException 404: If template not found or not accessible.
    """
    template = await get_template(db, current_user.id, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.patch("/{template_id}", response_model=EmailTemplateResponse)
async def update_template_endpoint(
    template_id: uuid.UUID,
    body: EmailTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a custom template.

    System templates cannot be modified.

    Args:
        template_id: The template's UUID.
        body: Update data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated template.

    Raises:
        HTTPException 404: If template not found.
        HTTPException 400: If attempting to update a system template.
    """
    template = await get_template(db, current_user.id, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        updated = await update_template(
            db, template,
            name=body.name, subject=body.subject,
            html_content=body.html_content, text_content=body.text_content,
            category=body.category,
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{template_id}", status_code=204)
async def delete_template_endpoint(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a custom template.

    System templates cannot be deleted.

    Args:
        template_id: The template's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If template not found.
        HTTPException 400: If attempting to delete a system template.
    """
    template = await get_template(db, current_user.id, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        await delete_template(db, template)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
