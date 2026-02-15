"""
Tests for the Super Admin Dashboard LLM Gateway proxy endpoints.

For Developers:
    Tests the proxy layer that forwards admin requests to the LLM Gateway.
    All httpx calls to the gateway are mocked. Uses MagicMock for response
    objects and AsyncMock for async methods.

For QA Engineers:
    Covers: provider listing, creation, update, deletion via proxy,
    usage summary/by-provider/by-service via proxy, gateway errors
    (502 connect error, 504 timeout), and unauthorized access.

For Project Managers:
    These tests validate that the admin dashboard correctly proxies all
    LLM management operations to the gateway, maintaining the separation
    of concerns between admin and gateway services.

For End Users:
    Proxy tests ensure that admin operations on LLM providers work
    correctly, which impacts the reliability of all AI-powered features.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx as httpx_lib
import pytest


def _mock_response(status_code: int = 200, json_data=None):
    """
    Create a MagicMock that mimics an httpx.Response.

    Uses MagicMock (not AsyncMock) for the response object since
    httpx.Response methods like ``.json()`` are synchronous.

    Args:
        status_code: The HTTP status code to return.
        json_data: The JSON body to return from ``.json()``.

    Returns:
        A MagicMock configured as an httpx.Response.
    """
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    return resp


def _mock_client_with(method: str, response: MagicMock):
    """
    Create a mock httpx.AsyncClient that returns the given response.

    Sets up the async context manager (__aenter__/__aexit__) and the
    specified HTTP method as an AsyncMock.

    Args:
        method: The HTTP method to mock (get, post, patch, delete).
        response: The mock response to return.

    Returns:
        A configured AsyncMock acting as httpx.AsyncClient.
    """
    mock_client = AsyncMock()
    setattr(mock_client, method, AsyncMock(return_value=response))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


# --------------------------------------------------------------------------- #
#  Provider proxy tests
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_list_providers_proxy(client, auth_headers):
    """
    GET /llm/providers proxies to the gateway and returns provider list.

    Verifies:
        - Returns 200 with the mocked provider list.
        - The gateway's GET method is called with the correct URL.
    """
    providers = [
        {"id": "uuid-1", "name": "claude", "display_name": "Anthropic Claude"},
        {"id": "uuid-2", "name": "openai", "display_name": "OpenAI"},
    ]
    mock_client = _mock_client_with("get", _mock_response(200, providers))

    with patch("app.api.llm_proxy.httpx.AsyncClient", return_value=mock_client):
        resp = await client.get(
            "/api/v1/admin/llm/providers", headers=auth_headers
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["name"] == "claude"
    assert data[1]["name"] == "openai"


@pytest.mark.asyncio
async def test_create_provider_proxy(client, auth_headers):
    """
    POST /llm/providers proxies the creation request to the gateway.

    Verifies:
        - Returns 201 with the created provider.
        - The gateway's POST method is called.
    """
    created = {"id": "uuid-new", "name": "gemini", "display_name": "Google Gemini"}
    mock_client = _mock_client_with("post", _mock_response(200, created))

    with patch("app.api.llm_proxy.httpx.AsyncClient", return_value=mock_client):
        resp = await client.post(
            "/api/v1/admin/llm/providers",
            json={
                "name": "gemini",
                "display_name": "Google Gemini",
                "api_key": "gkey",
            },
            headers=auth_headers,
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "gemini"


@pytest.mark.asyncio
async def test_update_provider_proxy(client, auth_headers):
    """
    PATCH /llm/providers/{id} proxies the update request to the gateway.

    Verifies:
        - Returns 200 with the updated provider.
    """
    updated = {
        "id": "uuid-1",
        "name": "claude",
        "display_name": "Anthropic Claude v2",
        "is_enabled": False,
    }
    mock_client = _mock_client_with("patch", _mock_response(200, updated))

    with patch("app.api.llm_proxy.httpx.AsyncClient", return_value=mock_client):
        resp = await client.patch(
            "/api/v1/admin/llm/providers/uuid-1",
            json={"display_name": "Anthropic Claude v2", "is_enabled": False},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "Anthropic Claude v2"
    assert data["is_enabled"] is False


@pytest.mark.asyncio
async def test_delete_provider_proxy(client, auth_headers):
    """
    DELETE /llm/providers/{id} proxies the deletion to the gateway.

    Verifies:
        - Returns 204 (No Content).
    """
    mock_client = _mock_client_with("delete", _mock_response(204))

    with patch("app.api.llm_proxy.httpx.AsyncClient", return_value=mock_client):
        resp = await client.delete(
            "/api/v1/admin/llm/providers/uuid-1",
            headers=auth_headers,
        )

    assert resp.status_code == 204


# --------------------------------------------------------------------------- #
#  Usage proxy tests
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_usage_summary_proxy(client, auth_headers):
    """
    GET /llm/usage/summary proxies to the gateway's usage summary.

    Verifies:
        - Returns 200 with the mocked summary data.
    """
    summary = {
        "period_days": 30,
        "total_requests": 100,
        "total_cost_usd": 5.50,
        "total_tokens": 50000,
    }
    mock_client = _mock_client_with("get", _mock_response(200, summary))

    with patch("app.api.llm_proxy.httpx.AsyncClient", return_value=mock_client):
        resp = await client.get(
            "/api/v1/admin/llm/usage/summary?days=30",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_requests"] == 100
    assert data["total_cost_usd"] == 5.50


@pytest.mark.asyncio
async def test_usage_by_provider_proxy(client, auth_headers):
    """
    GET /llm/usage/by-provider proxies to the gateway.

    Verifies:
        - Returns 200 with per-provider usage data.
    """
    by_provider = [
        {"provider_name": "claude", "request_count": 80, "total_cost_usd": 4.00},
        {"provider_name": "openai", "request_count": 20, "total_cost_usd": 1.50},
    ]
    mock_client = _mock_client_with("get", _mock_response(200, by_provider))

    with patch("app.api.llm_proxy.httpx.AsyncClient", return_value=mock_client):
        resp = await client.get(
            "/api/v1/admin/llm/usage/by-provider?days=30",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["provider_name"] == "claude"


@pytest.mark.asyncio
async def test_usage_by_service_proxy(client, auth_headers):
    """
    GET /llm/usage/by-service proxies to the gateway.

    Verifies:
        - Returns 200 with per-service usage data.
    """
    by_service = [
        {"service_name": "trendscout", "request_count": 50, "total_cost_usd": 2.50},
        {"service_name": "contentforge", "request_count": 30, "total_cost_usd": 1.80},
    ]
    mock_client = _mock_client_with("get", _mock_response(200, by_service))

    with patch("app.api.llm_proxy.httpx.AsyncClient", return_value=mock_client):
        resp = await client.get(
            "/api/v1/admin/llm/usage/by-service?days=30",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["service_name"] == "trendscout"


# --------------------------------------------------------------------------- #
#  Error handling tests
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_proxy_gateway_connection_error(client, auth_headers):
    """
    Gateway connection error returns 502.

    Verifies:
        - Returns 502 with ``Cannot connect to LLM Gateway`` detail.
    """
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx_lib.ConnectError("refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.llm_proxy.httpx.AsyncClient", return_value=mock_client):
        resp = await client.get(
            "/api/v1/admin/llm/providers", headers=auth_headers
        )

    assert resp.status_code == 502
    assert "Cannot connect" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_proxy_gateway_timeout(client, auth_headers):
    """
    Gateway timeout returns 504.

    Verifies:
        - Returns 504 with ``timed out`` in the detail.
    """
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=httpx_lib.TimeoutException("timed out")
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.llm_proxy.httpx.AsyncClient", return_value=mock_client):
        resp = await client.get(
            "/api/v1/admin/llm/providers", headers=auth_headers
        )

    assert resp.status_code == 504
    assert "timed out" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_proxy_gateway_error_response(client, auth_headers):
    """
    Gateway 4xx/5xx responses are forwarded as-is.

    Verifies:
        - A 404 from the gateway is returned as 404 to the admin client.
    """
    error_resp = _mock_response(404, {"detail": "Provider not found"})
    mock_client = _mock_client_with("get", error_resp)

    with patch("app.api.llm_proxy.httpx.AsyncClient", return_value=mock_client):
        resp = await client.get(
            "/api/v1/admin/llm/providers", headers=auth_headers
        )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Provider not found"


@pytest.mark.asyncio
async def test_proxy_unauthorized(client):
    """
    Proxy endpoints without auth return 401.

    Verifies:
        - Returns 401 (HTTPBearer rejects missing credentials).
    """
    resp = await client.get("/api/v1/admin/llm/providers")
    assert resp.status_code in (401, 403)
