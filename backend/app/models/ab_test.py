"""ABTest and ABTestVariant database models.

Defines the ``ab_tests`` and ``ab_test_variants`` tables for running
split-testing experiments on the storefront. Each test has multiple
variants (including a control) and tracks impressions, conversions, and
revenue to determine a statistical winner.

**For Developers:**
    Import these models via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``metric`` string identifies which KPI the
    test measures (e.g. "conversion_rate", "avg_order_value"). Variant
    assignment logic should use the ``weight`` percentages to randomly
    bucket visitors. The ``is_control`` flag marks the baseline variant.

**For QA Engineers:**
    - ``ABTestStatus`` restricts the lifecycle to ``draft``, ``running``,
      ``paused``, or ``completed``.
    - Each test must have at least two variants (one control + one or more
      treatments).
    - ``weight`` values across variants for a test should sum to 100.
    - ``impressions`` counts how many visitors saw the variant.
    - ``conversions`` counts how many visitors completed the target action.
    - ``revenue`` tracks the total revenue attributed to the variant.
    - ``started_at`` and ``ended_at`` define the experiment window.

**For End Users:**
    A/B tests let you experiment with different versions of your
    storefront to find what works best. Create a test, define variants
    (e.g. different headlines or layouts), and the system will
    automatically split your visitors between them. Track conversion
    rates and revenue to pick the winning version with confidence.
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
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ABTestStatus(str, enum.Enum):
    """Lifecycle states for an A/B test.

    Attributes:
        draft: Test is being configured and not yet live.
        running: Test is actively splitting traffic between variants.
        paused: Test is temporarily stopped but can be resumed.
        completed: Test has ended and a winner has been determined.
    """

    draft = "draft"
    running = "running"
    paused = "paused"
    completed = "completed"


class ABTest(Base):
    """SQLAlchemy model representing an A/B test experiment.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the test to its store.
        name: Human-readable name for the experiment.
        description: Optional longer description of what is being tested.
        status: Current lifecycle status (draft, running, paused, completed).
        metric: The key metric being measured (e.g. "conversion_rate").
        started_at: Timestamp when the test was activated (null if draft).
        ended_at: Timestamp when the test was completed (null if ongoing).
        created_at: Timestamp when the test was created (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
        store: Relationship to the Store.
        variants: One-to-many relationship to ABTestVariant records.
    """

    __tablename__ = "ab_tests"

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
    status: Mapped[ABTestStatus] = mapped_column(
        Enum(ABTestStatus), default=ABTestStatus.draft, nullable=False
    )
    metric: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    store = relationship("Store", backref="ab_tests", lazy="selectin")
    variants = relationship(
        "ABTestVariant",
        back_populates="test",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ABTestVariant(Base):
    """SQLAlchemy model representing a variant within an A/B test.

    Each test has multiple variants including one control. Traffic is split
    among variants based on their weight percentages.

    Attributes:
        id: Unique identifier (UUID v4).
        test_id: Foreign key linking the variant to its parent test.
        name: Display name of the variant (e.g. "Control", "Variant A").
        description: Optional description of what differs in this variant.
        weight: Traffic allocation percentage (all variants should sum to 100).
        is_control: Whether this is the baseline variant.
        impressions: Count of visitors who were shown this variant.
        conversions: Count of visitors who completed the target action.
        revenue: Total revenue attributed to this variant.
        created_at: Timestamp when the variant was created.
        test: Relationship back to the parent ABTest.
    """

    __tablename__ = "ab_test_variants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ab_tests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    is_control: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=0, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    test = relationship("ABTest", back_populates="variants")

    @property
    def conversion_rate(self) -> float:
        """Compute the conversion rate for this variant.

        Returns:
            The ratio of conversions to impressions, or 0.0 if there
            are no impressions yet.
        """
        if self.impressions == 0:
            return 0.0
        return self.conversions / self.impressions
