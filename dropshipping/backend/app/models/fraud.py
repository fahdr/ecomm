"""FraudCheck database model.

Defines the ``fraud_checks`` table for recording automated fraud risk
assessments on orders. Each check evaluates an order's risk level and
captures the signals that contributed to the score.

**For Developers:**
    Import this model via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``signals`` JSON column stores a list of
    detected risk indicators (e.g. ``["ip_mismatch", "high_velocity",
    "disposable_email"]``). The ``risk_score`` is a normalized value from
    0.00 to 100.00. The ``reviewed_by`` foreign key uses SET NULL so that
    the review record persists even if the admin account is deleted.

**For QA Engineers:**
    - ``FraudRiskLevel`` restricts the assessment to ``low``, ``medium``,
      ``high``, or ``critical``.
    - ``risk_score`` ranges from 0.00 (no risk) to 100.00 (maximum risk).
    - ``signals`` is a JSON array of string identifiers for each detected
      risk factor.
    - ``is_flagged`` indicates the order was automatically held for manual
      review.
    - ``reviewed_by`` and ``reviewed_at`` are populated when an admin
      manually reviews the flagged order.
    - Each order should have at most one fraud check record.

**For End Users:**
    Fraud detection automatically analyzes each order for suspicious
    activity. Orders deemed risky are flagged for your review before
    fulfillment. You can see the risk score, detected signals, and
    approve or reject flagged orders from your dashboard.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FraudRiskLevel(str, enum.Enum):
    """Risk assessment levels for an order.

    Attributes:
        low: Minimal risk, order can be fulfilled normally.
        medium: Some risk indicators detected, monitor the order.
        high: Significant risk, order should be reviewed before fulfillment.
        critical: Very high risk, order should be held and investigated.
    """

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class FraudCheck(Base):
    """SQLAlchemy model representing a fraud risk assessment for an order.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the check to its store.
        order_id: Foreign key linking the check to the assessed order.
        risk_level: The overall risk classification (low, medium, high,
            critical).
        risk_score: Numeric risk score from 0.00 to 100.00.
        signals: JSON array of detected risk signal identifiers.
        is_flagged: Whether the order was automatically flagged for review.
        reviewed_by: Optional foreign key to the admin who reviewed the
            flagged order.
        reviewed_at: Timestamp when the manual review was completed.
        notes: Optional admin notes about the review decision.
        created_at: Timestamp when the check was performed (DB server time).
        store: Relationship to the Store.
        order: Relationship to the Order.
        reviewer: Relationship to the User who reviewed (nullable).
    """

    __tablename__ = "fraud_checks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    risk_level: Mapped[FraudRiskLevel] = mapped_column(
        Enum(FraudRiskLevel), nullable=False
    )
    risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    signals: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    store = relationship("Store", backref="fraud_checks", lazy="selectin")
    order = relationship("Order", backref="fraud_check", uselist=False, lazy="selectin")
    reviewer = relationship("User", backref="fraud_reviews", lazy="selectin")
