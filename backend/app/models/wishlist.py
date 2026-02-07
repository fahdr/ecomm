"""WishlistItem database model.

Defines the ``wishlist_items`` table for customer product wishlists.
Each wishlist item links a customer to a product they want to save
for later.

**For Developers:**
    Import this model via ``app.models`` so that Alembic picks up schema
    changes automatically. The unique constraint on ``(customer_id, product_id)``
    prevents duplicate wishlist entries.

**For QA Engineers:**
    - A customer can only wishlist each product once (409 on duplicate).
    - Deleting a customer cascades to their wishlist items.
    - Deleting a product cascades to all wishlist items referencing it.

**For End Users:**
    Save products to your wishlist to keep track of items you're
    interested in buying later.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WishlistItem(Base):
    """SQLAlchemy model representing a wishlisted product for a customer.

    Attributes:
        id: Unique identifier (UUID v4).
        customer_id: Foreign key linking to the customer.
        product_id: Foreign key linking to the wishlisted product.
        created_at: Timestamp when the item was added to the wishlist.
        customer: Relationship to the Customer.
        product: Relationship to the Product.
    """

    __tablename__ = "wishlist_items"
    __table_args__ = (
        UniqueConstraint(
            "customer_id", "product_id", name="uq_wishlist_customer_product"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer = relationship("Customer", backref="wishlist_items", lazy="selectin")
    product = relationship("Product", lazy="selectin")
