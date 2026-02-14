"""
Tests for the LLM Gateway HTTP client.

Validates request construction, response parsing, error handling,
and timeout behavior for the ``call_llm`` function.

For Developers:
    All tests mock ``httpx.AsyncClient.post`` to avoid real HTTP calls.
    The mock returns structured JSON matching the LLM Gateway's response.

For QA Engineers:
    Covers: successful call, HTTP error handling, timeout, connection
    error, unexpected exceptions, and response structure validation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm_client import LLMGatewayError, call_llm


@pytest.mark.asyncio
async def test_call_llm_success():
    """call_llm returns parsed JSON on successful gateway response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": "Generated ad copy here",
        "provider": "claude",
        "model": "claude-sonnet-4-20250514",
        "input_tokens": 100,
        "output_tokens": 50,
        "cost_usd": 0.001,
        "cached": False,
        "latency_ms": 500,
    }

    with patch("app.services.llm_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await call_llm(
            prompt="Generate ad copy for shoes",
            system="You are an ad copywriter",
            user_id="test-user-123",
            task_type="ad_copy_generation",
        )

    assert result["content"] == "Generated ad copy here"
    assert result["provider"] == "claude"
    assert result["input_tokens"] == 100


@pytest.mark.asyncio
async def test_call_llm_http_error():
    """call_llm raises LLMGatewayError on 4xx/5xx responses."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("app.services.llm_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(LLMGatewayError) as exc_info:
            await call_llm(prompt="test", user_id="u1")

    assert exc_info.value.status_code == 500
    assert "500" in exc_info.value.detail


@pytest.mark.asyncio
async def test_call_llm_timeout():
    """call_llm raises LLMGatewayError on timeout."""
    import httpx

    with patch("app.services.llm_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("timed out")
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(LLMGatewayError) as exc_info:
            await call_llm(prompt="test", user_id="u1")

    assert "timed out" in exc_info.value.detail


@pytest.mark.asyncio
async def test_call_llm_connect_error():
    """call_llm raises LLMGatewayError on connection failure."""
    import httpx

    with patch("app.services.llm_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(LLMGatewayError) as exc_info:
            await call_llm(prompt="test", user_id="u1")

    assert "Failed to connect" in exc_info.value.detail
