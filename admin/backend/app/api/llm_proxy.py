"""
LLM Gateway proxy router for the Super Admin Dashboard.

Forwards admin requests to the LLM Gateway's provider and usage endpoints.
This allows the admin dashboard to manage LLM providers and view usage
analytics without directly connecting to the gateway.

For Developers:
    All proxy endpoints forward the request to the LLM Gateway at
    ``settings.llm_gateway_url`` with the ``X-Service-Key`` header set to
    ``settings.llm_gateway_key``. The response is returned as-is.

    The proxy uses httpx.AsyncClient for non-blocking HTTP calls. Errors
    from the gateway are translated into appropriate HTTP responses.

For QA Engineers:
    Mock the httpx calls to the gateway. Test that:
    - Provider CRUD (list, create, update, delete) proxies correctly.
    - Usage endpoints (summary, by-provider, by-service) proxy correctly.
    - Gateway errors (500, timeout) are handled gracefully.

For Project Managers:
    The proxy pattern means the admin dashboard does not need direct
    database access to the LLM Gateway tables. All management goes
    through the gateway's own API, maintaining separation of concerns.

For End Users:
    This is an internal management interface. End users benefit from
    the LLM providers being properly configured and monitored.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.api.deps import get_current_admin
from app.config import settings
from app.models.admin_user import AdminUser

router = APIRouter()

# Timeout for proxy requests to the LLM Gateway (seconds)
GATEWAY_TIMEOUT = 10.0


def _gateway_headers() -> dict[str, str]:
    """
    Build the authentication headers for the LLM Gateway.

    Returns:
        Dict with the X-Service-Key header set to the configured key.
    """
    return {"X-Service-Key": settings.llm_gateway_key}


async def _proxy_get(path: str, params: dict | None = None) -> dict | list:
    """
    Proxy a GET request to the LLM Gateway.

    Args:
        path: The gateway endpoint path (e.g., ``/api/v1/providers``).
        params: Optional query parameters.

    Returns:
        The JSON response from the gateway.

    Raises:
        HTTPException: If the gateway returns a non-2xx status or is unreachable.
    """
    url = f"{settings.llm_gateway_url}{path}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers=_gateway_headers(),
                params=params,
                timeout=GATEWAY_TIMEOUT,
            )
            if resp.status_code >= 400:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=resp.json().get("detail", "Gateway error"),
                )
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=502, detail="Cannot connect to LLM Gateway"
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504, detail="LLM Gateway request timed out"
        )


async def _proxy_post(path: str, body: dict) -> dict:
    """
    Proxy a POST request to the LLM Gateway.

    Args:
        path: The gateway endpoint path.
        body: The JSON request body.

    Returns:
        The JSON response from the gateway.

    Raises:
        HTTPException: If the gateway returns a non-2xx status or is unreachable.
    """
    url = f"{settings.llm_gateway_url}{path}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers=_gateway_headers(),
                json=body,
                timeout=GATEWAY_TIMEOUT,
            )
            if resp.status_code >= 400:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=resp.json().get("detail", "Gateway error"),
                )
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=502, detail="Cannot connect to LLM Gateway"
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504, detail="LLM Gateway request timed out"
        )


async def _proxy_patch(path: str, body: dict) -> dict:
    """
    Proxy a PATCH request to the LLM Gateway.

    Args:
        path: The gateway endpoint path.
        body: The JSON request body with fields to update.

    Returns:
        The JSON response from the gateway.

    Raises:
        HTTPException: If the gateway returns a non-2xx status or is unreachable.
    """
    url = f"{settings.llm_gateway_url}{path}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                url,
                headers=_gateway_headers(),
                json=body,
                timeout=GATEWAY_TIMEOUT,
            )
            if resp.status_code >= 400:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=resp.json().get("detail", "Gateway error"),
                )
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=502, detail="Cannot connect to LLM Gateway"
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504, detail="LLM Gateway request timed out"
        )


async def _proxy_delete(path: str) -> None:
    """
    Proxy a DELETE request to the LLM Gateway.

    Args:
        path: The gateway endpoint path.

    Raises:
        HTTPException: If the gateway returns a non-2xx status or is unreachable.
    """
    url = f"{settings.llm_gateway_url}{path}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                url,
                headers=_gateway_headers(),
                timeout=GATEWAY_TIMEOUT,
            )
            if resp.status_code >= 400:
                detail = "Gateway error"
                try:
                    detail = resp.json().get("detail", detail)
                except Exception:
                    pass
                raise HTTPException(
                    status_code=resp.status_code, detail=detail
                )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=502, detail="Cannot connect to LLM Gateway"
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504, detail="LLM Gateway request timed out"
        )


# --------------------------------------------------------------------------- #
#  Provider proxy endpoints
# --------------------------------------------------------------------------- #


@router.get("/llm/providers")
async def list_providers(
    _admin: AdminUser = Depends(get_current_admin),
):
    """
    List all LLM providers configured in the gateway.

    Proxies to ``GET /api/v1/providers`` on the LLM Gateway.

    Returns:
        List of provider configuration dicts.
    """
    return await _proxy_get("/api/v1/providers")


@router.post("/llm/providers", status_code=201)
async def create_provider(
    request: Request,
    _admin: AdminUser = Depends(get_current_admin),
):
    """
    Create a new LLM provider in the gateway.

    Proxies to ``POST /api/v1/providers`` on the LLM Gateway.

    Args:
        request: The incoming FastAPI request (body forwarded as-is).

    Returns:
        The created provider configuration dict.
    """
    body = await request.json()
    return await _proxy_post("/api/v1/providers", body)


@router.patch("/llm/providers/{provider_id}")
async def update_provider(
    provider_id: str,
    request: Request,
    _admin: AdminUser = Depends(get_current_admin),
):
    """
    Update an LLM provider in the gateway.

    Proxies to ``PATCH /api/v1/providers/{id}`` on the LLM Gateway.

    Args:
        provider_id: The provider's UUID.
        request: The incoming FastAPI request (body forwarded as-is).

    Returns:
        The updated provider configuration dict.
    """
    body = await request.json()
    return await _proxy_patch(f"/api/v1/providers/{provider_id}", body)


@router.delete("/llm/providers/{provider_id}", status_code=204)
async def delete_provider(
    provider_id: str,
    _admin: AdminUser = Depends(get_current_admin),
):
    """
    Delete an LLM provider from the gateway.

    Proxies to ``DELETE /api/v1/providers/{id}`` on the LLM Gateway.

    Args:
        provider_id: The provider's UUID.
    """
    await _proxy_delete(f"/api/v1/providers/{provider_id}")


# --------------------------------------------------------------------------- #
#  Usage proxy endpoints
# --------------------------------------------------------------------------- #


@router.get("/llm/usage/summary")
async def usage_summary(
    days: int = 30,
    _admin: AdminUser = Depends(get_current_admin),
):
    """
    Get LLM usage summary from the gateway.

    Proxies to ``GET /api/v1/usage/summary`` on the LLM Gateway.

    Args:
        days: Number of days to look back (default 30).

    Returns:
        Usage summary dict with total requests, cost, tokens, etc.
    """
    return await _proxy_get("/api/v1/usage/summary", {"days": days})


@router.get("/llm/usage/by-provider")
async def usage_by_provider(
    days: int = 30,
    _admin: AdminUser = Depends(get_current_admin),
):
    """
    Get LLM usage breakdown by provider from the gateway.

    Proxies to ``GET /api/v1/usage/by-provider`` on the LLM Gateway.

    Args:
        days: Number of days to look back (default 30).

    Returns:
        List of usage dicts grouped by provider.
    """
    return await _proxy_get("/api/v1/usage/by-provider", {"days": days})


@router.get("/llm/usage/by-service")
async def usage_by_service(
    days: int = 30,
    _admin: AdminUser = Depends(get_current_admin),
):
    """
    Get LLM usage breakdown by calling service from the gateway.

    Proxies to ``GET /api/v1/usage/by-service`` on the LLM Gateway.

    Args:
        days: Number of days to look back (default 30).

    Returns:
        List of usage dicts grouped by service.
    """
    return await _proxy_get("/api/v1/usage/by-service", {"days": days})
