"""Segment and SegmentCustomer database models.

Defines the ``segments`` and ``segment_customers`` tables for grouping
customers into targetable segments. Segments can be manual (hand-picked
customers) or automatic (rule-based dynamic membership).

**For Developers:**
    Import these models via ``app.models`` so that Alembic picks up schema
    changes automatically. Manual segments use the ``segment_customers``
    junction table for explicit membership. Automatic segments store filter
    rules as a JSON column and dynamically evaluate membership at query
    time (the ``customer_count`` is a denormalized cache).

**For QA Engineers:**
    - ``SegmentType`` restricts the type to ``manual`` or ``automatic``.
    - For manual segments, customers are explicitly added to
      ``segment_customers``.
    - For automatic segments, the ``rules`` JSON column stores filter
      criteria (e.g. ``{"total_spent_gte": 100, "country": "US"}``).
    - ``customer_count`` is a cached count that should be refreshed
      periodically or on membership changes.
    - The unique constraint on (``segment_id``, ``customer_id``) prevents
      adding the same customer to a segment twice.

**For End Users:**
    Segments help you organize your customers into groups for targeted
    marketing and analysis. Create manual segments by hand-picking
    customers, or set up automatic segments with rules (e.g. "customers
    who spent over $100" or "customers in the US"). Use segments for
    email campaigns, discount targeting, and customer insights.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SegmentType(str, enum.Enum):
    """Types of customer segments.

    Attributes:
        manual: Membership is explicitly managed by the store owner.
        automatic: Membership is dynamically determined by filter rules.
    """

    manual = "manual"
    automatic = "automatic"


class Segment(Base):
    """SQLAlchemy model representing a customer segment.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the segment to its store.
        name: Display name of the segment.
        description: Optional description of the segment's purpose.
        segment_type: Whether membership is manual or automatic.
        rules: JSON object containing filter rules for automatic segments
            (null for manual segments).
        customer_count: Cached count of customers in this segment.
        created_at: Timestamp when the segment was created (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
        store: Relationship to the Store.
        customers: Many-to-many relationship to User records via junction table.
    """

    __tablename__ = "segments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    segment_type: Mapped[SegmentType] = mapped_column(
        Enum(SegmentType), nullable=False
    )
    rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    customer_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    store = relationship("Store", backref="segments", lazy="selectin")
    customers = relationship(
        "User",
        secondary="segment_customers",
        backref="segments",
        lazy="selectin",
    )


class SegmentCustomer(Base):
    """Junction table linking segments to customers (many-to-many).

    Used for manual segment membership. Each record represents a customer
    explicitly added to a segment.

    Attributes:
        id: Unique identifier (UUID v4).
        segment_id: Foreign key to the segment.
        customer_id: Foreign key to the customer (user).
        added_at: Timestamp when the customer was added to the segment.
    """

    __tablename__ = "segment_customers"
    __table_args__ = (
        UniqueConstraint(
            "segment_id", "customer_id", name="uq_segment_customers_pair"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("segments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
