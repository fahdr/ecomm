"""Domain purchase business logic.

Provides high-level operations for searching, purchasing, renewing, and
managing domain names through the platform. Integrates with the DNS
management service for automatic DNS and SSL configuration after purchase.

**For Developers:**
    This service coordinates between the domain registrar abstraction,
    the DNS management service, and the database models. It manages
    the full lifecycle of domain purchases from search to renewal.

**For QA Engineers:**
    - ``search_available_domains`` returns results from the registrar.
    - ``purchase_domain`` creates a CustomDomain record with all purchase
      fields populated (purchase_provider, purchase_date, expiry_date,
      registrar_order_id, is_purchased=True).
    - After purchase, DNS is auto-configured and SSL is provisioned.
    - ``renew_domain`` updates the expiry_date and registrar_order_id.
    - ``toggle_auto_renew`` flips the auto_renew flag on the domain.

**For Project Managers:**
    This service powers Feature 7 (Domain Purchasing), enabling merchants
    to search for, purchase, and manage domain names directly through
    the platform dashboard.

**For End Users:**
    Search for and purchase domain names right from your dashboard. The
    platform handles DNS configuration and SSL certificates automatically
    after purchase. You can also set up auto-renewal so your domain never
    expires unexpectedly.
"""

import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import CustomDomain, DomainStatus
from app.services.domain_registrar.base import DomainSearchResult
from app.services.domain_registrar.factory import get_domain_provider


async def search_available_domains(
    query: str,
    tlds: list[str] | None = None,
) -> list[dict]:
    """Search for available domain names across multiple TLDs.

    Args:
        query: The domain name query (without TLD extension).
        tlds: List of TLD extensions to search. Defaults to
            ["com", "io", "store"].

    Returns:
        A list of dicts with domain availability and pricing info.
        Each dict has: domain, available, price, currency, period_years.
    """
    if tlds is None:
        tlds = ["com", "io", "store"]

    provider = get_domain_provider()
    results = await provider.search_domains(query, tlds)

    return [
        {
            "domain": r.domain,
            "available": r.available,
            "price": str(r.price),
            "currency": r.currency,
            "period_years": r.period_years,
        }
        for r in results
    ]


async def purchase_domain(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    domain: str,
    years: int = 1,
    contact_info: dict | None = None,
) -> dict:
    """Purchase a domain and configure it for a store.

    Performs the full purchase flow:
    1. Purchase domain via registrar.
    2. Create or update CustomDomain record with purchase metadata.
    3. Set nameservers to point to the platform.
    4. Auto-configure DNS records (A + CNAME).
    5. Provision SSL certificate.

    Args:
        db: Async database session.
        store_id: UUID of the store to attach the domain to.
        user_id: UUID of the purchasing user.
        domain: The fully-qualified domain name to purchase.
        years: Registration period in years (default 1).
        contact_info: Registrant contact information (optional).

    Returns:
        A dict with domain, order_id, status, expiry_date,
        auto_dns_configured, and ssl_provisioned.

    Raises:
        ValueError: If the store doesn't exist or belongs to another user,
            or if the domain is already in use.
    """
    from app.config import settings
    from app.models.store import Store, StoreStatus
    from app.services import dns_management_service

    # Verify store ownership
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if store is None or store.status == StoreStatus.deleted:
        raise ValueError("Store not found")
    if store.user_id != user_id:
        raise ValueError("Store not found")

    # Check if store already has a domain
    existing = await db.execute(
        select(CustomDomain).where(CustomDomain.store_id == store_id)
    )
    existing_domain = existing.scalar_one_or_none()
    if existing_domain is not None:
        raise ValueError(
            "This store already has a custom domain. "
            "Delete the existing domain first."
        )

    # Check if domain is used by another store
    domain_check = await db.execute(
        select(CustomDomain).where(CustomDomain.domain == domain.lower().strip())
    )
    if domain_check.scalar_one_or_none() is not None:
        raise ValueError(f"Domain '{domain}' is already in use")

    if contact_info is None:
        contact_info = {}

    # 1. Purchase via registrar
    provider = get_domain_provider()
    purchase_result = await provider.purchase_domain(domain, years, contact_info)

    if purchase_result.status != "success":
        raise ValueError(
            f"Domain purchase failed: {purchase_result.status}"
        )

    # 2. Create CustomDomain record
    mode = getattr(settings, "domain_provider_mode", "mock")
    verification_token = f"dropship-verify-{secrets.token_hex(16)}"

    custom_domain = CustomDomain(
        store_id=store_id,
        domain=domain.lower().strip(),
        verification_token=verification_token,
        status=DomainStatus.verified,
        verified_at=datetime.now(timezone.utc),
        purchase_provider=mode,
        purchase_date=datetime.now(timezone.utc),
        expiry_date=purchase_result.expiry_date,
        auto_renew=False,
        registrar_order_id=purchase_result.order_id,
        is_purchased=True,
    )
    db.add(custom_domain)
    await db.flush()
    await db.refresh(custom_domain)

    # 3. Set nameservers to platform
    platform_ns_str = getattr(
        settings, "platform_nameservers", "ns1.platform.app,ns2.platform.app"
    )
    nameservers = [ns.strip() for ns in platform_ns_str.split(",")]
    await provider.set_nameservers(domain, nameservers)

    # 4. Auto-configure DNS
    auto_dns_configured = False
    try:
        await dns_management_service.auto_configure_dns(db, custom_domain.id)
        auto_dns_configured = True
    except Exception:
        pass  # DNS config failure shouldn't block the purchase

    # 5. Provision SSL
    ssl_provisioned = False
    try:
        await dns_management_service.provision_ssl(db, custom_domain.id)
        ssl_provisioned = True
    except Exception:
        pass  # SSL failure shouldn't block the purchase

    await db.refresh(custom_domain)

    return {
        "domain": custom_domain.domain,
        "order_id": purchase_result.order_id,
        "status": purchase_result.status,
        "expiry_date": (
            custom_domain.expiry_date.isoformat()
            if custom_domain.expiry_date
            else None
        ),
        "auto_dns_configured": auto_dns_configured,
        "ssl_provisioned": ssl_provisioned,
    }


async def renew_domain(
    db: AsyncSession,
    domain_id: uuid.UUID,
    years: int = 1,
) -> dict:
    """Renew a domain registration.

    Args:
        db: Async database session.
        domain_id: UUID of the CustomDomain to renew.
        years: Number of years to renew for (default 1).

    Returns:
        A dict with domain, new_expiry_date, and order_id.

    Raises:
        ValueError: If the domain is not found or is not a purchased domain.
    """
    result = await db.execute(
        select(CustomDomain).where(CustomDomain.id == domain_id)
    )
    domain = result.scalar_one_or_none()
    if domain is None:
        raise ValueError("Domain not found")
    if not domain.is_purchased:
        raise ValueError("This domain was not purchased through the platform")

    provider = get_domain_provider()
    renew_result = await provider.renew_domain(domain.domain, years)

    if renew_result.status != "success":
        raise ValueError(f"Domain renewal failed: {renew_result.status}")

    domain.expiry_date = renew_result.expiry_date
    domain.registrar_order_id = renew_result.order_id

    await db.flush()
    await db.refresh(domain)

    return {
        "domain": domain.domain,
        "new_expiry_date": (
            domain.expiry_date.isoformat() if domain.expiry_date else None
        ),
        "order_id": renew_result.order_id,
    }


async def list_owned_domains(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[dict]:
    """List all domains purchased by a user.

    Finds all CustomDomain records where is_purchased=True and the
    associated store belongs to the user.

    Args:
        db: Async database session.
        user_id: UUID of the user.

    Returns:
        A list of dicts with domain purchase information.
    """
    from app.models.store import Store, StoreStatus

    result = await db.execute(
        select(CustomDomain)
        .join(Store, CustomDomain.store_id == Store.id)
        .where(
            Store.user_id == user_id,
            Store.status != StoreStatus.deleted,
            CustomDomain.is_purchased.is_(True),
        )
    )
    domains = list(result.scalars().all())

    return [
        {
            "id": str(d.id),
            "store_id": str(d.store_id),
            "domain": d.domain,
            "status": d.status.value if hasattr(d.status, "value") else d.status,
            "purchase_provider": d.purchase_provider,
            "purchase_date": d.purchase_date.isoformat() if d.purchase_date else None,
            "expiry_date": d.expiry_date.isoformat() if d.expiry_date else None,
            "auto_renew": d.auto_renew,
            "is_purchased": d.is_purchased,
            "ssl_provisioned": d.ssl_provisioned,
            "auto_dns_configured": d.auto_dns_configured,
        }
        for d in domains
    ]


async def toggle_auto_renew(
    db: AsyncSession,
    domain_id: uuid.UUID,
    auto_renew: bool,
) -> dict:
    """Toggle auto-renewal for a purchased domain.

    Args:
        db: Async database session.
        domain_id: UUID of the CustomDomain.
        auto_renew: Whether to enable or disable auto-renewal.

    Returns:
        A dict with domain name and the new auto_renew status.

    Raises:
        ValueError: If the domain is not found or is not a purchased domain.
    """
    result = await db.execute(
        select(CustomDomain).where(CustomDomain.id == domain_id)
    )
    domain = result.scalar_one_or_none()
    if domain is None:
        raise ValueError("Domain not found")
    if not domain.is_purchased:
        raise ValueError("This domain was not purchased through the platform")

    domain.auto_renew = auto_renew
    await db.flush()
    await db.refresh(domain)

    return {
        "domain": domain.domain,
        "auto_renew": domain.auto_renew,
    }
