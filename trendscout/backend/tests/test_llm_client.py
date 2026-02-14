"""
Tests for the LLM Gateway client.

Covers HTTP communication with the centralized LLM Gateway service,
including success responses, error handling, timeouts, and connection
failures.

For Developers:
    Tests mock ``httpx.AsyncClient.post`` to avoid real HTTP calls.
    The ``call_llm`` function is async — tests use ``pytest.mark.asyncio``.

For QA Engineers:
    These tests verify:
    - Successful LLM calls return parsed JSON (test_call_llm_success).
    - HTTP errors raise LLMGatewayError with status_code (test_call_llm_http_error).
    - Connection failures raise LLMGatewayError (test_call_llm_connection_error).
    - Timeouts raise LLMGatewayError (test_call_llm_timeout).
    - Correct headers are sent (test_call_llm_sends_correct_headers).
    - Custom parameters are forwarded (test_call_llm_custom_params).

For Project Managers:
    The LLM client is the bridge between TrendScout and the AI analysis
    engine.  These tests ensure robust error handling so the research
    pipeline degrades gracefully when the gateway is unavailable.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.llm_client import LLMGatewayError, call_llm


@pytest.mark.asyncio
async def test_call_llm_success():
    """call_llm returns parsed JSON on 200 response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": "Analysis text",
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }

    with patch("app.services.llm_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await call_llm(
            prompt="Analyze this product",
            system="You are an analyst",
            user_id="test-user-123",
            task_type="product_analysis",
        )

    assert result["content"] == "Analysis text"
    assert result["usage"]["input_tokens"] == 100


@pytest.mark.asyncio
async def test_call_llm_http_error():
    """call_llm raises LLMGatewayError with status_code on non-2xx response."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Rate limited"

    with patch("app.services.llm_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        with pytest.raises(LLMGatewayError) as exc_info:
            await call_llm(prompt="Test prompt")

    assert exc_info.value.status_code == 429
    assert "429" in exc_info.value.detail


@pytest.mark.asyncio
async def test_call_llm_connection_error():
    """call_llm raises LLMGatewayError on connection failure."""
    with patch("app.services.llm_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.side_effect = httpx.ConnectError("Connection refused")
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        with pytest.raises(LLMGatewayError) as exc_info:
            await call_llm(prompt="Test prompt")

    assert "Failed to connect" in exc_info.value.detail
    assert exc_info.value.status_code is None


@pytest.mark.asyncio
async def test_call_llm_timeout():
    """call_llm raises LLMGatewayError on timeout."""
    with patch("app.services.llm_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.side_effect = httpx.TimeoutException("Timed out")
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        with pytest.raises(LLMGatewayError) as exc_info:
            await call_llm(prompt="Test prompt")

    assert "timed out" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_call_llm_sends_correct_headers():
    """call_llm sends X-Service-Key and Content-Type headers."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"content": "ok"}

    with patch("app.services.llm_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        await call_llm(prompt="Test")

        # Verify the post call
        call_args = instance.post.call_args
        headers = call_args.kwargs.get("headers", {})
        assert "X-Service-Key" in headers
        assert headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_call_llm_custom_params():
    """call_llm forwards custom model, max_tokens, and temperature."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"content": "ok"}

    with patch("app.services.llm_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        await call_llm(
            prompt="Test",
            model="claude-opus-4-20250514",
            max_tokens=2048,
            temperature=0.7,
        )

        # Verify payload contains custom params
        call_args = instance.post.call_args
        payload = call_args.kwargs.get("json", {})
        assert payload["model"] == "claude-opus-4-20250514"
        assert payload["max_tokens"] == 2048
        assert payload["temperature"] == 0.7


@pytest.mark.asyncio
async def test_call_llm_includes_system_message():
    """call_llm includes system message when provided."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"content": "ok"}

    with patch("app.services.llm_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        await call_llm(
            prompt="Analyze this",
            system="You are an analyst",
        )

        call_args = instance.post.call_args
        payload = call_args.kwargs.get("json", {})
        messages = payload["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are an analyst"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Analyze this"


@pytest.mark.asyncio
async def test_call_llm_no_system_message():
    """call_llm omits system message when not provided."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"content": "ok"}

    with patch("app.services.llm_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        await call_llm(prompt="Analyze this")

        call_args = instance.post.call_args
        payload = call_args.kwargs.get("json", {})
        messages = payload["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
