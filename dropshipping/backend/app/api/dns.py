"""DNS management API router.

Provides endpoints for managing DNS records, auto-configuration, SSL
provisioning, and DNS status for stores with custom domains.

**For Developers:**
    The router is nested under stores: ``/stores/{store_id}/domain/dns/...``
    and ``/stores/{store_id}/domain/ssl/...``. The ``get_current_user``
    dependency enforces authentication. DNS operations are delegated to
    ``dns_management_service``.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - Auto-configure creates exactly 2 records (A + CNAME) and returns 200.
    - SSL provision sets ssl_provisioned=True and returns certificate info.
    - DNS status returns propagation information for managed records.
    - CRUD endpoints follow standard REST patterns (POST/GET/PATCH/DELETE).
    - 404 is returned if the store or domain is not found.

**For Project Managers:**
    These endpoints power Feature 6 (DNS Management), enabling automatic
    and manual DNS record management for custom domains.

**For End Users:**
    Manage your domain's DNS records through the platform. Use
    auto-configure to set up records automatically, or manage them
    manually for more control.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.domain import CustomDomain
from app.models.store import Store, StoreStatus
from app.models.user import User
from app.schemas.dns import (
    AutoConfigureResponse,
    CreateDnsRecordRequest,
    DnsRecordResponse,
    DnsStatusResponse,
    SslProvisionResponse,
    UpdateDnsRecordRequest,
)

router = APIRouter(prefix="/stores/{store_id}/domain", tags=["dns"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_store_domain(
    db: AsyncSession, store_id: uuid.UUID, user_id: uuid.UUID
) -> CustomDomain:
    """Verify store ownership and retrieve the custom domain.

    Args:
        db: Async database session.
        store_id: The UUID of the store.
        user_id: The requesting user's UUID.

    Returns:
        The CustomDomain ORM instance.

    Raises:
        HTTPException: 404 if the store, domain, or ownership check fails.
    """
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if store is None or store.status == StoreStatus.deleted or store.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    domain_result = await db.execute(
        select(CustomDomain).where(CustomDomain.store_id == store_id)
    )
    domain = domain_result.scalar_one_or_none()
    if domain is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No custom domain configured for this store",
        )
    return domain


# ---------------------------------------------------------------------------
# Auto-configure DNS
# ---------------------------------------------------------------------------


@router.post(
    "/dns/auto-configure",
    response_model=AutoConfigureResponse,
    status_code=status.HTTP_200_OK,
)
async def auto_configure_dns_endpoint(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutoConfigureResponse:
    """Auto-configure DNS records for a store's custom domain.

    Creates A and CNAME records pointing to the platform. The A record
    maps the root domain to the platform IP, and the CNAME maps ``www``
    to the platform hostname.

    Args:
        store_id: The UUID of the store.
        current_user: The authenticated store owner.
        db: Async database session.

    Returns:
        AutoConfigureResponse with the created records.

    Raises:
        HTTPException 404: If the store or domain is not found.
    """
    from app.services import dns_management_service

    domain = await _get_store_domain(db, store_id, current_user.id)

    try:
        records = await dns_management_service.auto_configure_dns(db, domain.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    return AutoConfigureResponse(
        records_created=len(records),
        records=[DnsRecordResponse.model_validate(r) for r in records],
    )


# ---------------------------------------------------------------------------
# DNS Records CRUD
# ---------------------------------------------------------------------------


@router.get("/dns/records", response_model=list[DnsRecordResponse])
async def list_dns_records_endpoint(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DnsRecordResponse]:
    """List all DNS records for a store's custom domain.

    Args:
        store_id: The UUID of the store.
        current_user: The authenticated store owner.
        db: Async database session.

    Returns:
        A list of DnsRecordResponse objects.

    Raises:
        HTTPException 404: If the store or domain is not found.
    """
    from app.services import dns_management_service

    domain = await _get_store_domain(db, store_id, current_user.id)

    try:
        records = await dns_management_service.list_dns_records(db, domain.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    return [DnsRecordResponse.model_validate(r) for r in records]


@router.post(
    "/dns/records",
    response_model=DnsRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_dns_record_endpoint(
    store_id: uuid.UUID,
    request: CreateDnsRecordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DnsRecordResponse:
    """Create a new DNS record for a store's custom domain.

    Args:
        store_id: The UUID of the store.
        request: The DNS record creation payload.
        current_user: The authenticated store owner.
        db: Async database session.

    Returns:
        The created DnsRecordResponse.

    Raises:
        HTTPException 404: If the store or domain is not found.
    """
    from app.services import dns_management_service

    domain = await _get_store_domain(db, store_id, current_user.id)

    try:
        record = await dns_management_service.create_dns_record(
            db,
            domain_id=domain.id,
            record_type=request.record_type,
            name=request.name,
            value=request.value,
            ttl=request.ttl,
            priority=request.priority,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    return DnsRecordResponse.model_validate(record)


@router.patch("/dns/records/{record_id}", response_model=DnsRecordResponse)
async def update_dns_record_endpoint(
    store_id: uuid.UUID,
    record_id: uuid.UUID,
    request: UpdateDnsRecordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DnsRecordResponse:
    """Update an existing DNS record.

    Args:
        store_id: The UUID of the store.
        record_id: The UUID of the DNS record to update.
        request: The update payload with optional fields.
        current_user: The authenticated store owner.
        db: Async database session.

    Returns:
        The updated DnsRecordResponse.

    Raises:
        HTTPException 404: If the store, domain, or record is not found.
    """
    from app.services import dns_management_service

    # Verify ownership (will raise 404 if invalid)
    await _get_store_domain(db, store_id, current_user.id)

    try:
        record = await dns_management_service.update_dns_record(
            db,
            record_id=record_id,
            record_type=request.record_type,
            name=request.name,
            value=request.value,
            ttl=request.ttl,
            priority=request.priority,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    return DnsRecordResponse.model_validate(record)


@router.delete(
    "/dns/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_dns_record_endpoint(
    store_id: uuid.UUID,
    record_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a DNS record.

    Args:
        store_id: The UUID of the store.
        record_id: The UUID of the DNS record to delete.
        current_user: The authenticated store owner.
        db: Async database session.

    Raises:
        HTTPException 404: If the store, domain, or record is not found.
    """
    from app.services import dns_management_service

    # Verify ownership
    await _get_store_domain(db, store_id, current_user.id)

    try:
        await dns_management_service.delete_dns_record(db, record_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )


# ---------------------------------------------------------------------------
# SSL Provisioning
# ---------------------------------------------------------------------------


@router.post("/ssl/provision", response_model=SslProvisionResponse)
async def provision_ssl_endpoint(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SslProvisionResponse:
    """Provision an SSL certificate for a store's custom domain.

    Args:
        store_id: The UUID of the store.
        current_user: The authenticated store owner.
        db: Async database session.

    Returns:
        SslProvisionResponse with certificate details.

    Raises:
        HTTPException 404: If the store or domain is not found.
    """
    from app.services import dns_management_service

    domain = await _get_store_domain(db, store_id, current_user.id)

    try:
        updated_domain = await dns_management_service.provision_ssl(db, domain.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    return SslProvisionResponse(
        ssl_provisioned=updated_domain.ssl_provisioned,
        ssl_certificate_id=updated_domain.ssl_certificate_id,
        ssl_expires_at=updated_domain.ssl_expires_at,
    )


# ---------------------------------------------------------------------------
# DNS Status
# ---------------------------------------------------------------------------


@router.get("/dns/status", response_model=DnsStatusResponse)
async def dns_status_endpoint(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DnsStatusResponse:
    """Get the DNS status summary for a store's custom domain.

    Returns a comprehensive overview of DNS configuration, SSL status,
    record count, and propagation status.

    Args:
        store_id: The UUID of the store.
        current_user: The authenticated store owner.
        db: Async database session.

    Returns:
        DnsStatusResponse with the status summary.

    Raises:
        HTTPException 404: If the store or domain is not found.
    """
    from app.services import dns_management_service

    domain = await _get_store_domain(db, store_id, current_user.id)

    try:
        status_data = await dns_management_service.get_dns_status(db, domain.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    return DnsStatusResponse(**status_data)
