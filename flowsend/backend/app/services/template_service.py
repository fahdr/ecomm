"""
Email template management service.

Handles CRUD operations for email templates, including both
user-created custom templates and system-provided templates.

For Developers:
    - System templates have `user_id=None` and `is_system=True`.
    - Users can read system templates but cannot modify or delete them.
    - Custom templates are scoped to the creating user.
    - Templates are filterable by category.

For QA Engineers:
    Test: create/read/update/delete custom templates, read system templates,
    verify system templates cannot be modified, category filtering.

For Project Managers:
    Templates are a key UX feature — system templates provide immediate
    value for new users, while custom templates enable brand consistency.
"""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_template import EmailTemplate
from app.models.user import User


async def create_template(
    db: AsyncSession, user: User, name: str, subject: str,
    html_content: str, text_content: str | None = None,
    category: str = "newsletter",
) -> EmailTemplate:
    """
    Create a new custom email template.

    Args:
        db: Async database session.
        user: The owning user.
        name: Template display name.
        subject: Default subject line.
        html_content: HTML body content.
        text_content: Plain-text fallback (optional).
        category: Template category.

    Returns:
        The newly created EmailTemplate.
    """
    template = EmailTemplate(
        user_id=user.id,
        name=name,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
        category=category,
        is_system=False,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


async def get_templates(
    db: AsyncSession, user_id: uuid.UUID,
    page: int = 1, page_size: int = 50,
    category: str | None = None,
) -> tuple[list[EmailTemplate], int]:
    """
    List email templates (user's custom + system templates).

    Args:
        db: Async database session.
        user_id: The user's UUID (to filter custom templates).
        page: Page number (1-indexed).
        page_size: Items per page.
        category: Optional category filter.

    Returns:
        Tuple of (list of EmailTemplate, total count).
    """
    # Show user's custom templates AND system templates
    base_filter = or_(
        EmailTemplate.user_id == user_id,
        EmailTemplate.is_system.is_(True),
    )

    count_query = select(func.count(EmailTemplate.id)).where(base_filter)
    query = select(EmailTemplate).where(base_filter)

    if category:
        count_query = count_query.where(EmailTemplate.category == category)
        query = query.where(EmailTemplate.category == category)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(EmailTemplate.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    templates = list(result.scalars().all())

    return templates, total


async def get_template(
    db: AsyncSession, user_id: uuid.UUID, template_id: uuid.UUID
) -> EmailTemplate | None:
    """
    Get a single template by ID (user's own or system template).

    Args:
        db: Async database session.
        user_id: The user's UUID.
        template_id: The template's UUID.

    Returns:
        The EmailTemplate if found and accessible, None otherwise.
    """
    result = await db.execute(
        select(EmailTemplate).where(
            EmailTemplate.id == template_id,
            or_(
                EmailTemplate.user_id == user_id,
                EmailTemplate.is_system.is_(True),
            ),
        )
    )
    return result.scalar_one_or_none()


async def update_template(
    db: AsyncSession, template: EmailTemplate,
    name: str | None = None, subject: str | None = None,
    html_content: str | None = None, text_content: str | None = None,
    category: str | None = None,
) -> EmailTemplate:
    """
    Update an existing custom template.

    System templates cannot be updated.

    Args:
        db: Async database session.
        template: The template to update.
        name: Updated name (optional).
        subject: Updated subject (optional).
        html_content: Updated HTML content (optional).
        text_content: Updated plain-text content (optional).
        category: Updated category (optional).

    Returns:
        The updated EmailTemplate.

    Raises:
        ValueError: If attempting to update a system template.
    """
    if template.is_system:
        raise ValueError("Cannot modify system templates")

    if name is not None:
        template.name = name
    if subject is not None:
        template.subject = subject
    if html_content is not None:
        template.html_content = html_content
    if text_content is not None:
        template.text_content = text_content
    if category is not None:
        template.category = category

    await db.flush()
    await db.refresh(template)
    return template


async def delete_template(db: AsyncSession, template: EmailTemplate) -> None:
    """
    Delete a custom template.

    System templates cannot be deleted.

    Args:
        db: Async database session.
        template: The template to delete.

    Raises:
        ValueError: If attempting to delete a system template.
    """
    if template.is_system:
        raise ValueError("Cannot delete system templates")

    await db.delete(template)
    await db.flush()


async def create_system_template(
    db: AsyncSession, name: str, subject: str,
    html_content: str, text_content: str | None = None,
    category: str = "newsletter",
) -> EmailTemplate:
    """
    Create a system template (available to all users).

    Args:
        db: Async database session.
        name: Template name.
        subject: Default subject line.
        html_content: HTML body content.
        text_content: Plain-text fallback (optional).
        category: Template category.

    Returns:
        The newly created system EmailTemplate.
    """
    template = EmailTemplate(
        user_id=None,
        name=name,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
        category=category,
        is_system=True,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template
