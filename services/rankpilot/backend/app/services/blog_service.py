"""
Blog post management service for the RankPilot SEO engine.

Handles CRUD for blog posts, AI content generation (mock), slug generation,
word counting, and plan limit checking for monthly post creation.

For Developers:
    Slug generation uses a simple title-to-slug conversion. The word count
    is recalculated on every content update. AI generation is mocked — in
    production it would call the Anthropic API.

For QA Engineers:
    Test CRUD, slug uniqueness within a site, plan limit enforcement,
    AI generation mock, and word count accuracy.

For Project Managers:
    Blog post generation is the primary value driver. The plan limit
    (max_items) controls how many posts a user can create per month.

For End Users:
    Create and manage SEO-optimized blog posts. Use AI generation
    to create content targeting your keywords automatically.
"""

import re
import uuid
from datetime import UTC, datetime, date

from sqlalchemy import func, select, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blog_post import BlogPost
from app.models.user import User


def generate_slug(title: str) -> str:
    """
    Generate a URL-safe slug from a title.

    Converts to lowercase, replaces non-alphanumeric characters with hyphens,
    and strips leading/trailing hyphens.

    Args:
        title: The blog post title to slugify.

    Returns:
        A URL-safe slug string.

    Examples:
        >>> generate_slug("10 Best SEO Tips for 2024")
        '10-best-seo-tips-for-2024'
        >>> generate_slug("Hello World!")
        'hello-world'
    """
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    slug = slug.strip("-")
    return slug


def count_words(content: str) -> int:
    """
    Count the number of words in a text string.

    Splits on whitespace and counts non-empty tokens.

    Args:
        content: The text content to count words in.

    Returns:
        Number of words in the content.
    """
    if not content:
        return 0
    return len(content.split())


async def count_monthly_posts(
    db: AsyncSession, user_id: uuid.UUID
) -> int:
    """
    Count blog posts created by a user in the current calendar month.

    Used for plan limit enforcement (max_items = posts per month).

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Number of posts created this month.
    """
    today = date.today()
    result = await db.execute(
        select(func.count())
        .select_from(BlogPost)
        .where(
            BlogPost.user_id == user_id,
            extract("year", BlogPost.created_at) == today.year,
            extract("month", BlogPost.created_at) == today.month,
        )
    )
    return result.scalar() or 0


async def create_blog_post(
    db: AsyncSession,
    user: User,
    site_id: uuid.UUID,
    title: str,
    content: str | None = None,
    meta_description: str | None = None,
    keywords: list[str] | None = None,
) -> BlogPost:
    """
    Create a new blog post.

    Generates a slug from the title and calculates word count if content
    is provided. The post is created in 'draft' status by default.

    Args:
        db: Async database session.
        user: The owning user.
        site_id: Parent site UUID.
        title: Blog post title.
        content: Optional post content.
        meta_description: Optional SEO meta description.
        keywords: Optional list of target keywords.

    Returns:
        The newly created BlogPost.
    """
    slug = generate_slug(title)
    actual_content = content or ""
    word_count = count_words(actual_content)

    post = BlogPost(
        site_id=site_id,
        user_id=user.id,
        title=title,
        slug=slug,
        content=actual_content,
        meta_description=meta_description,
        keywords=keywords or [],
        word_count=word_count,
        status="draft",
    )
    db.add(post)
    await db.flush()
    return post


async def get_blog_post(
    db: AsyncSession,
    post_id: uuid.UUID,
    user_id: uuid.UUID,
) -> BlogPost | None:
    """
    Get a single blog post by ID, scoped to the user.

    Args:
        db: Async database session.
        post_id: The blog post's UUID.
        user_id: The requesting user's UUID.

    Returns:
        The BlogPost if found and owned by user, None otherwise.
    """
    result = await db.execute(
        select(BlogPost).where(BlogPost.id == post_id, BlogPost.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_blog_posts(
    db: AsyncSession,
    user_id: uuid.UUID,
    site_id: uuid.UUID | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[BlogPost], int]:
    """
    List blog posts for a user with optional site filter and pagination.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        site_id: Optional site UUID to filter by.
        page: Page number (1-indexed).
        per_page: Items per page.

    Returns:
        Tuple of (list of BlogPosts, total count).
    """
    base_query = select(BlogPost).where(BlogPost.user_id == user_id)
    count_query = select(func.count()).select_from(BlogPost).where(
        BlogPost.user_id == user_id
    )

    if site_id:
        base_query = base_query.where(BlogPost.site_id == site_id)
        count_query = count_query.where(BlogPost.site_id == site_id)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    offset = (page - 1) * per_page
    result = await db.execute(
        base_query.order_by(BlogPost.created_at.desc()).offset(offset).limit(per_page)
    )
    posts = list(result.scalars().all())
    return posts, total


async def update_blog_post(
    db: AsyncSession,
    post: BlogPost,
    title: str | None = None,
    content: str | None = None,
    meta_description: str | None = ...,  # type: ignore[assignment]
    keywords: list[str] | None = None,
    status: str | None = None,
) -> BlogPost:
    """
    Update a blog post's fields.

    Recalculates slug if title changes and word count if content changes.
    Sets published_at when status changes to 'published'.

    Args:
        db: Async database session.
        post: The BlogPost to update.
        title: New title (optional).
        content: New content (optional).
        meta_description: New meta description (Ellipsis = not provided).
        keywords: New keyword list (optional).
        status: New status (optional).

    Returns:
        The updated BlogPost.
    """
    if title is not None:
        post.title = title
        post.slug = generate_slug(title)
    if content is not None:
        post.content = content
        post.word_count = count_words(content)
    if meta_description is not ...:
        post.meta_description = meta_description
    if keywords is not None:
        post.keywords = keywords
    if status is not None:
        post.status = status
        if status == "published" and post.published_at is None:
            post.published_at = datetime.now(UTC)

    await db.flush()
    return post


async def delete_blog_post(db: AsyncSession, post: BlogPost) -> None:
    """
    Delete a blog post.

    Args:
        db: Async database session.
        post: The BlogPost to delete.
    """
    await db.delete(post)
    await db.flush()


async def generate_blog_content(
    db: AsyncSession, post: BlogPost
) -> BlogPost:
    """
    Generate AI content for a blog post (mock implementation).

    In production, this would call the Anthropic Claude API to generate
    SEO-optimized content based on the post's title and keywords.
    The mock generates placeholder content.

    Args:
        db: Async database session.
        post: The BlogPost to generate content for.

    Returns:
        The updated BlogPost with generated content.
    """
    # Mock AI-generated content
    keywords_str = ", ".join(post.keywords) if post.keywords else "general SEO"
    generated_content = f"""# {post.title}

## Introduction

In this comprehensive guide, we explore everything you need to know about {keywords_str}.
Whether you're a beginner or an experienced professional, this article will provide
valuable insights to help you improve your search engine rankings.

## Key Takeaways

- Understanding the fundamentals of {keywords_str} is essential for modern SEO.
- Implementing best practices can significantly improve your organic traffic.
- Regular monitoring and optimization ensure sustained search performance.

## Understanding {post.title}

Search engine optimization is a constantly evolving field. The strategies that worked
yesterday may not be as effective today. That's why it's crucial to stay updated
with the latest trends and best practices related to {keywords_str}.

### Best Practices

1. **Keyword Research**: Start with thorough keyword research to identify opportunities.
2. **Content Quality**: Create high-quality, informative content that serves user intent.
3. **Technical SEO**: Ensure your site is technically sound with fast loading times.
4. **Link Building**: Build authoritative backlinks to strengthen your domain authority.
5. **User Experience**: Optimize for user experience with clear navigation and mobile-friendliness.

## Measuring Success

Track your progress using key metrics:
- Organic traffic growth
- Keyword ranking improvements
- Click-through rates from search results
- Bounce rate and time on page

## Conclusion

Implementing a solid SEO strategy focused on {keywords_str} will help you achieve
sustainable organic growth. Remember that SEO is a long-term investment that
requires patience, consistency, and continuous optimization.

*This article was generated by RankPilot's AI engine to help you get started with SEO content creation.*
"""

    # Generate meta description if not set
    if not post.meta_description:
        post.meta_description = (
            f"Learn everything about {keywords_str}. "
            f"Comprehensive guide covering best practices, tips, and strategies "
            f"for improving your search engine rankings."
        )[:320]

    post.content = generated_content
    post.word_count = count_words(generated_content)
    await db.flush()
    return post
