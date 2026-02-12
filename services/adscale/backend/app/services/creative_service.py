"""
Ad creative management and AI copy generation service.

Handles CRUD operations for ad creatives and provides AI-powered
ad copy generation using mock Claude responses.

For Developers:
    The `generate_ad_copy` function returns mock AI-generated copy.
    In production, this would call the Anthropic Claude API with a
    structured prompt to generate headlines, descriptions, and CTAs.

For QA Engineers:
    Test CRUD operations, AI copy generation (should return non-empty
    strings), and status transitions (active -> paused -> rejected).

For Project Managers:
    AI copy generation is a key value proposition — it saves users
    time by automatically writing compelling ad text.

For End Users:
    Let AI write your ad copy — just provide a product name and
    description, and AdScale generates headlines and descriptions.
"""

import uuid

from sqlalchemy import select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad_creative import AdCreative
from app.models.ad_group import AdGroup


async def create_creative(
    db: AsyncSession,
    ad_group_id: uuid.UUID,
    headline: str,
    description: str,
    destination_url: str,
    image_url: str | None = None,
    call_to_action: str = "Shop Now",
    status: str = "active",
) -> AdCreative:
    """
    Create a new ad creative within an ad group.

    Args:
        db: Async database session.
        ad_group_id: UUID of the parent ad group.
        headline: Ad headline text.
        description: Ad body/description text.
        destination_url: Landing page URL.
        image_url: URL to the ad image asset (optional).
        call_to_action: CTA button text (default: "Shop Now").
        status: Initial status (default: "active").

    Returns:
        The newly created AdCreative.

    Raises:
        ValueError: If the ad group is not found.
    """
    # Verify ad group exists
    result = await db.execute(
        select(AdGroup).where(AdGroup.id == ad_group_id)
    )
    if not result.scalar_one_or_none():
        raise ValueError("Ad group not found.")

    creative = AdCreative(
        ad_group_id=ad_group_id,
        headline=headline,
        description=description,
        image_url=image_url,
        destination_url=destination_url,
        call_to_action=call_to_action,
        status=status,
    )
    db.add(creative)
    await db.flush()
    return creative


async def list_creatives(
    db: AsyncSession,
    ad_group_id: uuid.UUID | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[AdCreative], int]:
    """
    List ad creatives, optionally filtered by ad group.

    Args:
        db: Async database session.
        ad_group_id: Optional filter by parent ad group UUID.
        offset: Pagination offset (default 0).
        limit: Maximum items per page (default 50).

    Returns:
        Tuple of (list of AdCreatives, total count).
    """
    query = select(AdCreative)
    count_query = select(sql_func.count(AdCreative.id))

    if ad_group_id:
        query = query.where(AdCreative.ad_group_id == ad_group_id)
        count_query = count_query.where(AdCreative.ad_group_id == ad_group_id)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    result = await db.execute(
        query.order_by(AdCreative.created_at.desc()).offset(offset).limit(limit)
    )
    creatives = list(result.scalars().all())

    return creatives, total


async def get_creative(
    db: AsyncSession,
    creative_id: uuid.UUID,
) -> AdCreative | None:
    """
    Get a specific ad creative by ID.

    Args:
        db: Async database session.
        creative_id: UUID of the ad creative.

    Returns:
        The AdCreative if found, None otherwise.
    """
    result = await db.execute(
        select(AdCreative).where(AdCreative.id == creative_id)
    )
    return result.scalar_one_or_none()


async def update_creative(
    db: AsyncSession,
    creative_id: uuid.UUID,
    **updates,
) -> AdCreative | None:
    """
    Update an existing ad creative.

    Only provided (non-None) fields are updated.

    Args:
        db: Async database session.
        creative_id: UUID of the creative to update.
        **updates: Keyword arguments with field names and new values.

    Returns:
        The updated AdCreative, or None if not found.
    """
    creative = await get_creative(db, creative_id)
    if not creative:
        return None

    for key, value in updates.items():
        if value is not None and hasattr(creative, key):
            setattr(creative, key, value)

    await db.flush()
    return creative


async def delete_creative(
    db: AsyncSession,
    creative_id: uuid.UUID,
) -> bool:
    """
    Delete an ad creative.

    Args:
        db: Async database session.
        creative_id: UUID of the creative to delete.

    Returns:
        True if the creative was found and deleted, False if not found.
    """
    creative = await get_creative(db, creative_id)
    if not creative:
        return False

    await db.delete(creative)
    await db.flush()
    return True


def generate_ad_copy(
    product_name: str,
    product_description: str,
    target_audience: str | None = None,
    tone: str | None = None,
) -> dict:
    """
    Generate AI ad copy for a product (mock implementation).

    In production, this would call Claude API with a structured prompt.
    The mock version generates deterministic copy based on the product info.

    Args:
        product_name: Name of the product to advertise.
        product_description: Brief product description for context.
        target_audience: Description of the target audience (optional).
        tone: Desired tone of voice (optional).

    Returns:
        Dict with 'headline', 'description', and 'call_to_action' keys.
    """
    # Mock AI-generated copy based on product info
    audience_suffix = f" for {target_audience}" if target_audience else ""
    tone_prefix = f"{tone.title()} " if tone else ""

    headline = f"{tone_prefix}Discover {product_name} — Transform Your Experience"
    description = (
        f"Introducing {product_name}: {product_description} "
        f"Designed{audience_suffix} to deliver exceptional value. "
        f"Don't miss out on this game-changing solution."
    )
    call_to_action = "Shop Now"

    # Vary CTA based on tone if provided
    if tone:
        tone_ctas = {
            "professional": "Learn More",
            "playful": "Get Yours!",
            "urgent": "Buy Now",
            "luxury": "Explore Collection",
        }
        call_to_action = tone_ctas.get(tone.lower(), "Shop Now")

    return {
        "headline": headline[:255],
        "description": description[:1024],
        "call_to_action": call_to_action[:50],
    }
