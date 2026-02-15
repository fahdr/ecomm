"""
Blog post model for AI-generated SEO content.

Blog posts are the primary content creation feature of RankPilot. Users can
create posts manually or have AI generate optimized content targeting specific
keywords. Blog post creation counts toward the plan's monthly limit (max_items).

For Developers:
    The `content` field stores the full HTML/Markdown body as TEXT.
    The `keywords` field uses a PostgreSQL ARRAY(String) for the target keywords.
    The `slug` is auto-generated from the title and must be unique per site.
    `word_count` is calculated when content is saved.
    `published_at` is set when status changes to 'published'.

For QA Engineers:
    Test blog post CRUD via /api/v1/blog-posts.
    Verify plan limits: free users get 2 posts/month, pro gets 20, enterprise unlimited.
    Test AI generation endpoint and verify content quality mock.
    Verify slug uniqueness within a site.

For Project Managers:
    Blog posts are the core revenue driver — users upgrade to create more content.
    AI generation is the key value proposition that differentiates RankPilot.

For End Users:
    Create SEO-optimized blog posts with AI assistance. Target specific keywords
    to improve your search rankings. Posts count toward your monthly limit.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BlogPost(Base):
    """
    An SEO-optimized blog post associated with a site.

    Attributes:
        id: Unique identifier (UUID v4).
        site_id: Foreign key to the parent site.
        user_id: Foreign key to the owning user.
        title: Blog post title (used for SEO title tag).
        slug: URL-safe slug derived from the title (unique per site).
        content: Full blog post content in Markdown/HTML.
        meta_description: SEO meta description (max ~160 chars recommended).
        keywords: List of target keywords for this post.
        status: Publication status ('draft', 'published', 'archived').
        word_count: Number of words in the content.
        published_at: Timestamp when the post was published.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        site: Related Site record.
    """

    __tablename__ = "blog_posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    meta_description: Mapped[str | None] = mapped_column(String(320), nullable=True)
    keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=[], nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    site = relationship("Site", back_populates="blog_posts", lazy="selectin")
