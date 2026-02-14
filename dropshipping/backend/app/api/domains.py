"""Domains API router.

Provides endpoints for managing custom domain configuration for stores.
Store owners can set, verify, and remove custom domains to replace the
default platform subdomain.

**For Developers:**
    The router is nested under stores: ``/stores/{store_id}/domain/...``
    (full path: ``/api/v1/stores/{store_id}/domain/...``).
    The ``get_current_user`` dependency is used for authentication.
    Service functions in ``domain_service`` handle DNS verification.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - POST set returns 201 with the domain configuration.
    - Verify checks DNS records and updates verification status.
    - DELETE returns 204 and reverts to the platform subdomain.
    - Domain must be unique across all stores.

**For End Users:**
    - Set a custom domain (e.g. ``shop.yourbrand.com``) for your store.
    - Verify domain ownership by adding the provided DNS records.
    - Remove the custom domain to revert to the default URL.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.domain import (
    CreateDomainRequest,
    DomainResponse,
    VerifyDomainResponse,
)

router = APIRouter(prefix="/stores/{store_id}/domain", tags=["domains"])


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.post("", response_model=DomainResponse, status_code=status.HTTP_201_CREATED)
async def set_domain_endpoint(
    store_id: uuid.UUID,
    request: CreateDomainRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DomainResponse:
    """Set a custom domain for a store.

    Configures a custom domain and generates the DNS verification
    token and CNAME target. The domain must be verified via the
    ``/verify`` endpoint after DNS records are configured.

    Args:
        store_id: The UUID of the store.
        request: Domain setup payload with the custom domain name.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        DomainResponse with the domain config, verification token,
        and CNAME target for DNS setup.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
        HTTPException 400: If the domain is already in use by another store.
    """
    from app.services import domain_service

    try:
        domain = await domain_service.create_domain(
            db,
            store_id=store_id,
            user_id=current_user.id,
            domain=request.domain,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "already" in detail.lower() or "invalid" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return DomainResponse.model_validate(domain)


@router.get("", response_model=DomainResponse)
async def get_domain_endpoint(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DomainResponse:
    """Get the current domain configuration for a store.

    Returns the custom domain settings including verification status
    and DNS configuration details.

    Args:
        store_id: The UUID of the store.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        DomainResponse with the current domain configuration.

    Raises:
        HTTPException 404: If the store is not found or has no custom domain.
    """
    from app.services import domain_service

    try:
        domain = await domain_service.get_domain(
            db, store_id=store_id, user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    if domain is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No custom domain configured for this store",
        )
    return DomainResponse.model_validate(domain)


@router.post("/verify", response_model=VerifyDomainResponse)
async def verify_domain_endpoint(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VerifyDomainResponse:
    """Verify domain DNS configuration.

    Checks DNS records to verify domain ownership. The store's domain
    must have:
    - A CNAME record pointing to the provided target.
    - A TXT record containing the verification token.

    Args:
        store_id: The UUID of the store.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        DomainVerifyResponse with verification result and instructions.

    Raises:
        HTTPException 404: If the store or domain configuration is not found.
        HTTPException 400: If verification fails with DNS errors.
    """
    from app.services import domain_service

    try:
        result = await domain_service.verify_domain(
            db, store_id=store_id, user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    # Service returns a dict with 'verified', 'domain' (str), 'message' keys.
    return VerifyDomainResponse(
        verified=result["verified"],
        message=result["message"],
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def remove_domain_endpoint(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Remove the custom domain from a store.

    Reverts the store to using the default platform subdomain.

    Args:
        store_id: The UUID of the store.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        204 No Content on success.

    Raises:
        HTTPException 404: If the store or domain configuration is not found.
    """
    from app.services import domain_service

    try:
        await domain_service.delete_domain(
            db, store_id=store_id, user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
