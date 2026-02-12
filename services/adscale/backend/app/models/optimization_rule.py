"""
Optimization Rule model for automated campaign management.

Stores user-defined rules that automatically adjust campaigns based on
performance metrics. Rules evaluate conditions against campaign metrics
and execute actions when thresholds are met.

For Developers:
    Rules are evaluated periodically by Celery beat tasks. The `conditions`
    field is a JSON dict specifying what metric to check and the comparison
    operator. The `rule_type` determines the action taken when triggered.
    `threshold` is the numeric value the condition is compared against.

For QA Engineers:
    Test rule CRUD, threshold evaluation logic, execution counting,
    and the execute-now endpoint. Verify that rules only trigger
    when conditions are met.

For Project Managers:
    Optimization rules automate campaign management — for example,
    automatically pausing campaigns with low ROAS or increasing budget
    for high-performing campaigns.

For End Users:
    Set up optimization rules to automate your campaign management.
    Rules can pause underperforming campaigns, scale winners, or
    adjust bids based on your performance targets.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RuleType(str, enum.Enum):
    """
    Types of automated optimization actions.

    Attributes:
        pause_low_roas: Pause campaigns with ROAS below threshold.
        scale_high_roas: Increase budget for campaigns with ROAS above threshold.
        adjust_bid: Adjust bid amounts based on performance.
        increase_budget: Increase daily budget by a percentage when performing well.
    """

    pause_low_roas = "pause_low_roas"
    scale_high_roas = "scale_high_roas"
    adjust_bid = "adjust_bid"
    increase_budget = "increase_budget"


class OptimizationRule(Base):
    """
    User-defined automation rule for campaign optimization.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        name: Human-readable rule name.
        rule_type: The type of action this rule performs.
        conditions: JSON dict with evaluation conditions (metric, operator, etc.).
        threshold: Numeric threshold value for the rule condition.
        is_active: Whether the rule is currently enabled.
        last_executed: Timestamp of last successful execution (nullable).
        executions_count: Total number of times this rule has been triggered.
        created_at: Record creation timestamp.
        user: Related User record.
    """

    __tablename__ = "optimization_rules"

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
    rule_type: Mapped[RuleType] = mapped_column(Enum(RuleType), nullable=False)
    conditions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_executed: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    executions_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User", backref="optimization_rules", lazy="selectin")
