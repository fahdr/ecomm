"""Domain purchasing API router.

Provides endpoints for searching, purchasing, renewing, and managing
domain names through the platform.

**For Developers:**
    Domain search and owned domains list are user-scoped (not store-scoped).
    Purchase and renewal endpoints are store-scoped under
    ``/stores/{store_id}/domain/...``. The ``get_current_user`` dependency
    enforces authentication on all endpoints.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - Search endpoint returns domain availability and pricing.
    - Purchase creates a CustomDomain with is_purchased=True.
    - Purchase auto-configures DNS and provisions SSL.
    - Renew updates expiry_date and order_id.
    - Auto-renew toggle returns the new status.
    - 404 is returned if the store or domain is not found.

**For Project Managers:**
    These endpoints power Feature 7 (Domain Purchasing), enabling merchants
    to search for and buy domains, manage renewals, and configure auto-renewal.

**For End Users:**
    Search for available domains, purchase them, and manage your domain
    portfolio all from within your dashboard.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.domain import CustomDomain
from app.models.store import Store, StoreStatus
from app.models.user import User
from app.schemas.domain_purchase import (
    AutoRenewRequest,
    AutoRenewResponse,
    DomainPurchaseRequest,
    DomainPurchaseResponse,
    DomainRenewRequest,
    DomainRenewResponse,
    DomainSearchResultItem,
    DomainSearchResponse,
    OwnedDomainItem,
    OwnedDomainResponse,
)

router = APIRouter(tags=["domain-purchase"])


# ---------------------------------------------------------------------------
# Domain Search (user-scoped, not store-scoped)
# ---------------------------------------------------------------------------


@router.get("/domains/search", response_model=DomainSearchResponse)
async def search_domains_endpoint(
    q: str = Query(..., min_length=1, max_length=63, description="Domain name query"),
    tlds: str = Query(
        default="com,io,store",
        description="Comma-separated TLD list",
    ),
    current_user: User = Depends(get_current_user),
) -> DomainSearchResponse:
    """Search for available domain names.

    Searches the configured domain registrar for domain availability
    across the specified TLD extensions.

    Args:
        q: The domain name query (without TLD).
        tlds: Comma-separated list of TLD extensions.
        current_user: The authenticated user.

    Returns:
        DomainSearchResponse with a list of results per TLD.
    """
    from app.services import domain_purchase_service

    tld_list = [t.strip() for t in tlds.split(",") if t.strip()]
    results = await domain_purchase_service.search_available_domains(q, tld_list)

    return DomainSearchResponse(
        results=[DomainSearchResultItem(**r) for r in results]
    )


# ---------------------------------------------------------------------------
# Owned Domains (user-scoped)
# ---------------------------------------------------------------------------


@router.get("/domains/owned", response_model=OwnedDomainResponse)
async def list_owned_domains_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OwnedDomainResponse:
    """List all domains purchased by the current user.

    Args:
        current_user: The authenticated user.
        db: Async database session.

    Returns:
        OwnedDomainResponse with a list of purchased domains.
    """
    from app.services import domain_purchase_service

    domains = await domain_purchase_service.list_owned_domains(db, current_user.id)

    return OwnedDomainResponse(
        domains=[OwnedDomainItem(**d) for d in domains]
    )


# ---------------------------------------------------------------------------
# Purchase Domain (store-scoped)
# ---------------------------------------------------------------------------


@router.post(
    "/stores/{store_id}/domain/purchase",
    response_model=DomainPurchaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def purchase_domain_endpoint(
    store_id: uuid.UUID,
    request: DomainPurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DomainPurchaseResponse:
    """Purchase a domain and configure it for a store.

    Purchases the domain via the configured registrar, creates the
    CustomDomain record, sets nameservers, auto-configures DNS, and
    provisions SSL.

    Args:
        store_id: The UUID of the store.
        request: The domain purchase payload.
        current_user: The authenticated user.
        db: Async database session.

    Returns:
        DomainPurchaseResponse with purchase and configuration details.

    Raises:
        HTTPException 404: If the store is not found.
        HTTPException 400: If the domain is already in use or purchase fails.
    """
    from app.services import domain_purchase_service

    try:
        result = await domain_purchase_service.purchase_domain(
            db,
            store_id=store_id,
            user_id=current_user.id,
            domain=request.domain,
            years=request.years,
            contact_info=request.contact_info,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "already" in detail.lower() or "failed" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)

    return DomainPurchaseResponse(**result)


# ---------------------------------------------------------------------------
# Renew Domain (store-scoped)
# ---------------------------------------------------------------------------


@router.post(
    "/stores/{store_id}/domain/renew",
    response_model=DomainRenewResponse,
)
async def renew_domain_endpoint(
    store_id: uuid.UUID,
    request: DomainRenewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DomainRenewResponse:
    """Renew a domain registration for a store.

    Args:
        store_id: The UUID of the store.
        request: The renewal payload with the number of years.
        current_user: The authenticated user.
        db: Async database session.

    Returns:
        DomainRenewResponse with the new expiry date.

    Raises:
        HTTPException 404: If the store or domain is not found.
        HTTPException 400: If the domain was not purchased via the platform.
    """
    from app.services import domain_purchase_service

    # Verify store ownership
    store_result = await db.execute(select(Store).where(Store.id == store_id))
    store = store_result.scalar_one_or_none()
    if store is None or store.status == StoreStatus.deleted or store.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    # Get domain
    domain_result = await db.execute(
        select(CustomDomain).where(CustomDomain.store_id == store_id)
    )
    domain = domain_result.scalar_one_or_none()
    if domain is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No custom domain configured for this store",
        )

    try:
        result = await domain_purchase_service.renew_domain(
            db, domain_id=domain.id, years=request.years
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "not purchased" in detail.lower() or "failed" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)

    return DomainRenewResponse(**result)


# ---------------------------------------------------------------------------
# Auto-Renew Toggle (store-scoped)
# ---------------------------------------------------------------------------


@router.patch(
    "/stores/{store_id}/domain/auto-renew",
    response_model=AutoRenewResponse,
)
async def toggle_auto_renew_endpoint(
    store_id: uuid.UUID,
    request: AutoRenewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutoRenewResponse:
    """Toggle auto-renewal for a store's domain.

    Args:
        store_id: The UUID of the store.
        request: The auto-renew toggle payload.
        current_user: The authenticated user.
        db: Async database session.

    Returns:
        AutoRenewResponse with the updated auto-renew status.

    Raises:
        HTTPException 404: If the store or domain is not found.
        HTTPException 400: If the domain was not purchased via the platform.
    """
    from app.services import domain_purchase_service

    # Verify store ownership
    store_result = await db.execute(select(Store).where(Store.id == store_id))
    store = store_result.scalar_one_or_none()
    if store is None or store.status == StoreStatus.deleted or store.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    # Get domain
    domain_result = await db.execute(
        select(CustomDomain).where(CustomDomain.store_id == store_id)
    )
    domain = domain_result.scalar_one_or_none()
    if domain is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No custom domain configured for this store",
        )

    try:
        result = await domain_purchase_service.toggle_auto_renew(
            db, domain_id=domain.id, auto_renew=request.auto_renew
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "not purchased" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)

    return AutoRenewResponse(**result)
