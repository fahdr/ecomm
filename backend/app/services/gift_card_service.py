"""Gift card business logic.

Handles gift card creation, validation, charging, and refunding. Gift
cards act as store-credit instruments with a unique code, balance
tracking, and a full transaction history.

**For Developers:**
    Gift card codes are generated using ``secrets`` for cryptographic
    randomness in the format ``GC-XXXX-XXXX-XXXX``. Balance is tracked
    as ``current_balance`` and decremented via ``charge_gift_card``.
    Every charge and refund creates a ``GiftCardTransaction`` audit
    record for reconciliation.

**For QA Engineers:**
    - ``generate_gift_card_code`` produces a 16-character alphanumeric
      code formatted as ``GC-XXXX-XXXX-XXXX``.
    - ``create_gift_card`` sets ``current_balance`` equal to
      ``initial_balance``.
    - ``validate_gift_card`` checks active status, expiry, and positive
      balance.
    - ``charge_gift_card`` prevents overdraft (amount > balance).
    - ``refund_gift_card`` adds credit back to the card balance.
    - ``disable_gift_card`` sets ``status`` to ``disabled``.

**For Project Managers:**
    This service powers Feature 20 (Gift Cards) from the backlog. It
    provides a store-credit mechanism that can be sold or given to
    customers and redeemed at checkout.

**For End Users:**
    Create gift cards for your store that customers can use at checkout.
    Gift cards have a balance that decreases with each purchase. You can
    set expiry dates and disable cards if needed.
"""

import secrets
import string
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store, StoreStatus


# ---------------------------------------------------------------------------
# Gift card models -- import conditionally as models may be created by
# another agent.
# ---------------------------------------------------------------------------
try:
    from app.models.gift_card import GiftCard, GiftCardStatus, GiftCardTransaction
except ImportError:
    GiftCard = None  # type: ignore[assignment,misc]
    GiftCardTransaction = None  # type: ignore[assignment,misc]


def generate_gift_card_code() -> str:
    """Generate a unique, human-readable gift card code.

    Produces a 12-character alphanumeric code formatted as
    ``GC-XXXX-XXXX-XXXX`` where each X is an uppercase letter or digit.
    Uses ``secrets`` for cryptographic randomness.

    Returns:
        A gift card code string in the format ``GC-XXXX-XXXX-XXXX``.
    """
    chars = string.ascii_uppercase + string.digits
    segments = [
        "".join(secrets.choice(chars) for _ in range(4))
        for _ in range(3)
    ]
    return f"GC-{'-'.join(segments)}"


async def _verify_store_ownership(
    db: AsyncSession, store_id: uuid.UUID, user_id: uuid.UUID
) -> Store:
    """Verify that a store exists and belongs to the given user.

    Args:
        db: Async database session.
        store_id: The UUID of the store.
        user_id: The requesting user's UUID.

    Returns:
        The Store ORM instance.

    Raises:
        ValueError: If the store doesn't exist, is deleted, or belongs
            to a different user.
    """
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if store is None or store.status == StoreStatus.deleted:
        raise ValueError("Store not found")
    if store.user_id != user_id:
        raise ValueError("Store not found")
    return store


async def create_gift_card(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    initial_balance: Decimal,
    customer_email: str | None = None,
    expires_at: datetime | None = None,
) -> "GiftCard":
    """Create a new gift card for a store.

    Generates a unique code and sets the current balance equal to the
    initial balance.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        initial_balance: The starting balance of the gift card.
        customer_email: Optional email of the recipient.
        expires_at: Optional expiry date/time.

    Returns:
        The newly created GiftCard ORM instance.

    Raises:
        ValueError: If the store doesn't exist, belongs to another user,
            or the initial balance is not positive.
    """
    await _verify_store_ownership(db, store_id, user_id)

    if initial_balance <= Decimal("0.00"):
        raise ValueError("Initial balance must be greater than zero")

    # Generate a unique code (retry if collision, though extremely unlikely)
    code = generate_gift_card_code()
    attempts = 0
    while attempts < 10:
        existing = await db.execute(
            select(GiftCard).where(
                GiftCard.store_id == store_id,
                GiftCard.code == code,
            )
        )
        if existing.scalar_one_or_none() is None:
            break
        code = generate_gift_card_code()
        attempts += 1

    gift_card = GiftCard(
        store_id=store_id,
        code=code,
        initial_balance=initial_balance,
        current_balance=initial_balance,
        customer_email=customer_email,
        expires_at=expires_at,
        status=GiftCardStatus.active,
    )
    db.add(gift_card)
    await db.flush()
    await db.refresh(gift_card)
    return gift_card


async def list_gift_cards(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list, int]:
    """List gift cards for a store with pagination.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        page: Page number (1-based).
        per_page: Number of items per page.

    Returns:
        A tuple of (gift cards list, total count).

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    query = select(GiftCard).where(GiftCard.store_id == store_id)
    count_query = select(func.count(GiftCard.id)).where(GiftCard.store_id == store_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(GiftCard.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    gift_cards = list(result.scalars().all())

    return gift_cards, total


async def get_gift_card(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    gift_card_id: uuid.UUID,
) -> "GiftCard":
    """Retrieve a single gift card, verifying store ownership.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        gift_card_id: The UUID of the gift card to retrieve.

    Returns:
        The GiftCard ORM instance.

    Raises:
        ValueError: If the store or gift card doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(GiftCard).where(
            GiftCard.id == gift_card_id,
            GiftCard.store_id == store_id,
        )
    )
    gift_card = result.scalar_one_or_none()
    if gift_card is None:
        raise ValueError("Gift card not found")
    return gift_card


async def validate_gift_card(
    db: AsyncSession,
    store_id: uuid.UUID,
    code: str,
) -> dict:
    """Validate a gift card code for use at checkout.

    Checks that the code exists, the card is active, not expired, and
    has a positive balance. Does NOT require store ownership as this
    is called on behalf of customers.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        code: The gift card code to validate.

    Returns:
        A dict with ``valid`` (bool), ``balance`` (Decimal or None),
        and ``message`` (str).
    """
    result = await db.execute(
        select(GiftCard).where(
            GiftCard.store_id == store_id,
            GiftCard.code == code.upper(),
        )
    )
    gift_card = result.scalar_one_or_none()

    if gift_card is None:
        return {"valid": False, "balance": None, "message": "Invalid gift card code"}

    if gift_card.status != GiftCardStatus.active:
        return {"valid": False, "balance": None, "message": "This gift card is not active"}

    now = datetime.now(timezone.utc)
    if gift_card.expires_at and now > gift_card.expires_at:
        return {"valid": False, "balance": None, "message": "This gift card has expired"}

    if gift_card.current_balance <= Decimal("0.00"):
        return {
            "valid": False,
            "balance": Decimal("0.00"),
            "message": "This gift card has no remaining balance",
        }

    return {
        "valid": True,
        "balance": gift_card.current_balance,
        "message": f"Gift card valid. Balance: ${gift_card.current_balance}",
    }


async def charge_gift_card(
    db: AsyncSession,
    store_id: uuid.UUID,
    code: str,
    amount: Decimal,
    order_id: uuid.UUID,
) -> "GiftCardTransaction":
    """Charge (debit) an amount from a gift card.

    Decrements the card's ``current_balance`` and creates a transaction
    record. Prevents overdraft by validating the amount does not exceed
    the remaining balance.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        code: The gift card code.
        amount: The amount to charge.
        order_id: The UUID of the order being paid.

    Returns:
        The GiftCardTransaction audit record.

    Raises:
        ValueError: If the gift card is not found, not valid, or the
            amount exceeds the available balance.
    """
    result = await db.execute(
        select(GiftCard).where(
            GiftCard.store_id == store_id,
            GiftCard.code == code.upper(),
        )
    )
    gift_card = result.scalar_one_or_none()
    if gift_card is None:
        raise ValueError("Gift card not found")

    if gift_card.status != GiftCardStatus.active:
        raise ValueError("Gift card is not active")

    now = datetime.now(timezone.utc)
    if gift_card.expires_at and now > gift_card.expires_at:
        raise ValueError("Gift card has expired")

    if amount > gift_card.current_balance:
        raise ValueError(
            f"Charge amount (${amount}) exceeds gift card balance "
            f"(${gift_card.current_balance})"
        )

    if amount <= Decimal("0.00"):
        raise ValueError("Charge amount must be greater than zero")

    # Debit the balance
    gift_card.current_balance -= amount

    # Create transaction record
    transaction = GiftCardTransaction(
        gift_card_id=gift_card.id,
        order_id=order_id,
        amount=-amount,  # Negative for debits
        transaction_type="charge",
        note=f"Charged for order",
    )
    db.add(transaction)
    await db.flush()
    await db.refresh(transaction)
    return transaction


async def refund_gift_card(
    db: AsyncSession,
    gift_card_id: uuid.UUID,
    amount: Decimal,
    order_id: uuid.UUID,
    note: str | None = None,
) -> "GiftCardTransaction":
    """Refund (credit) an amount back to a gift card.

    Increments the card's ``current_balance`` and creates a transaction
    record.

    Args:
        db: Async database session.
        gift_card_id: The UUID of the gift card.
        amount: The amount to refund (must be positive).
        order_id: The UUID of the order being refunded.
        note: Optional note explaining the refund.

    Returns:
        The GiftCardTransaction audit record.

    Raises:
        ValueError: If the gift card is not found or the amount is not
            positive.
    """
    result = await db.execute(
        select(GiftCard).where(GiftCard.id == gift_card_id)
    )
    gift_card = result.scalar_one_or_none()
    if gift_card is None:
        raise ValueError("Gift card not found")

    if amount <= Decimal("0.00"):
        raise ValueError("Refund amount must be greater than zero")

    # Credit the balance
    gift_card.current_balance += amount

    transaction = GiftCardTransaction(
        gift_card_id=gift_card.id,
        order_id=order_id,
        amount=amount,  # Positive for credits
        transaction_type="refund",
        note=note or "Refund credited",
    )
    db.add(transaction)
    await db.flush()
    await db.refresh(transaction)
    return transaction


async def disable_gift_card(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    gift_card_id: uuid.UUID,
) -> "GiftCard":
    """Disable a gift card so it can no longer be used.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        gift_card_id: The UUID of the gift card to disable.

    Returns:
        The updated GiftCard ORM instance with ``status`` set to ``disabled``.

    Raises:
        ValueError: If the store or gift card doesn't exist, or the store
            belongs to another user.
    """
    gift_card = await get_gift_card(db, store_id, user_id, gift_card_id)
    if gift_card.status == GiftCardStatus.disabled:
        raise ValueError("Gift card is already disabled")
    gift_card.status = GiftCardStatus.disabled
    await db.flush()
    await db.refresh(gift_card)
    return gift_card
