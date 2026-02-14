"""Refund database model.

Defines the ``refunds`` table for tracking order refund requests and their
processing lifecycle. Refunds are scoped to a store and linked to a
specific order.

**For Developers:**
    Import this model via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``store_id`` foreign key scopes refunds to
    a store. The ``stripe_refund_id`` column stores the Stripe Refund
    object ID once the refund has been processed through Stripe. In
    dropshipping, refunds are typically handled by the store owner absorbing
    the cost rather than returning physical items to a supplier.

**For QA Engineers:**
    - ``RefundStatus`` restricts the lifecycle to ``pending``, ``approved``,
      ``rejected``, or ``completed``.
    - ``RefundReason`` restricts the customer's reason to ``defective``,
      ``wrong_item``, ``not_as_described``, ``changed_mind``, or ``other``.
    - ``amount`` is the refund amount in the store's currency and may be
      partial (less than the order total).
    - ``stripe_refund_id`` is populated only after Stripe processes the
      refund.
    - ``admin_notes`` is private and never shown to the customer.

**For End Users:**
    When a customer requests a refund, it appears in your Refunds dashboard.
    You can review the reason, approve or reject the request, and process
    the refund through Stripe. Since dropshipping stores don't hold
    inventory, there is no physical return process -- refunds are monetary.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RefundStatus(str, enum.Enum):
    """Lifecycle states for a refund request.

    Attributes:
        pending: Refund requested, awaiting store owner review.
        approved: Refund approved by the store owner, awaiting processing.
        rejected: Refund request was denied by the store owner.
        completed: Refund has been processed and funds returned to customer.
    """

    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    completed = "completed"


class RefundReason(str, enum.Enum):
    """Predefined reasons a customer may request a refund.

    Attributes:
        defective: Product arrived damaged or defective.
        wrong_item: Customer received the wrong product.
        not_as_described: Product did not match the listing description.
        changed_mind: Customer changed their mind about the purchase.
        other: Any reason not covered by the predefined options.
    """

    defective = "defective"
    wrong_item = "wrong_item"
    not_as_described = "not_as_described"
    changed_mind = "changed_mind"
    other = "other"


class Refund(Base):
    """SQLAlchemy model representing a refund request for an order.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the refund to its store.
        order_id: Foreign key linking the refund to the original order.
        customer_email: Email of the customer requesting the refund.
        reason: Predefined reason for the refund request.
        reason_details: Optional free-text elaboration on the reason.
        amount: The monetary amount to be refunded.
        status: Current lifecycle status (pending, approved, rejected,
            completed).
        stripe_refund_id: Stripe Refund object ID, populated after
            processing.
        admin_notes: Private notes from the store owner (not shown to
            customer).
        created_at: Timestamp when the refund was requested (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
        store: Relationship to the Store.
        order: Relationship to the Order being refunded.
    """

    __tablename__ = "refunds"

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
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[RefundReason] = mapped_column(
        Enum(RefundReason), nullable=False
    )
    reason_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[RefundStatus] = mapped_column(
        Enum(RefundStatus), default=RefundStatus.pending, nullable=False
    )
    stripe_refund_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    store = relationship("Store", backref="refunds", lazy="selectin")
    order = relationship("Order", backref="refunds", lazy="selectin")
