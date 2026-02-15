"""GiftCard and GiftCardTransaction database models.

Defines the ``gift_cards`` and ``gift_card_transactions`` tables for
managing store gift cards. Gift cards have a balance that decreases as
customers redeem them and can be tracked through a full transaction log.

**For Developers:**
    Import these models via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``code`` is unique per store (composite
    unique constraint). The ``current_balance`` should always equal
    ``initial_balance`` minus the sum of ``charge`` transactions plus the
    sum of ``refund`` and ``adjustment`` transactions. Use
    ``GiftCardTransaction`` for all balance modifications to maintain an
    audit trail.

**For QA Engineers:**
    - ``GiftCardStatus`` restricts the lifecycle to ``active``, ``used``,
      ``expired``, or ``disabled``.
    - ``TransactionType`` restricts transaction types to ``charge``,
      ``refund``, or ``adjustment``.
    - ``current_balance`` should never go below 0.
    - ``code`` is unique within a store but not globally.
    - ``issued_by`` tracks which admin created the gift card.
    - ``customer_email`` is who the gift card was sent to (the recipient).
    - ``expires_at`` is optional; if null the gift card never expires.
    - Each transaction records the ``amount`` changed, linked to an
      optional order for ``charge`` and ``refund`` types.

**For End Users:**
    Gift cards let your customers pre-pay for purchases or send store
    credit to others. As a store owner, you can issue gift cards with
    custom amounts, track their usage, and see a full transaction history.
    Customers enter gift card codes at checkout to apply their balance.
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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GiftCardStatus(str, enum.Enum):
    """Lifecycle states for a gift card.

    Attributes:
        active: Gift card has remaining balance and can be redeemed.
        used: Gift card balance has been fully consumed.
        expired: Gift card has passed its expiration date.
        disabled: Gift card was manually disabled by the store owner.
    """

    active = "active"
    used = "used"
    expired = "expired"
    disabled = "disabled"


class TransactionType(str, enum.Enum):
    """Types of gift card balance changes.

    Attributes:
        charge: Balance deducted when used at checkout.
        refund: Balance restored due to an order refund.
        adjustment: Manual balance adjustment by the store owner.
    """

    charge = "charge"
    refund = "refund"
    adjustment = "adjustment"


class GiftCard(Base):
    """SQLAlchemy model representing a store gift card.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the gift card to its store.
        code: Redemption code, unique within the store.
        initial_balance: The original loaded amount on the gift card.
        current_balance: The remaining available balance.
        status: Current lifecycle status (active, used, expired, disabled).
        customer_email: Optional email of the gift card recipient.
        issued_by: Optional foreign key to the admin user who created it.
        expires_at: Optional expiration date/time.
        created_at: Timestamp when the gift card was created (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
        store: Relationship to the Store.
        transactions: One-to-many relationship to GiftCardTransaction records.
    """

    __tablename__ = "gift_cards"
    __table_args__ = (
        UniqueConstraint("store_id", "code", name="uq_gift_cards_store_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[GiftCardStatus] = mapped_column(
        Enum(GiftCardStatus), default=GiftCardStatus.active, nullable=False
    )
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issued_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
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

    store = relationship("Store", backref="gift_cards", lazy="selectin")
    issuer = relationship("User", backref="issued_gift_cards", lazy="selectin")
    transactions = relationship(
        "GiftCardTransaction",
        back_populates="gift_card",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class GiftCardTransaction(Base):
    """Audit record tracking every balance change on a gift card.

    Attributes:
        id: Unique identifier (UUID v4).
        gift_card_id: Foreign key to the gift card.
        order_id: Optional foreign key to the order (for charge/refund).
        amount: The amount of the balance change.
        transaction_type: The type of change (charge, refund, adjustment).
        note: Optional human-readable note explaining the transaction.
        created_at: Timestamp when the transaction occurred.
        gift_card: Relationship back to the GiftCard.
        order: Relationship to the associated Order (if applicable).
    """

    __tablename__ = "gift_card_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    gift_card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gift_cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType), nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    gift_card = relationship("GiftCard", back_populates="transactions")
    order = relationship("Order", backref="gift_card_transactions", lazy="selectin")
