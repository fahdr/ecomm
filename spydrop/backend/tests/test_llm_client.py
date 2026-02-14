"""
Tests for the LLM Gateway client.

Verifies HTTP request formation, response parsing, and error handling
for the LLM Gateway client.

For Developers:
    Tests mock ``httpx.AsyncClient`` to avoid real network calls.
    Each test verifies a specific scenario (success, auth failure,
    rate limit, timeout, connection error).

For QA Engineers:
    These tests cover:
    - Successful LLM call with parsed response.
    - 401 authentication error handling.
    - 429 rate limit error handling.
    - Timeout error handling.
    - Connection error handling.
    - Generic server error handling.

For Project Managers:
    The LLM client is the bridge to AI features. These tests ensure
    reliable error handling so the app degrades gracefully when the
    LLM Gateway is unavailable.

For End Users:
    These tests ensure AI-powered features work reliably and handle
    errors without crashing.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.llm_client import call_llm


@pytest.mark.asyncio
async def test_call_llm_success():
    """Successful LLM call returns parsed response dict."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": "Hello from LLM",
        "provider": "claude",
        "model": "claude-3",
        "input_tokens": 10,
        "output_tokens": 5,
        "cost_usd": 0.001,
        "cached": False,
        "latency_ms": 150,
    }

    with patch("app.services.llm_client.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_client

        result = await call_llm(prompt="Hello", system="Be helpful")

    assert result["content"] == "Hello from LLM"
    assert result["provider"] == "claude"
    assert result.get("error") is None


@pytest.mark.asyncio
async def test_call_llm_auth_failure():
    """401 response returns auth error dict."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {"detail": "Invalid service key"}
    mock_response.text = '{"detail": "Invalid service key"}'

    with patch("app.services.llm_client.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_client

        result = await call_llm(prompt="Hello")

    assert "authentication failed" in result["error"].lower()
    assert result["content"] == ""


@pytest.mark.asyncio
async def test_call_llm_rate_limit():
    """429 response returns rate limit error dict."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.json.return_value = {"detail": "Rate limit exceeded"}
    mock_response.text = '{"detail": "Rate limit exceeded"}'

    with patch("app.services.llm_client.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_client

        result = await call_llm(prompt="Hello")

    assert "rate limit" in result["error"].lower()
    assert result["content"] == ""


@pytest.mark.asyncio
async def test_call_llm_timeout():
    """Timeout exception returns timeout error dict."""
    with patch("app.services.llm_client.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_client

        result = await call_llm(prompt="Hello", timeout=1.0)

    assert "timed out" in result["error"].lower()
    assert result["content"] == ""


@pytest.mark.asyncio
async def test_call_llm_connection_error():
    """Connection error returns connection error dict."""
    with patch("app.services.llm_client.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_client

        result = await call_llm(prompt="Hello")

    assert "connect" in result["error"].lower()
    assert result["content"] == ""


@pytest.mark.asyncio
async def test_call_llm_server_error():
    """500+ response returns server error dict."""
    mock_response = MagicMock()
    mock_response.status_code = 502
    mock_response.json.return_value = {"detail": "Bad gateway"}
    mock_response.text = '{"detail": "Bad gateway"}'

    with patch("app.services.llm_client.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_client

        result = await call_llm(prompt="Hello")

    assert "502" in result["error"]
    assert result["content"] == ""
