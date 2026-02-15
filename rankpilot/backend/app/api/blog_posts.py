"""
Blog post API routes for SEO content management.

Provides CRUD endpoints for blog posts and an AI generation endpoint.
Blog post creation is subject to plan limits (max_items = posts per month).

For Developers:
    The `/generate` endpoint triggers mock AI content generation for an
    existing blog post. Plan limits are checked before creating new posts.
    The monthly limit uses PLAN_LIMITS[user.plan].max_items.

For QA Engineers:
    Test CRUD, plan limit enforcement (free: 2/mo, pro: 20/mo),
    AI generation, and status transitions (draft -> published -> archived).

For Project Managers:
    Blog posts drive plan upgrades. The AI generation feature is the
    key differentiator that makes users choose paid plans.

For End Users:
    Create and manage SEO blog posts. Use AI to generate content automatically.
    Upgrade your plan to create more posts per month.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.constants.plans import PLAN_LIMITS
from app.database import get_db
from app.models.user import User
from app.schemas.seo import (
    BlogPostCreate,
    BlogPostGenerate,
    BlogPostResponse,
    BlogPostUpdate,
)
from app.services.blog_service import (
    count_monthly_posts,
    create_blog_post,
    delete_blog_post,
    generate_blog_content,
    get_blog_post,
    list_blog_posts,
    update_blog_post,
)
from app.services.site_service import get_site

router = APIRouter(prefix="/blog-posts", tags=["blog-posts"])


@router.post("", response_model=BlogPostResponse, status_code=status.HTTP_201_CREATED)
async def create_blog_post_endpoint(
    body: BlogPostCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new blog post.

    Checks plan limits before creation. Content can be provided directly
    or left empty for later AI generation.

    Args:
        body: BlogPostCreate with site_id, title, optional content and keywords.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly created BlogPostResponse.

    Raises:
        HTTPException 403: If monthly plan limit is reached.
        HTTPException 404: If the referenced site is not found.
    """
    # Verify site ownership
    site = await get_site(db, body.site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Check plan limit
    plan_limits = PLAN_LIMITS[current_user.plan]
    if plan_limits.max_items != -1:
        monthly_count = await count_monthly_posts(db, current_user.id)
        if monthly_count >= plan_limits.max_items:
            raise HTTPException(
                status_code=403,
                detail=f"Monthly blog post limit reached ({plan_limits.max_items}). "
                f"Upgrade your plan to create more posts.",
            )

    post = await create_blog_post(
        db,
        current_user,
        body.site_id,
        body.title,
        body.content,
        body.meta_description,
        body.keywords,
    )
    return post


@router.get("", response_model=dict)
async def list_blog_posts_endpoint(
    site_id: uuid.UUID | None = Query(None, description="Filter by site ID"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List blog posts for the authenticated user with optional site filter.

    Args:
        site_id: Optional site UUID to filter by.
        page: Page number (1-indexed).
        per_page: Items per page (max 100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated response with items, total, page, and per_page.
    """
    posts, total = await list_blog_posts(
        db, current_user.id, site_id, page, per_page
    )
    return {
        "items": [BlogPostResponse.model_validate(p) for p in posts],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{post_id}", response_model=BlogPostResponse)
async def get_blog_post_endpoint(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single blog post by ID.

    Args:
        post_id: The blog post's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The BlogPostResponse.

    Raises:
        HTTPException 404: If the post is not found.
    """
    post = await get_blog_post(db, post_id, current_user.id)
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")
    return post


@router.patch("/{post_id}", response_model=BlogPostResponse)
async def update_blog_post_endpoint(
    post_id: uuid.UUID,
    body: BlogPostUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a blog post's fields.

    Only the fields provided in the request body will be updated.
    Setting status to 'published' automatically sets published_at.

    Args:
        post_id: The blog post's UUID.
        body: BlogPostUpdate with optional fields to change.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated BlogPostResponse.

    Raises:
        HTTPException 404: If the post is not found.
    """
    post = await get_blog_post(db, post_id, current_user.id)
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")

    updated = await update_blog_post(
        db,
        post,
        title=body.title,
        content=body.content,
        meta_description=body.meta_description if body.meta_description is not None else ...,
        keywords=body.keywords,
        status=body.status,
    )
    return updated


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blog_post_endpoint(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a blog post.

    Args:
        post_id: The blog post's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If the post is not found.
    """
    post = await get_blog_post(db, post_id, current_user.id)
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")
    await delete_blog_post(db, post)


@router.post("/generate", response_model=BlogPostResponse)
async def generate_blog_post_endpoint(
    body: BlogPostGenerate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate AI content for an existing blog post (mock).

    Fills in the post's content and meta description using AI-generated
    text based on the title and keywords. The mock generates placeholder
    SEO content.

    Args:
        body: BlogPostGenerate with the post_id to generate content for.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The BlogPostResponse with generated content.

    Raises:
        HTTPException 404: If the post is not found.
    """
    post = await get_blog_post(db, body.post_id, current_user.id)
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")
    updated_post = await generate_blog_content(db, post)
    return updated_post
