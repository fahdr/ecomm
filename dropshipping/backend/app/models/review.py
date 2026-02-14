"""Review database model.

Defines the ``reviews`` table for customer product reviews. Reviews are
scoped to a store and linked to a specific product. They support a
moderation workflow via the ``status`` field.

**For Developers:**
    Import this model via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``store_id`` foreign key scopes reviews to
    a store, while ``product_id`` links to the reviewed product.
    ``customer_id`` is a SET NULL foreign key so that reviews persist even
    if the customer account is deleted. The ``is_verified_purchase`` flag
    should be set programmatically by checking if the customer has a
    completed order containing the product.

**For QA Engineers:**
    - ``ReviewStatus`` restricts moderation state to ``pending``,
      ``approved``, or ``rejected``.
    - ``rating`` is an integer from 1 to 5 (star rating).
    - Only ``approved`` reviews should appear on the public storefront.
    - ``is_verified_purchase`` indicates the reviewer actually bought the
      product and should be displayed as a badge.
    - ``customer_name`` and ``customer_email`` are captured at review time
      so the review remains complete even if the customer account is deleted.

**For End Users:**
    Reviews let your customers share their experience with products. As a
    store owner, you can moderate reviews (approve or reject) before they
    appear publicly. Verified purchase badges help build trust with
    prospective buyers.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReviewStatus(str, enum.Enum):
    """Moderation states for a product review.

    Attributes:
        pending: Review submitted but not yet moderated.
        approved: Review approved and visible on the storefront.
        rejected: Review rejected and hidden from the storefront.
    """

    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Review(Base):
    """SQLAlchemy model representing a customer product review.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the review to its store.
        product_id: Foreign key linking the review to the reviewed product.
        customer_id: Optional foreign key to the customer's user account.
        customer_name: Display name of the reviewer at time of submission.
        customer_email: Email of the reviewer at time of submission.
        rating: Star rating from 1 (worst) to 5 (best).
        title: Optional short summary of the review.
        body: Optional detailed review text.
        status: Moderation status (pending, approved, rejected).
        is_verified_purchase: Whether the reviewer has a confirmed purchase
            of this product.
        created_at: Timestamp when the review was created (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
        store: Relationship to the Store.
        product: Relationship to the Product being reviewed.
        customer: Relationship to the User who wrote the review (nullable).
    """

    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.pending, nullable=False
    )
    is_verified_purchase: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
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

    store = relationship("Store", backref="reviews", lazy="selectin")
    product = relationship("Product", backref="reviews", lazy="selectin")
    customer = relationship("User", backref="reviews", lazy="selectin")
