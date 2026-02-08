"""Custom domain business logic.

Handles domain registration, DNS verification, and deletion for stores
that want to use a custom domain instead of the platform subdomain.

**For Developers:**
    Each store can have at most one custom domain. Domain verification
    uses a DNS TXT record check. In dev mode, verification is mocked
    and always succeeds. The ``verification_token`` is a random string
    that the store owner must add as a TXT record on their domain.

**For QA Engineers:**
    - ``create_domain`` validates the domain format (basic regex).
    - ``create_domain`` generates a random verification token.
    - ``verify_domain`` checks for the TXT record (mocked in dev).
    - ``delete_domain`` is a hard delete.
    - Only one domain per store is allowed.

**For Project Managers:**
    This service powers Feature 22 (Custom Domains) from the backlog.
    It enables store owners to use their own domain name for their
    storefront.

**For End Users:**
    Connect your own domain name to your store for a professional
    branded experience. Add a DNS TXT record for verification, then
    point your domain's DNS to our servers.
"""

import re
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store, StoreStatus


# ---------------------------------------------------------------------------
# CustomDomain model -- import conditionally.
# ---------------------------------------------------------------------------
try:
    from app.models.domain import CustomDomain, DomainStatus
except ImportError:
    CustomDomain = None  # type: ignore[assignment,misc]


# Basic domain format validation regex
_DOMAIN_REGEX = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,}$"
)


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


async def create_domain(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    domain: str,
) -> "CustomDomain":
    """Register a custom domain for a store.

    Validates the domain format, generates a verification token, and
    creates the domain record in ``pending`` verification status. Only
    one domain per store is allowed.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        domain: The custom domain name (e.g. ``"shop.example.com"``).

    Returns:
        The newly created CustomDomain ORM instance.

    Raises:
        ValueError: If the store doesn't exist, belongs to another user,
            the domain format is invalid, or the store already has a
            custom domain.
    """
    await _verify_store_ownership(db, store_id, user_id)

    # Validate domain format
    domain = domain.lower().strip()
    if not _DOMAIN_REGEX.match(domain):
        raise ValueError(
            f"Invalid domain format: '{domain}'. "
            f"Expected a valid domain like 'shop.example.com'."
        )

    # Check if store already has a domain
    existing = await db.execute(
        select(CustomDomain).where(CustomDomain.store_id == store_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError(
            "This store already has a custom domain. "
            "Delete the existing domain first."
        )

    # Check if domain is already used by another store
    domain_check = await db.execute(
        select(CustomDomain).where(CustomDomain.domain == domain)
    )
    if domain_check.scalar_one_or_none() is not None:
        raise ValueError(f"Domain '{domain}' is already in use")

    # Generate verification token
    verification_token = f"dropship-verify-{secrets.token_hex(16)}"

    custom_domain = CustomDomain(
        store_id=store_id,
        domain=domain,
        verification_token=verification_token,
        status=DomainStatus.pending,
    )
    db.add(custom_domain)
    await db.flush()
    await db.refresh(custom_domain)
    return custom_domain


async def get_domain(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
) -> "CustomDomain | None":
    """Get the custom domain for a store, if one exists.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        The CustomDomain ORM instance, or None if no domain is configured.

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(CustomDomain).where(CustomDomain.store_id == store_id)
    )
    return result.scalar_one_or_none()


async def verify_domain(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict:
    """Verify domain ownership by checking for a DNS TXT record.

    In development mode, verification always succeeds (mocked). In
    production, this would perform an actual DNS lookup for a TXT
    record matching the verification token.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        A dict with ``verified`` (bool), ``domain`` (str), and
        ``message`` (str).

    Raises:
        ValueError: If the store doesn't exist, belongs to another user,
            or no custom domain is configured.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(CustomDomain).where(CustomDomain.store_id == store_id)
    )
    custom_domain = result.scalar_one_or_none()
    if custom_domain is None:
        raise ValueError("No custom domain configured for this store")

    if custom_domain.status in (DomainStatus.verified, DomainStatus.active):
        return {
            "verified": True,
            "domain": custom_domain.domain,
            "message": "Domain is already verified",
        }

    # In dev mode, auto-verify. In production, perform DNS TXT lookup.
    # Production implementation would look like:
    #   import dns.resolver
    #   answers = dns.resolver.resolve(custom_domain.domain, 'TXT')
    #   for rdata in answers:
    #       if custom_domain.verification_token in str(rdata):
    #           verified = True
    #           break

    # Mock verification (always succeeds in dev)
    verified = True

    if verified:
        custom_domain.status = DomainStatus.verified
        await db.flush()
        await db.refresh(custom_domain)
        return {
            "verified": True,
            "domain": custom_domain.domain,
            "message": "Domain verified successfully",
        }

    return {
        "verified": False,
        "domain": custom_domain.domain,
        "message": (
            f"Verification failed. Add a TXT record with value "
            f"'{custom_domain.verification_token}' to your domain's DNS."
        ),
    }


async def delete_domain(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Delete the custom domain for a store.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Raises:
        ValueError: If the store doesn't exist, belongs to another user,
            or no custom domain is configured.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(CustomDomain).where(CustomDomain.store_id == store_id)
    )
    custom_domain = result.scalar_one_or_none()
    if custom_domain is None:
        raise ValueError("No custom domain configured for this store")

    await db.delete(custom_domain)
    await db.flush()
