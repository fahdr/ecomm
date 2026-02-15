"""
Import history model for auditing import job lifecycle events.

Each ImportHistory record logs a significant action taken on an import
job (created, failed, retried, cancelled). This provides an audit trail
for debugging and analytics.

For Developers:
    History entries are immutable once created. Use the ``details`` JSON
    column for action-specific metadata (e.g., error messages, retry
    counts, cancellation reasons).

For Project Managers:
    Import history enables analytics on import success rates, common
    failure patterns, and user behavior tracking.

For QA Engineers:
    Verify that history entries are created for each status transition.
    Test cascading deletes when the parent ImportJob is removed.

For End Users:
    View the activity log for each import to see what happened at each
    step of the process.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ImportHistory(Base):
    """
    An audit log entry for an import job lifecycle event.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the user who owns the import job.
        import_job_id: Foreign key to the parent ImportJob.
        action: Type of action logged (e.g., 'created', 'failed', 'retried', 'cancelled').
        details: Optional JSON metadata for the action.
        created_at: Timestamp when the action occurred.
        import_job: Back-reference to the parent ImportJob.
    """

    __tablename__ = "import_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    import_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    details: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    import_job = relationship(
        "ImportJob", back_populates="history"
    )
