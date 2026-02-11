"""Slug generation utility.

Converts human-readable names into URL-friendly slugs and ensures
uniqueness within the database by appending numeric suffixes when needed.

**For Developers:**
    Use ``generate_unique_slug`` when creating any entity that needs a
    unique slug (stores, products, blog posts, etc.). The function queries
    the database to check for collisions and appends ``-2``, ``-3``, etc.

**For QA Engineers:**
    - Slugs are lowercased, stripped of special characters, and hyphenated.
    - Consecutive hyphens are collapsed; leading/trailing hyphens are removed.
    - Collision resolution: ``my-store``, ``my-store-2``, ``my-store-3``, etc.
"""

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def slugify(value: str) -> str:
    """Convert a string to a URL-friendly slug.

    Normalizes unicode characters, removes non-alphanumeric characters
    (except hyphens), collapses consecutive hyphens, and strips
    leading/trailing hyphens.

    Args:
        value: The human-readable string to convert.

    Returns:
        A lowercase, hyphen-separated slug string.

    Examples:
        >>> slugify("My Cool Store!")
        'my-cool-store'
        >>> slugify("  Héllo  Wörld  ")
        'hello-world'
    """
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[-\s]+", "-", value)
    value = value.strip("-")
    return value


async def generate_unique_slug(
    db: AsyncSession,
    model_class,
    name: str,
    slug_field: str = "slug",
    exclude_id=None,
) -> str:
    """Generate a unique slug for a given model by checking the database.

    Starts with the base slug derived from ``name``. If it already exists,
    appends ``-2``, ``-3``, etc. until a unique slug is found.

    Args:
        db: Async database session for uniqueness checks.
        model_class: The SQLAlchemy model class to check against.
        name: The human-readable name to derive the slug from.
        slug_field: The name of the slug column on the model. Defaults to ``"slug"``.
        exclude_id: Optional UUID of the current entity to exclude from the
            uniqueness check (used during updates so a record doesn't conflict
            with itself).

    Returns:
        A unique slug string that does not exist in the database for the given model.
    """
    base_slug = slugify(name)
    slug = base_slug
    counter = 2

    column = getattr(model_class, slug_field)

    while True:
        query = select(model_class).where(column == slug)
        if exclude_id is not None:
            query = query.where(model_class.id != exclude_id)
        result = await db.execute(query)
        if result.scalar_one_or_none() is None:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1
