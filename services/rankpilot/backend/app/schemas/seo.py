"""
Pydantic schemas for all RankPilot SEO feature endpoints.

Defines request/response models for Sites, Blog Posts, Keyword Tracking,
SEO Audits, and Schema Configurations.

For Developers:
    All schemas use Pydantic v2 with `from_attributes = True` for ORM
    compatibility. UUIDs are typed as `uuid.UUID` for automatic serialization.
    Lists use generic types for proper OpenAPI schema generation.

For QA Engineers:
    Test validation: invalid UUIDs return 422, missing required fields
    return 422, string length limits are enforced.

For Project Managers:
    These schemas define the API contract between the frontend dashboard
    and the backend. Any change here affects the API documentation at /docs.

For End Users:
    These data formats define what information you send to and receive
    from the RankPilot API endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Pagination ────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    """
    Generic paginated response wrapper.

    Attributes:
        items: List of items for the current page.
        total: Total number of items across all pages.
        page: Current page number (1-indexed).
        per_page: Number of items per page.
    """

    items: list
    total: int
    page: int
    per_page: int


# ── Site Schemas ──────────────────────────────────────────────────────────

class SiteCreate(BaseModel):
    """
    Request schema for creating a new site.

    Attributes:
        domain: The website domain (e.g. 'example.com').
        sitemap_url: Optional URL of the site's XML sitemap.
    """

    domain: str = Field(..., min_length=3, max_length=255, description="Website domain")
    sitemap_url: str | None = Field(None, max_length=512, description="XML sitemap URL")


class SiteUpdate(BaseModel):
    """
    Request schema for updating a site.

    All fields are optional — only provided fields will be updated.

    Attributes:
        domain: Updated website domain.
        sitemap_url: Updated sitemap URL.
        status: Updated operational status.
    """

    domain: str | None = Field(None, min_length=3, max_length=255)
    sitemap_url: str | None = None
    status: str | None = Field(None, pattern="^(active|pending|error)$")


class SiteResponse(BaseModel):
    """
    Response schema for a site record.

    Attributes:
        id: Site unique identifier.
        user_id: Owning user ID.
        domain: Website domain.
        sitemap_url: XML sitemap URL (if set).
        verification_method: How the site was verified (if verified).
        is_verified: Whether domain ownership is confirmed.
        last_crawled: Timestamp of last crawl.
        status: Current operational status.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    domain: str
    sitemap_url: str | None
    verification_method: str | None
    is_verified: bool
    last_crawled: datetime | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Blog Post Schemas ─────────────────────────────────────────────────────

class BlogPostCreate(BaseModel):
    """
    Request schema for creating a blog post.

    Content can be provided directly or left empty for AI generation.

    Attributes:
        site_id: ID of the site this post belongs to.
        title: Blog post title.
        content: Optional post content (empty for AI generation).
        meta_description: Optional SEO meta description.
        keywords: Target keywords for the post.
    """

    site_id: uuid.UUID = Field(..., description="Parent site ID")
    title: str = Field(..., min_length=1, max_length=500, description="Post title")
    content: str | None = Field(None, description="Post content (optional for AI generation)")
    meta_description: str | None = Field(None, max_length=320)
    keywords: list[str] = Field(default_factory=list, description="Target keywords")


class BlogPostUpdate(BaseModel):
    """
    Request schema for updating a blog post.

    All fields are optional — only provided fields will be updated.

    Attributes:
        title: Updated title.
        content: Updated content.
        meta_description: Updated meta description.
        keywords: Updated keyword list.
        status: Updated publication status.
    """

    title: str | None = Field(None, min_length=1, max_length=500)
    content: str | None = None
    meta_description: str | None = Field(None, max_length=320)
    keywords: list[str] | None = None
    status: str | None = Field(None, pattern="^(draft|published|archived)$")


class BlogPostResponse(BaseModel):
    """
    Response schema for a blog post record.

    Attributes:
        id: Blog post unique identifier.
        site_id: Parent site ID.
        user_id: Owning user ID.
        title: Post title.
        slug: URL-safe slug.
        content: Full post content.
        meta_description: SEO meta description.
        keywords: Target keyword list.
        status: Publication status.
        word_count: Content word count.
        published_at: Publication timestamp.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    id: uuid.UUID
    site_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    slug: str
    content: str
    meta_description: str | None
    keywords: list[str]
    status: str
    word_count: int
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BlogPostGenerate(BaseModel):
    """
    Request schema for AI-generated blog post content.

    Triggers the AI to generate content for an existing blog post.

    Attributes:
        post_id: ID of the blog post to generate content for.
    """

    post_id: uuid.UUID = Field(..., description="Blog post ID to generate content for")


# ── Keyword Tracking Schemas ─────────────────────────────────────────────

class KeywordTrackingCreate(BaseModel):
    """
    Request schema for adding a keyword to track.

    Attributes:
        site_id: ID of the site to track this keyword for.
        keyword: The search keyword/phrase to track.
    """

    site_id: uuid.UUID = Field(..., description="Parent site ID")
    keyword: str = Field(..., min_length=1, max_length=255, description="Keyword to track")


class KeywordTrackingResponse(BaseModel):
    """
    Response schema for a tracked keyword.

    Attributes:
        id: Keyword tracking unique identifier.
        site_id: Parent site ID.
        keyword: The tracked keyword/phrase.
        current_rank: Current search position (None = not ranked).
        previous_rank: Previous search position (for trend tracking).
        search_volume: Estimated monthly search volume.
        difficulty: SEO difficulty score (0-100).
        tracked_since: When tracking started.
        last_checked: When rank was last checked.
    """

    id: uuid.UUID
    site_id: uuid.UUID
    keyword: str
    current_rank: int | None
    previous_rank: int | None
    search_volume: int | None
    difficulty: float | None
    tracked_since: datetime
    last_checked: datetime | None

    model_config = {"from_attributes": True}


# ── SEO Audit Schemas ────────────────────────────────────────────────────

class SeoAuditRun(BaseModel):
    """
    Request schema for triggering an SEO audit.

    Attributes:
        site_id: ID of the site to audit.
    """

    site_id: uuid.UUID = Field(..., description="Site to audit")


class SeoAuditResponse(BaseModel):
    """
    Response schema for an SEO audit result.

    Attributes:
        id: Audit unique identifier.
        site_id: Audited site ID.
        overall_score: SEO health score (0-100).
        issues: List of detected issues with severity and details.
        recommendations: List of actionable improvement suggestions.
        pages_crawled: Number of pages analyzed.
        created_at: Audit execution timestamp.
    """

    id: uuid.UUID
    site_id: uuid.UUID
    overall_score: float
    issues: list
    recommendations: list
    pages_crawled: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Schema Config Schemas ────────────────────────────────────────────────

class SchemaConfigCreate(BaseModel):
    """
    Request schema for creating a JSON-LD schema configuration.

    Attributes:
        site_id: Parent site ID.
        page_type: Schema.org type ('product', 'article', 'faq', 'breadcrumb', 'organization').
        schema_json: Optional custom JSON-LD template (auto-generated if empty).
    """

    site_id: uuid.UUID = Field(..., description="Parent site ID")
    page_type: str = Field(
        ...,
        pattern="^(product|article|faq|breadcrumb|organization)$",
        description="Schema.org page type",
    )
    schema_json: dict | None = Field(None, description="Custom JSON-LD template")


class SchemaConfigUpdate(BaseModel):
    """
    Request schema for updating a schema configuration.

    Attributes:
        schema_json: Updated JSON-LD template.
        is_active: Whether this config is enabled.
    """

    schema_json: dict | None = None
    is_active: bool | None = None


class SchemaConfigResponse(BaseModel):
    """
    Response schema for a JSON-LD schema configuration.

    Attributes:
        id: Schema config unique identifier.
        site_id: Parent site ID.
        page_type: Schema.org page type.
        schema_json: JSON-LD template object.
        is_active: Whether this config is enabled.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    id: uuid.UUID
    site_id: uuid.UUID
    page_type: str
    schema_json: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
