"""
Pydantic schemas for social media features (accounts, posts, queue, analytics).

Defines request/response data structures for all PostPilot feature endpoints.
Uses Pydantic v2 with `from_attributes=True` for direct ORM model conversion.

For Developers:
    All schemas use Pydantic v2 BaseModel with strict typing. Optional fields
    use `| None` syntax. Lists default to empty. Datetime fields accept
    ISO 8601 strings. Use `model_config = {"from_attributes": True}` for
    schemas that are returned from ORM queries.

For QA Engineers:
    Test validation: invalid platforms should return 422, empty content should
    be rejected, and scheduled_for must be a valid datetime. Verify that
    response schemas match what the API actually returns.

For Project Managers:
    These schemas define the contract between the frontend dashboard and
    the backend API. Any changes here affect both sides of the integration.

For End Users:
    These data formats define what information you provide when creating posts,
    connecting accounts, or viewing analytics.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.content_queue import QueueStatus
from app.models.post import PostStatus
from app.models.social_account import SocialPlatform


# ── Social Account Schemas ──────────────────────────────────────────


class SocialAccountConnect(BaseModel):
    """
    Request to connect a new social media account.

    In the current implementation, this simulates an OAuth flow.
    The platform and account_name are provided, and a mock connection
    is established.

    Attributes:
        platform: The social media platform to connect.
        account_name: Display name for the account (e.g., @mybrand).
        account_id_external: Platform-specific account ID (optional, auto-generated if not provided).
    """

    platform: SocialPlatform
    account_name: str = Field(
        ..., min_length=1, max_length=255, description="Display name for the account"
    )
    account_id_external: str | None = Field(
        None, description="Platform account ID (auto-generated if omitted)"
    )


class SocialAccountResponse(BaseModel):
    """
    Social account data returned in API responses.

    Tokens are never included in responses for security.

    Attributes:
        id: Account unique identifier.
        platform: Social media platform.
        account_name: Display name of the account.
        account_id_external: Platform-specific account ID.
        is_connected: Whether the account is currently connected.
        connected_at: When the account was connected.
        created_at: Record creation timestamp.
    """

    id: uuid.UUID
    platform: SocialPlatform
    account_name: str
    account_id_external: str
    is_connected: bool
    connected_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Post Schemas ────────────────────────────────────────────────────


class PostCreate(BaseModel):
    """
    Request to create a new social media post.

    Attributes:
        account_id: Target social account to publish to.
        content: Post caption/text content.
        media_urls: List of media URLs to attach (images, videos).
        hashtags: List of hashtags (without # prefix).
        platform: Target platform (must match the account's platform).
        scheduled_for: Optional scheduled publish time (ISO 8601).
    """

    account_id: uuid.UUID
    content: str = Field(
        ..., min_length=1, max_length=5000, description="Post caption text"
    )
    media_urls: list[str] = Field(
        default_factory=list, description="Media attachment URLs"
    )
    hashtags: list[str] = Field(
        default_factory=list, description="Hashtags without # prefix"
    )
    platform: str = Field(
        ..., description="Target platform (instagram, facebook, tiktok)"
    )
    scheduled_for: datetime | None = Field(
        None, description="Scheduled publish time (ISO 8601)"
    )


class PostUpdate(BaseModel):
    """
    Request to update an existing post (partial update).

    All fields are optional. Only provided fields are updated.

    Attributes:
        content: Updated caption text.
        media_urls: Updated media URLs.
        hashtags: Updated hashtag list.
        scheduled_for: Updated schedule time.
    """

    content: str | None = Field(None, max_length=5000)
    media_urls: list[str] | None = None
    hashtags: list[str] | None = None
    scheduled_for: datetime | None = None


class PostResponse(BaseModel):
    """
    Post data returned in API responses.

    Attributes:
        id: Post unique identifier.
        account_id: Target social account ID.
        content: Post caption text.
        media_urls: Attached media URLs.
        hashtags: Post hashtags.
        platform: Target platform.
        status: Current lifecycle status.
        scheduled_for: Scheduled publish time.
        posted_at: Actual publish time.
        error_message: Error details if failed.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
    """

    id: uuid.UUID
    account_id: uuid.UUID
    content: str
    media_urls: list[str]
    hashtags: list[str]
    platform: str
    status: PostStatus
    scheduled_for: datetime | None
    posted_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PostSchedule(BaseModel):
    """
    Request to schedule an existing post for future publication.

    Attributes:
        scheduled_for: The datetime to publish the post (ISO 8601).
    """

    scheduled_for: datetime = Field(
        ..., description="When to publish the post (ISO 8601)"
    )


class PostListResponse(BaseModel):
    """
    Paginated list of posts.

    Attributes:
        items: List of post records.
        total: Total number of posts matching the query.
        page: Current page number (1-indexed).
        per_page: Number of items per page.
    """

    items: list[PostResponse]
    total: int
    page: int
    per_page: int


# ── Post Metrics Schemas ────────────────────────────────────────────


class PostMetricsResponse(BaseModel):
    """
    Engagement metrics for a single post.

    Attributes:
        id: Metrics record identifier.
        post_id: Associated post identifier.
        impressions: Number of times the post was displayed.
        reach: Unique users who saw the post.
        likes: Number of likes/reactions.
        comments: Number of comments.
        shares: Number of shares/reposts.
        clicks: Number of link clicks.
        engagement_rate: Calculated engagement rate (likes+comments+shares)/impressions.
        fetched_at: When metrics were last refreshed.
    """

    id: uuid.UUID
    post_id: uuid.UUID
    impressions: int
    reach: int
    likes: int
    comments: int
    shares: int
    clicks: int
    engagement_rate: float = Field(
        default=0.0, description="(likes + comments + shares) / impressions"
    )
    fetched_at: datetime

    model_config = {"from_attributes": True}


# ── Content Queue Schemas ───────────────────────────────────────────


class ContentQueueCreate(BaseModel):
    """
    Request to add a product to the content generation queue.

    Attributes:
        product_data: JSON object with product information (title, description, price, image_url, etc.).
        platforms: List of target platforms for generated content.
    """

    product_data: dict = Field(
        ..., description="Product data dict (title, description, price, image_url, etc.)"
    )
    platforms: list[str] = Field(
        default_factory=list, description="Target platforms for this content"
    )


class ContentQueueResponse(BaseModel):
    """
    Content queue item returned in API responses.

    Attributes:
        id: Queue item identifier.
        product_data: Product information used for generation.
        ai_generated_content: AI-generated caption (None before generation).
        platforms: Target platforms.
        status: Queue item lifecycle status.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
    """

    id: uuid.UUID
    product_data: dict
    ai_generated_content: str | None
    platforms: list[str]
    status: QueueStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContentQueueListResponse(BaseModel):
    """
    Paginated list of content queue items.

    Attributes:
        items: List of queue item records.
        total: Total number of items matching the query.
        page: Current page number (1-indexed).
        per_page: Number of items per page.
    """

    items: list[ContentQueueResponse]
    total: int
    page: int
    per_page: int


# ── Calendar View Schema ────────────────────────────────────────────


class CalendarDay(BaseModel):
    """
    A single day in the calendar view with its scheduled posts.

    Attributes:
        date: The calendar date (ISO 8601 date string).
        posts: Posts scheduled for this date.
    """

    date: str
    posts: list[PostResponse]


class CalendarView(BaseModel):
    """
    Calendar view response with posts grouped by date.

    Attributes:
        days: List of calendar days with their posts.
        total_posts: Total number of posts in the date range.
    """

    days: list[CalendarDay]
    total_posts: int


# ── Analytics Schemas ───────────────────────────────────────────────


class AnalyticsOverview(BaseModel):
    """
    Aggregated analytics overview for the user's social media performance.

    Attributes:
        total_posts: Total number of published posts.
        total_impressions: Sum of all post impressions.
        total_reach: Sum of all post reach.
        total_likes: Sum of all post likes.
        total_comments: Sum of all post comments.
        total_shares: Sum of all post shares.
        total_clicks: Sum of all post clicks.
        avg_engagement_rate: Average engagement rate across all posts.
    """

    total_posts: int = 0
    total_impressions: int = 0
    total_reach: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    total_clicks: int = 0
    avg_engagement_rate: float = 0.0


class CaptionGenerateRequest(BaseModel):
    """
    Request to generate AI captions for product data.

    Attributes:
        product_data: Product information for caption generation.
        platform: Target platform to tailor the caption for.
        tone: Desired tone of the caption (casual, professional, playful, etc.).
    """

    product_data: dict = Field(
        ..., description="Product data for caption generation"
    )
    platform: str = Field(
        default="instagram", description="Target platform"
    )
    tone: str = Field(
        default="engaging", description="Caption tone (casual, professional, playful, engaging)"
    )


class CaptionGenerateResponse(BaseModel):
    """
    AI-generated caption response.

    Attributes:
        caption: The generated caption text.
        hashtags: Suggested hashtags for the post.
        platform: Platform the caption was generated for.
    """

    caption: str
    hashtags: list[str]
    platform: str
