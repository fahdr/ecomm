"""
System template seeder — creates default templates on application startup.

Provides four system templates covering the most common content generation
use cases: Professional, Casual, Luxury, and SEO-Focused.

For Developers:
    `seed_system_templates()` is called from the FastAPI lifespan handler.
    It is idempotent — checks for existing system templates by name before
    creating. Uses its own database session to avoid transaction conflicts.

    To add new system templates, add entries to the SYSTEM_TEMPLATES list
    and restart the application.

For QA Engineers:
    Verify system templates exist after startup by calling GET /api/v1/templates.
    All four should appear with is_system=True and user_id=None.
    Running startup multiple times should not create duplicates.

For Project Managers:
    System templates provide immediate value to new users. They demonstrate
    the feature without requiring any setup. The four presets cover the
    most common e-commerce copywriting styles.

For End Users:
    System templates are pre-built content styles ready to use:
    - Professional: Polished, formal business language
    - Casual: Friendly, approachable conversational tone
    - Luxury: Premium, aspirational high-end messaging
    - SEO-Focused: Keyword-optimized content for search rankings
"""

from sqlalchemy import select

from app.database import async_session_factory
from app.models.template import Template

# System template definitions
SYSTEM_TEMPLATES = [
    {
        "name": "Professional",
        "description": "Polished, formal language ideal for B2B products, electronics, and office supplies. Emphasizes quality, reliability, and specifications.",
        "tone": "professional",
        "style": "detailed",
        "content_types": ["title", "description", "meta_description", "keywords", "bullet_points"],
        "is_default": True,
    },
    {
        "name": "Casual",
        "description": "Friendly, approachable language perfect for lifestyle products, fashion, and consumer goods. Connects with everyday shoppers.",
        "tone": "casual",
        "style": "concise",
        "content_types": ["title", "description", "meta_description", "keywords", "bullet_points"],
        "is_default": False,
    },
    {
        "name": "Luxury",
        "description": "Premium, aspirational messaging for high-end products, jewelry, and designer goods. Evokes exclusivity and craftsmanship.",
        "tone": "luxury",
        "style": "storytelling",
        "content_types": ["title", "description", "meta_description", "keywords", "bullet_points"],
        "is_default": False,
    },
    {
        "name": "SEO-Focused",
        "description": "Keyword-optimized content designed to rank in search engines. Balances readability with strategic keyword placement.",
        "tone": "technical",
        "style": "list-based",
        "content_types": ["title", "description", "meta_description", "keywords", "bullet_points"],
        "is_default": False,
    },
]


async def seed_system_templates() -> int:
    """
    Seed system templates into the database.

    Creates the predefined system templates if they don't already exist.
    Checks by name to prevent duplicates on repeated startups.

    Returns:
        Number of new templates created.

    Note:
        Uses its own database session to avoid interference with
        the application's dependency injection system.
    """
    created_count = 0

    async with async_session_factory() as session:
        try:
            for template_data in SYSTEM_TEMPLATES:
                # Check if already exists
                result = await session.execute(
                    select(Template).where(
                        Template.name == template_data["name"],
                        Template.is_system.is_(True),
                    )
                )
                existing = result.scalar_one_or_none()

                if not existing:
                    template = Template(
                        user_id=None,
                        name=template_data["name"],
                        description=template_data["description"],
                        tone=template_data["tone"],
                        style=template_data["style"],
                        content_types=template_data["content_types"],
                        is_default=template_data["is_default"],
                        is_system=True,
                    )
                    session.add(template)
                    created_count += 1

            await session.commit()
        except Exception:
            await session.rollback()
            # Silently handle errors during seeding — the app should still start
            # even if the database is not yet ready (e.g., initial migration pending)
            pass

    return created_count
