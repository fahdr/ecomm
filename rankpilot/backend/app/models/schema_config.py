"""
Schema configuration model for JSON-LD structured data.

Schema configs store templates for generating JSON-LD structured data
markup for different page types. This helps search engines understand
page content and can improve rich snippet visibility in search results.

For Developers:
    `page_type` defines the schema.org type (product, article, faq, etc.).
    `schema_json` stores the JSON-LD template as a JSON column.
    Users can customize the template or use pre-built ones.
    The schema preview endpoint renders the JSON-LD with actual data.

For QA Engineers:
    Test schema CRUD via /api/v1/schema endpoints.
    Verify JSON-LD output is valid by testing the preview endpoint.
    Test each page_type to ensure correct schema.org structure.

For Project Managers:
    Schema markup improves search result appearance with rich snippets.
    This is a differentiating feature that adds value for all plan tiers.

For End Users:
    Generate JSON-LD structured data for your pages to improve how
    search engines display your content. Supports Product, Article,
    FAQ, BreadcrumbList, and Organization schemas.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SchemaConfig(Base):
    """
    JSON-LD schema markup configuration for a site.

    Attributes:
        id: Unique identifier (UUID v4).
        site_id: Foreign key to the parent site.
        page_type: Schema.org page type ('product', 'article', 'faq', 'breadcrumb', 'organization').
        schema_json: JSON-LD template object.
        is_active: Whether this schema config is currently enabled.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        site: Related Site record.
    """

    __tablename__ = "schema_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    page_type: Mapped[str] = mapped_column(String(50), nullable=False)
    schema_json: Mapped[dict] = mapped_column(JSON, default={}, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    site = relationship("Site", back_populates="schema_configs", lazy="selectin")
