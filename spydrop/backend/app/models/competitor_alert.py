"""
CompetitorAlert model for the SpyDrop service.

CompetitorAlert stores individual alert instances generated from catalog
diffs. Unlike PriceAlert (which defines monitoring rules), CompetitorAlert
records specific events that occurred — price drops, new products, etc.

For Developers:
    CompetitorAlert is created by ``check_and_create_alerts`` in the alert
    service when a catalog diff matches user-defined alert conditions. Each
    alert has a severity level (low/medium/high/critical) and can be marked
    as read by the user.

For QA Engineers:
    Test alert creation via the alert service after running a catalog diff.
    Verify that alerts are correctly classified by type and severity.
    Test the mark-as-read functionality via the API.

For Project Managers:
    CompetitorAlerts are the user-facing notifications about competitor
    changes. They drive the Alerts page in the dashboard and power the
    notification badges.

For End Users:
    View alerts to see when competitors change prices, add new products,
    or remove items. Mark alerts as read once you have reviewed them.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CompetitorAlert(Base):
    """
    A specific alert instance generated from a catalog change detection.

    Represents a single noteworthy event (price drop, new product, etc.)
    that the user should be informed about.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        competitor_id: Foreign key to the relevant competitor (optional).
        alert_type: Type of event ('price_drop', 'new_product',
            'out_of_stock', 'price_increase').
        severity: Alert severity ('low', 'medium', 'high', 'critical').
        message: Human-readable description of the event.
        data: JSON dict with contextual data (product details, price info).
        is_read: Whether the user has read/dismissed the alert.
        created_at: Timestamp when the alert was generated.
        owner: Related User record.
        competitor: Related Competitor record (optional).
    """

    __tablename__ = "competitor_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    competitor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competitors.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Alert type: price_drop, new_product, out_of_stock, price_increase",
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        nullable=False,
        doc="Severity: low, medium, high, critical",
    )
    message: Mapped[str] = mapped_column(
        String(1024), nullable=False, doc="Human-readable alert message"
    )
    data: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False, doc="Contextual data JSON"
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, doc="Whether the user has read this alert"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", lazy="selectin")
    competitor: Mapped["Competitor | None"] = relationship(
        "Competitor", lazy="selectin"
    )


# Avoid circular imports
from app.models.competitor import Competitor  # noqa: E402
from app.models.user import User  # noqa: E402
