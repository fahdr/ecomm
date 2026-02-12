"""
Template management API endpoints.

Provides CRUD operations for content generation templates. System templates
are read-only and visible to all users. Custom templates are private to
the user who created them.

For Developers:
    Templates are filtered by: system templates (user_id=NULL) OR
    user's own templates (user_id=current_user.id). System templates
    cannot be updated or deleted via the API.

    The seeding function in `app/services/template_seeder.py` creates
    the initial system templates at application startup.

For QA Engineers:
    Test template visibility:
    - GET /templates returns both system and user templates
    - System templates have is_system=True and cannot be deleted (403)
    - Custom templates can be created, updated, and deleted
    - Users cannot see or modify other users' templates

For Project Managers:
    Templates are a differentiating feature. System templates cover
    common use cases. Custom templates let users personalize AI output
    to match their brand voice, increasing stickiness and satisfaction.

For End Users:
    Templates control the tone and style of your generated content.
    Use system templates for quick starts, or create custom templates
    with your preferred settings for consistent brand messaging.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.template import Template
from app.models.user import User
from app.schemas.content import TemplateCreate, TemplateResponse, TemplateUpdate

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("/", response_model=TemplateResponse, status_code=201)
async def create_template(
    request: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a custom content template.

    Creates a new template owned by the current user with the specified
    tone, style, and content type settings.

    Args:
        request: Template data (name, tone, style, content_types, etc.).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        TemplateResponse with the newly created template.
    """
    template = Template(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        tone=request.tone,
        style=request.style,
        prompt_override=request.prompt_override,
        content_types=request.content_types,
        is_default=False,
        is_system=False,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


@router.get("/", response_model=list[TemplateResponse])
async def list_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all templates visible to the current user.

    Returns system templates (available to all users) and the user's
    own custom templates, ordered by system templates first, then by name.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of TemplateResponse objects.
    """
    result = await db.execute(
        select(Template)
        .where(
            or_(
                Template.is_system.is_(True),
                Template.user_id == current_user.id,
            )
        )
        .order_by(Template.is_system.desc(), Template.name)
    )
    return list(result.scalars().all())


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single template by ID.

    The user can access system templates or their own custom templates.

    Args:
        template_id: The template UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        TemplateResponse with template details.

    Raises:
        HTTPException 404: If the template is not found or not accessible.
    """
    result = await db.execute(
        select(Template).where(
            Template.id == template_id,
            or_(
                Template.is_system.is_(True),
                Template.user_id == current_user.id,
            ),
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found.",
        )
    return template


@router.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    request: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a custom template.

    Only the owning user can update their templates. System templates
    cannot be modified.

    Args:
        template_id: The template UUID.
        request: Partial update data (only provided fields are changed).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        TemplateResponse with updated template.

    Raises:
        HTTPException 404: If the template is not found.
        HTTPException 403: If trying to modify a system template.
    """
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found.",
        )

    if template.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System templates cannot be modified.",
        )

    if template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found.",
        )

    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.flush()
    await db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a custom template.

    System templates cannot be deleted. Only the owning user can
    delete their custom templates.

    Args:
        template_id: The template UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If the template is not found.
        HTTPException 403: If trying to delete a system template.
    """
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found.",
        )

    if template.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System templates cannot be deleted.",
        )

    if template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found.",
        )

    await db.delete(template)
    await db.flush()
