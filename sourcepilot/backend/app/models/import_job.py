"""
Import job model for tracking product import operations.

An ImportJob represents a single product import from a supplier platform
(AliExpress, CJ Dropship, Spocket, or manual entry) into the user's
dropshipping store. Jobs progress through a lifecycle of pending -> running ->
completed (or failed / cancelled).

For Developers:
    The ``product_data`` JSON column stores raw supplier data fetched during
    import. The ``config`` JSON column holds import settings like markup
    percentage, tags, and compare-at discount. The ``progress_percent``
    field enables real-time progress tracking in the dashboard.

For Project Managers:
    Import jobs are the primary metered resource. Each plan tier limits the
    number of imports per billing period (see constants/plans.py).

For QA Engineers:
    Test the full lifecycle: create job -> Celery task processes -> status
    transitions. Verify plan limits are enforced. Test cancellation of
    in-progress jobs.

For End Users:
    When you import a product from a supplier, an import job tracks the
    progress. You can view status, cancel pending jobs, and retry failed ones.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ImportJobStatus(str, enum.Enum):
    """
    Status values for an import job lifecycle.

    Attributes:
        pending: Job created, waiting for worker pickup.
        running: Worker is actively processing the import.
        completed: Import finished successfully, product created.
        failed: Import encountered an error.
        cancelled: User or system cancelled the import.
    """

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ImportSource(str, enum.Enum):
    """
    Supported supplier platforms for product imports.

    Attributes:
        aliexpress: AliExpress supplier marketplace.
        cjdropship: CJ Dropshipping fulfillment platform.
        spocket: Spocket supplier marketplace.
        manual: Manually entered product data.
    """

    aliexpress = "aliexpress"
    cjdropship = "cjdropship"
    spocket = "spocket"
    manual = "manual"


class ImportJob(Base):
    """
    A single product import operation from a supplier to a store.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the user who initiated the import.
        store_id: UUID of the target dropshipping store.
        source: Supplier platform the product is imported from.
        source_url: URL of the product on the supplier platform.
        source_product_id: Product identifier on the supplier platform.
        status: Current job lifecycle status.
        product_data: Raw supplier product data (JSON).
        config: Import configuration (markup, tags, etc.).
        error_message: Human-readable error if status is 'failed'.
        created_product_id: UUID of the created product in the store.
        progress_percent: Import progress from 0 to 100.
        created_at: Job creation timestamp.
        updated_at: Last modification timestamp.
        history: Related ImportHistory entries for audit trail.
    """

    __tablename__ = "import_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    source: Mapped[ImportSource] = mapped_column(
        Enum(ImportSource), nullable=False, index=True
    )
    source_url: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )
    source_product_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    status: Mapped[ImportJobStatus] = mapped_column(
        Enum(ImportJobStatus), default=ImportJobStatus.pending, nullable=False, index=True
    )
    product_data: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    config: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )
    created_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    progress_percent: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", backref="import_jobs", lazy="selectin")
    history: Mapped[list["ImportHistory"]] = relationship(
        "ImportHistory",
        back_populates="import_job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
