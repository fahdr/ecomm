"""
Site model for the RankPilot SEO engine.

Each site represents a domain that the user wants to optimize for SEO.
Sites can be verified, crawled, and audited to track their SEO health.

For Developers:
    The `status` field tracks the site's current operational state.
    Sites must be verified before audits can be run. The `verification_method`
    field records how the site was verified (meta tag, DNS, file upload).
    Relationships cascade on user deletion.

For QA Engineers:
    Test site CRUD via /api/v1/sites endpoints.
    Verify that unverified sites cannot trigger audits.
    Verify plan-based limits on number of sites.

For Project Managers:
    Sites are the top-level entity in RankPilot. All other features
    (blog posts, keywords, audits, schema) are scoped to a site.

For End Users:
    Add your website domain to start tracking SEO performance.
    Verify ownership to unlock auditing and keyword tracking.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Site(Base):
    """
    A website domain registered for SEO tracking and optimization.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        domain: The website domain (e.g. 'example.com').
        sitemap_url: URL of the site's XML sitemap (optional).
        verification_method: How ownership was verified ('meta_tag', 'dns', 'file', None).
        is_verified: Whether domain ownership has been confirmed.
        last_crawled: Timestamp of the most recent crawl.
        status: Current operational status ('active', 'pending', 'error').
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        owner: Related User record.
        blog_posts: Blog posts associated with this site.
        keyword_trackings: Keywords being tracked for this site.
        seo_audits: SEO audit history for this site.
        schema_configs: Schema markup configurations for this site.
    """

    __tablename__ = "sites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sitemap_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    verification_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_crawled: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", backref="sites")
    blog_posts = relationship(
        "BlogPost", back_populates="site", cascade="all, delete-orphan", lazy="selectin"
    )
    keyword_trackings = relationship(
        "KeywordTracking", back_populates="site", cascade="all, delete-orphan", lazy="selectin"
    )
    seo_audits = relationship(
        "SeoAudit", back_populates="site", cascade="all, delete-orphan", lazy="selectin"
    )
    schema_configs = relationship(
        "SchemaConfig", back_populates="site", cascade="all, delete-orphan", lazy="selectin"
    )
