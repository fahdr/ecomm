"""
Flow and FlowExecution models for automated email sequences.

Flows define automated email sequences triggered by events (signup,
purchase, abandoned cart, etc.). Each flow has a series of steps
stored as JSON. FlowExecutions track individual contact progress
through a flow.

For Developers:
    - `steps` is a JSON list of step objects: each has a `type`
      (e.g. "email", "delay", "condition"), a `config` dict, and an index.
    - `trigger_config` stores trigger-specific settings (e.g. delay after
      event, filter conditions).
    - `stats` caches aggregate performance metrics for the flow.
    - FlowExecution tracks per-contact progress; `current_step` is 0-indexed.

For QA Engineers:
    Test: flow CRUD, activate/pause lifecycle, step validation,
    execution creation and progression, trigger type filtering.

For Project Managers:
    Flows are the automation engine. They drive engagement by sending
    the right email at the right time based on user behavior.

For End Users:
    Create automated email sequences that send based on triggers like
    new signups, purchases, or scheduled times.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Flow(Base):
    """
    An automated email flow (sequence) with trigger and steps.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        name: Flow display name.
        description: Optional description of the flow's purpose.
        trigger_type: Event that starts the flow
            ("signup", "purchase", "abandoned_cart", "custom", "scheduled").
        trigger_config: Trigger-specific configuration (JSON).
        status: Flow lifecycle state ("draft", "active", "paused").
        steps: Ordered list of flow step definitions (JSON).
        stats: Cached aggregate performance stats (JSON).
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        owner: Related User record.
        executions: Related FlowExecution records.
    """

    __tablename__ = "flows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    steps: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)
    stats: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", backref="flows", lazy="selectin")
    executions = relationship(
        "FlowExecution", back_populates="flow", cascade="all, delete-orphan",
        lazy="selectin",
    )


class FlowExecution(Base):
    """
    Tracks a single contact's progress through a flow.

    Created when a contact enters a flow; updated as they advance
    through each step. Completed when all steps are done or the
    execution is canceled/failed.

    Attributes:
        id: Unique identifier (UUID v4).
        flow_id: Foreign key to the parent flow.
        contact_id: Foreign key to the contact executing the flow.
        current_step: Zero-indexed step the contact is currently on.
        status: Execution state ("running", "completed", "failed", "canceled").
        started_at: When the contact entered the flow.
        completed_at: When the execution finished (if applicable).
        flow: Related Flow record.
    """

    __tablename__ = "flow_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    flow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("flows.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="running", nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    flow = relationship("Flow", back_populates="executions", lazy="selectin")
