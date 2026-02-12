"""
Alert models for the SpyDrop service.

PriceAlert defines monitoring rules (e.g., notify when price drops > 10%).
AlertHistory stores triggered alert instances with context data.

For Developers:
    Alerts can be scoped to a specific product or an entire competitor.
    The `alert_type` field controls which events trigger the alert:
    price_drop, price_increase, new_product, out_of_stock, back_in_stock.
    The `threshold` field is a percentage for price-based alerts.

For QA Engineers:
    Test alert CRUD via /api/v1/alerts. Verify alerts trigger correctly
    when scan results match the alert conditions. Check alert history
    accumulates entries.

For Project Managers:
    Alerts are how users stay informed about competitor changes without
    manually checking. They can set thresholds for price changes and
    get notified about new/removed products.

For End Users:
    Set up alerts to get notified when competitors change their prices,
    add new products, or go out of stock.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PriceAlert(Base):
    """
    A monitoring rule that triggers when specified conditions are met.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        competitor_product_id: Optional FK to a specific product to monitor.
        competitor_id: Optional FK to a competitor (monitors all products).
        alert_type: Type of event to monitor ('price_drop', 'price_increase',
            'new_product', 'out_of_stock', 'back_in_stock').
        threshold: Percentage threshold for price-based alerts (e.g., 10.0 = 10%).
        is_active: Whether the alert is currently active.
        last_triggered: Timestamp of the last alert trigger.
        created_at: Record creation timestamp.
        user: Related User record.
        product: Related CompetitorProduct (optional).
        competitor: Related Competitor (optional).
        history: Related AlertHistory entries.
    """

    __tablename__ = "price_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    competitor_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competitor_products.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    competitor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competitors.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    last_triggered: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")
    product: Mapped["CompetitorProduct | None"] = relationship(
        "CompetitorProduct",
        back_populates="alerts",
        lazy="selectin",
        foreign_keys=[competitor_product_id],
    )
    competitor: Mapped["Competitor | None"] = relationship(
        "Competitor",
        back_populates="alerts",
        lazy="selectin",
        foreign_keys=[competitor_id],
    )
    history: Mapped[list["AlertHistory"]] = relationship(
        "AlertHistory",
        back_populates="alert",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AlertHistory(Base):
    """
    A record of a triggered alert instance.

    Stores the alert message and contextual data (price change amount,
    product details, etc.) for historical reference.

    Attributes:
        id: Unique identifier (UUID v4).
        alert_id: Foreign key to the parent PriceAlert.
        message: Human-readable description of what triggered the alert.
        data: JSON dict with contextual data (old_price, new_price, etc.).
        created_at: Timestamp when the alert was triggered.
        alert: Related PriceAlert record.
    """

    __tablename__ = "alert_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("price_alerts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(String(1024), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    alert: Mapped["PriceAlert"] = relationship(
        "PriceAlert", back_populates="history", lazy="selectin"
    )


# Avoid circular imports
from app.models.competitor import Competitor, CompetitorProduct  # noqa: E402
from app.models.user import User  # noqa: E402
