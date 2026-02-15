"""
Ad Creative model for individual ad units.

Stores the ad copy, image, destination URL, and call-to-action for each
ad unit within an ad group. Supports AI-generated copy via Claude.

For Developers:
    Creatives are the actual ad content shown to users. The `status` field
    tracks approval state — platforms may reject creatives that violate
    their ad policies. AI copy generation populates headline, description,
    and call_to_action fields.

For QA Engineers:
    Test CRUD operations, AI copy generation endpoint, status transitions
    (active -> paused -> rejected), and required field validation.

For Project Managers:
    Creatives are the visual and textual content of ads. The AI feature
    can generate compelling ad copy automatically, saving users time.

For End Users:
    Create ad creatives with headlines, descriptions, and images.
    Use the AI Generate button to automatically create compelling copy.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CreativeStatus(str, enum.Enum):
    """
    Ad creative approval and activation status.

    Attributes:
        active: Creative is approved and delivering.
        paused: Creative is paused by the user.
        rejected: Creative was rejected by the ad platform (policy violation).
    """

    active = "active"
    paused = "paused"
    rejected = "rejected"


class AdCreative(Base):
    """
    Individual ad creative (copy + image + CTA) within an ad group.

    Attributes:
        id: Unique identifier (UUID v4).
        ad_group_id: Foreign key to the parent ad group.
        headline: Ad headline text (max 90 chars for most platforms).
        description: Ad body/description text.
        image_url: URL to the ad image asset (nullable).
        destination_url: Landing page URL the ad links to.
        call_to_action: CTA button text (e.g., "Shop Now", "Learn More").
        status: Creative approval/activation status.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        ad_group: Related AdGroup record.
    """

    __tablename__ = "ad_creatives"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ad_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_groups.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    headline: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1024), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    destination_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    call_to_action: Mapped[str] = mapped_column(
        String(50), default="Shop Now", nullable=False
    )
    status: Mapped[CreativeStatus] = mapped_column(
        Enum(CreativeStatus), default=CreativeStatus.active, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    ad_group = relationship("AdGroup", back_populates="creatives", lazy="selectin")
