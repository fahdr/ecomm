"""DNS management business logic.

Provides high-level operations for managing DNS records associated with
custom domains, including auto-configuration, SSL provisioning, and
propagation verification.

**For Developers:**
    This service coordinates between the DNS provider abstraction layer
    and the database models. It manages DnsRecordEntry rows and updates
    the CustomDomain model with DNS/SSL status. The DNS provider is
    obtained via ``get_dns_provider()`` factory.

**For QA Engineers:**
    - ``auto_configure_dns`` creates exactly 2 records (A + CNAME).
    - ``provision_ssl`` sets ssl_provisioned=True and populates
      ssl_certificate_id, ssl_provider, and ssl_expires_at.
    - ``verify_dns_propagation`` checks all managed records.
    - CRUD operations on dns_records use the DnsRecordEntry model.
    - Deleting a managed record is allowed but triggers a warning log.

**For Project Managers:**
    This service powers Feature 6 (DNS Management), enabling automatic
    DNS configuration when merchants connect a custom domain, as well
    as manual record management for advanced users.

**For End Users:**
    When you connect a custom domain, the platform automatically sets
    up the DNS records needed to route traffic to your store. You can
    also manually manage DNS records if you prefer more control.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import CustomDomain, DnsRecordEntry, DnsRecordType, DomainStatus
from app.services.dns.base import DnsRecord
from app.services.dns.factory import get_dns_provider


async def auto_configure_dns(
    db: AsyncSession,
    domain_id: uuid.UUID,
) -> list[DnsRecordEntry]:
    """Auto-create A and CNAME records pointing to the platform.

    Creates an A record for the root domain and a CNAME record for the
    ``www`` subdomain. Updates the CustomDomain with dns_provider,
    dns_zone_id, and auto_dns_configured status.

    Args:
        db: Async database session.
        domain_id: UUID of the CustomDomain to configure.

    Returns:
        List of created DnsRecordEntry instances (A + CNAME).

    Raises:
        ValueError: If the domain is not found.
    """
    from app.config import settings

    result = await db.execute(
        select(CustomDomain).where(CustomDomain.id == domain_id)
    )
    domain = result.scalar_one_or_none()
    if domain is None:
        raise ValueError("Domain not found")

    provider = get_dns_provider()
    zone_id = await provider.get_zone_id(domain.domain)

    platform_ip = getattr(settings, "platform_ip_address", "192.0.2.1")
    platform_cname = getattr(settings, "platform_cname_target", "proxy.platform.app")

    # Create A record for root domain
    a_record_data = DnsRecord(
        record_type=DnsRecordType.A,
        name="@",
        value=platform_ip,
        ttl=3600,
    )
    a_result = await provider.create_record(zone_id, a_record_data)

    a_entry = DnsRecordEntry(
        domain_id=domain_id,
        record_type=DnsRecordType.A,
        name="@",
        value=platform_ip,
        ttl=3600,
        provider_record_id=a_result.provider_record_id,
        is_managed=True,
    )
    db.add(a_entry)

    # Create CNAME record for www subdomain
    cname_record_data = DnsRecord(
        record_type=DnsRecordType.CNAME,
        name="www",
        value=platform_cname,
        ttl=3600,
    )
    cname_result = await provider.create_record(zone_id, cname_record_data)

    cname_entry = DnsRecordEntry(
        domain_id=domain_id,
        record_type=DnsRecordType.CNAME,
        name="www",
        value=platform_cname,
        ttl=3600,
        provider_record_id=cname_result.provider_record_id,
        is_managed=True,
    )
    db.add(cname_entry)

    # Update the CustomDomain
    mode = getattr(settings, "dns_provider_mode", "mock")
    domain.dns_provider = mode
    domain.dns_zone_id = zone_id
    domain.auto_dns_configured = True

    await db.flush()
    await db.refresh(a_entry)
    await db.refresh(cname_entry)
    await db.refresh(domain)

    return [a_entry, cname_entry]


async def provision_ssl(
    db: AsyncSession,
    domain_id: uuid.UUID,
) -> CustomDomain:
    """Mock SSL certificate provisioning for a custom domain.

    Sets ssl_provisioned=True and populates ssl_certificate_id,
    ssl_provider, and ssl_expires_at on the CustomDomain. In production,
    this would trigger real SSL certificate issuance via Let's Encrypt
    or a similar CA.

    Args:
        db: Async database session.
        domain_id: UUID of the CustomDomain.

    Returns:
        The updated CustomDomain instance.

    Raises:
        ValueError: If the domain is not found.
    """
    result = await db.execute(
        select(CustomDomain).where(CustomDomain.id == domain_id)
    )
    domain = result.scalar_one_or_none()
    if domain is None:
        raise ValueError("Domain not found")

    domain.ssl_provisioned = True
    domain.ssl_provider = "letsencrypt"
    domain.ssl_certificate_id = f"ssl-cert-{uuid.uuid4().hex[:12]}"
    domain.ssl_expires_at = datetime.now(timezone.utc) + timedelta(days=90)
    domain.status = DomainStatus.active

    await db.flush()
    await db.refresh(domain)
    return domain


async def verify_dns_propagation(
    db: AsyncSession,
    domain_id: uuid.UUID,
) -> dict:
    """Check if DNS records for a domain have propagated globally.

    Verifies each managed DNS record via the DNS provider's
    verify_propagation method.

    Args:
        db: Async database session.
        domain_id: UUID of the CustomDomain.

    Returns:
        A dict with ``propagated`` (bool), ``total_records`` (int),
        ``verified_records`` (int), and ``details`` (list of dicts).

    Raises:
        ValueError: If the domain is not found.
    """
    result = await db.execute(
        select(CustomDomain).where(CustomDomain.id == domain_id)
    )
    domain = result.scalar_one_or_none()
    if domain is None:
        raise ValueError("Domain not found")

    records_result = await db.execute(
        select(DnsRecordEntry).where(
            DnsRecordEntry.domain_id == domain_id,
            DnsRecordEntry.is_managed.is_(True),
        )
    )
    records = list(records_result.scalars().all())

    if not records:
        return {
            "propagated": False,
            "total_records": 0,
            "verified_records": 0,
            "details": [],
        }

    provider = get_dns_provider()
    details = []
    verified_count = 0

    for record in records:
        is_propagated = await provider.verify_propagation(
            domain.domain, record.record_type, record.value
        )
        details.append({
            "record_type": record.record_type.value,
            "name": record.name,
            "value": record.value,
            "propagated": is_propagated,
        })
        if is_propagated:
            verified_count += 1

    all_propagated = verified_count == len(records)

    return {
        "propagated": all_propagated,
        "total_records": len(records),
        "verified_records": verified_count,
        "details": details,
    }


async def create_dns_record(
    db: AsyncSession,
    domain_id: uuid.UUID,
    record_type: DnsRecordType,
    name: str,
    value: str,
    ttl: int = 3600,
    priority: int | None = None,
) -> DnsRecordEntry:
    """Create a manual DNS record for a custom domain.

    Creates the record both in the DNS provider and in the local database.

    Args:
        db: Async database session.
        domain_id: UUID of the CustomDomain.
        record_type: The DNS record type.
        name: The record hostname/name.
        value: The record value.
        ttl: Time-to-live in seconds (default 3600).
        priority: Priority for MX/SRV records (optional).

    Returns:
        The created DnsRecordEntry instance.

    Raises:
        ValueError: If the domain is not found.
    """
    result = await db.execute(
        select(CustomDomain).where(CustomDomain.id == domain_id)
    )
    domain = result.scalar_one_or_none()
    if domain is None:
        raise ValueError("Domain not found")

    provider = get_dns_provider()
    zone_id = domain.dns_zone_id or await provider.get_zone_id(domain.domain)

    dns_record = DnsRecord(
        record_type=record_type,
        name=name,
        value=value,
        ttl=ttl,
        priority=priority,
    )
    provider_result = await provider.create_record(zone_id, dns_record)

    entry = DnsRecordEntry(
        domain_id=domain_id,
        record_type=record_type,
        name=name,
        value=value,
        ttl=ttl,
        priority=priority,
        provider_record_id=provider_result.provider_record_id,
        is_managed=False,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


async def list_dns_records(
    db: AsyncSession,
    domain_id: uuid.UUID,
) -> list[DnsRecordEntry]:
    """List all DNS records for a custom domain.

    Args:
        db: Async database session.
        domain_id: UUID of the CustomDomain.

    Returns:
        List of DnsRecordEntry instances for the domain.

    Raises:
        ValueError: If the domain is not found.
    """
    result = await db.execute(
        select(CustomDomain).where(CustomDomain.id == domain_id)
    )
    domain = result.scalar_one_or_none()
    if domain is None:
        raise ValueError("Domain not found")

    records_result = await db.execute(
        select(DnsRecordEntry).where(DnsRecordEntry.domain_id == domain_id)
    )
    return list(records_result.scalars().all())


async def update_dns_record(
    db: AsyncSession,
    record_id: uuid.UUID,
    record_type: DnsRecordType | None = None,
    name: str | None = None,
    value: str | None = None,
    ttl: int | None = None,
    priority: int | None = None,
) -> DnsRecordEntry:
    """Update an existing DNS record.

    Updates the record in both the DNS provider and the local database.
    Only non-None fields are updated.

    Args:
        db: Async database session.
        record_id: UUID of the DnsRecordEntry to update.
        record_type: New record type (optional).
        name: New record name (optional).
        value: New record value (optional).
        ttl: New TTL value (optional).
        priority: New priority value (optional).

    Returns:
        The updated DnsRecordEntry instance.

    Raises:
        ValueError: If the record is not found.
    """
    result = await db.execute(
        select(DnsRecordEntry).where(DnsRecordEntry.id == record_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise ValueError("DNS record not found")

    if record_type is not None:
        entry.record_type = record_type
    if name is not None:
        entry.name = name
    if value is not None:
        entry.value = value
    if ttl is not None:
        entry.ttl = ttl
    if priority is not None:
        entry.priority = priority

    # Update in provider if we have the provider record ID
    if entry.provider_record_id:
        domain_result = await db.execute(
            select(CustomDomain).where(CustomDomain.id == entry.domain_id)
        )
        domain = domain_result.scalar_one_or_none()
        if domain:
            provider = get_dns_provider()
            zone_id = domain.dns_zone_id or await provider.get_zone_id(domain.domain)
            dns_record = DnsRecord(
                record_type=entry.record_type,
                name=entry.name,
                value=entry.value,
                ttl=entry.ttl,
                priority=entry.priority,
            )
            await provider.update_record(zone_id, entry.provider_record_id, dns_record)

    await db.flush()
    await db.refresh(entry)
    return entry


async def delete_dns_record(
    db: AsyncSession,
    record_id: uuid.UUID,
) -> bool:
    """Delete a DNS record from both the provider and database.

    Args:
        db: Async database session.
        record_id: UUID of the DnsRecordEntry to delete.

    Returns:
        True if the record was successfully deleted.

    Raises:
        ValueError: If the record is not found.
    """
    result = await db.execute(
        select(DnsRecordEntry).where(DnsRecordEntry.id == record_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise ValueError("DNS record not found")

    # Delete from provider if we have the provider record ID
    if entry.provider_record_id:
        domain_result = await db.execute(
            select(CustomDomain).where(CustomDomain.id == entry.domain_id)
        )
        domain = domain_result.scalar_one_or_none()
        if domain:
            provider = get_dns_provider()
            zone_id = domain.dns_zone_id or await provider.get_zone_id(domain.domain)
            await provider.delete_record(zone_id, entry.provider_record_id)

    await db.delete(entry)
    await db.flush()
    return True


async def get_dns_status(
    db: AsyncSession,
    domain_id: uuid.UUID,
) -> dict:
    """Get a comprehensive DNS status summary for a domain.

    Args:
        db: Async database session.
        domain_id: UUID of the CustomDomain.

    Returns:
        A dict with domain name, dns_configured, ssl_provisioned,
        records_count, and propagation_status.

    Raises:
        ValueError: If the domain is not found.
    """
    result = await db.execute(
        select(CustomDomain).where(CustomDomain.id == domain_id)
    )
    domain = result.scalar_one_or_none()
    if domain is None:
        raise ValueError("Domain not found")

    records_result = await db.execute(
        select(DnsRecordEntry).where(DnsRecordEntry.domain_id == domain_id)
    )
    records = list(records_result.scalars().all())

    propagation = await verify_dns_propagation(db, domain_id)

    return {
        "domain": domain.domain,
        "dns_configured": domain.auto_dns_configured,
        "ssl_provisioned": domain.ssl_provisioned,
        "records_count": len(records),
        "propagation_status": "propagated" if propagation["propagated"] else "pending",
    }
