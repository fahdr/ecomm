"""
Tests for the LLM Gateway client.

Covers successful responses, error handling (HTTP errors, timeouts,
connection failures), and request construction.

For Developers:
    All tests mock httpx.AsyncClient to avoid real HTTP calls.
    Verify that the X-Service-Key header is set correctly.

For QA Engineers:
    These tests verify that the LLM client handles all failure modes
    gracefully and raises LLMGatewayError with appropriate details.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.llm_client import call_llm, LLMGatewayError


@pytest.mark.asyncio
async def test_call_llm_success():
    """call_llm returns parsed JSON on successful gateway response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": "Generated caption text",
        "provider": "claude",
        "model": "claude-sonnet-4-20250514",
        "input_tokens": 50,
        "output_tokens": 30,
        "cost_usd": 0.001,
    }

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.llm_client.httpx.AsyncClient", return_value=mock_client):
        result = await call_llm(
            prompt="Generate a caption for headphones",
            system="You are a social media expert",
            user_id="test-user-123",
            task_type="caption_generation",
        )

    assert result["content"] == "Generated caption text"
    assert result["provider"] == "claude"
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_call_llm_http_error():
    """call_llm raises LLMGatewayError on 4xx/5xx responses."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.llm_client.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(LLMGatewayError) as exc_info:
            await call_llm(prompt="test prompt")

    assert exc_info.value.status_code == 500
    assert "500" in exc_info.value.detail


@pytest.mark.asyncio
async def test_call_llm_timeout():
    """call_llm raises LLMGatewayError on timeout."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.TimeoutException("Request timed out")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.llm_client.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(LLMGatewayError) as exc_info:
            await call_llm(prompt="test prompt", timeout=1.0)

    assert "timed out" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_call_llm_connection_error():
    """call_llm raises LLMGatewayError on connection failure."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.llm_client.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(LLMGatewayError) as exc_info:
            await call_llm(prompt="test prompt")

    assert "connect" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_call_llm_sends_correct_headers():
    """call_llm sends X-Service-Key header with the configured gateway key."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"content": "ok"}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.llm_client.httpx.AsyncClient", return_value=mock_client):
        await call_llm(prompt="test")

    call_kwargs = mock_client.post.call_args
    headers = call_kwargs.kwargs.get("headers", {})
    assert "X-Service-Key" in headers
    assert headers["X-Service-Key"] == "dev-gateway-key"
