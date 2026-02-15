"""
Product-to-Post pipeline service for automated content creation.

Orchestrates the workflow from product data to scheduled social media posts:
1. Generate platform-specific captions from product data.
2. Create draft or scheduled posts for each target platform.
3. Optionally auto-schedule at optimal times per platform.

For Developers:
    ``product_to_posts`` is the main entry point. It iterates over the
    requested platforms, generates captions for each, and creates Post
    records. If auto_schedule is True, posts are scheduled at the next
    optimal time for each platform using the scheduler service.

For QA Engineers:
    Test with single and multiple platforms. Verify that auto-schedule
    assigns different optimal times per platform. Test with minimal
    product data (title only). Verify posts are created as drafts when
    auto_schedule is False.

For Project Managers:
    The product-to-post pipeline is PostPilot's signature automation.
    Users import a product and get ready-to-publish posts across all
    their connected platforms in one click.

For End Users:
    Import a product and PostPilot automatically generates optimized
    captions for each of your connected social media platforms. Choose
    to auto-schedule them or review as drafts first.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post, PostStatus
from app.services.caption_service import generate_caption
from app.services.scheduler_service import get_next_optimal_time

logger = logging.getLogger(__name__)


async def product_to_posts(
    db: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    product_data: dict,
    platforms: list[str],
    auto_schedule: bool = False,
    tone: str = "engaging",
) -> list[Post]:
    """
    Generate social media posts from product data for multiple platforms.

    For each requested platform, generates a platform-specific caption and
    creates a Post record. If auto_schedule is True, each post is scheduled
    at the next optimal time for its platform.

    Args:
        db: Async database session.
        user_id: UUID of the post owner.
        account_id: UUID of the target social account.
        product_data: Dict with product info (title, description, price, etc.).
        platforms: List of target platforms (e.g., ["instagram", "twitter"]).
        auto_schedule: Whether to automatically schedule at optimal times.
        tone: Desired caption tone (casual, professional, playful, engaging).

    Returns:
        List of newly created Post records (one per platform).
    """
    posts: list[Post] = []

    for platform in platforms:
        # Generate caption for this platform
        caption_result = generate_caption(
            product_data=product_data,
            platform=platform,
            tone=tone,
        )

        # Determine status and scheduled time
        status = PostStatus.draft
        scheduled_for = None

        if auto_schedule:
            status = PostStatus.scheduled
            scheduled_for = get_next_optimal_time(platform)

        # Create the post
        post = Post(
            user_id=user_id,
            account_id=account_id,
            content=caption_result["caption"],
            media_urls=product_data.get("media_urls", []),
            hashtags=caption_result["hashtags"],
            platform=platform,
            status=status,
            scheduled_for=scheduled_for,
        )
        db.add(post)
        posts.append(post)

        logger.info(
            "Created %s post for platform=%s user=%s (auto_schedule=%s)",
            status.value,
            platform,
            user_id,
            auto_schedule,
        )

    await db.flush()
    return posts
