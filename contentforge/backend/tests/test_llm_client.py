"""
LLM Gateway client unit tests.

Tests the ContentForge LLM client wrapper functions including the real
``call_contentforge_llm()`` (with mocked httpx) and the mock helper.

For Developers:
    Tests mock the httpx AsyncClient to avoid hitting the real LLM Gateway.
    The mock helper ``call_contentforge_llm_mock`` is tested directly.

For QA Engineers:
    Run with: ``pytest tests/test_llm_client.py -v``
    Tests verify:
    - Mock LLM returns expected response format
    - Real LLM client sends correct headers and payload
    - Gateway URL and service key are picked up from settings
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.llm_client import (
    call_contentforge_llm,
    call_contentforge_llm_mock,
)


@pytest.mark.asyncio
async def test_mock_llm_returns_expected_format():
    """call_contentforge_llm_mock returns a valid gateway response dict."""
    result = await call_contentforge_llm_mock("Generate a title for Widget Pro")

    assert "content" in result
    assert "provider" in result
    assert result["provider"] == "mock"
    assert result["model"] == "mock-v1"
    assert result["cost_usd"] == 0.0
    assert isinstance(result["input_tokens"], int)
    assert isinstance(result["output_tokens"], int)
    assert result["cached"] is False
    assert result["latency_ms"] == 1


@pytest.mark.asyncio
async def test_mock_llm_custom_content():
    """call_contentforge_llm_mock respects custom content parameter."""
    custom = "Custom generated title: Amazing Widget"
    result = await call_contentforge_llm_mock(
        "Generate a title", content=custom
    )
    assert result["content"] == custom


@pytest.mark.asyncio
async def test_mock_llm_accepts_all_kwargs():
    """call_contentforge_llm_mock accepts all kwargs without error."""
    result = await call_contentforge_llm_mock(
        "Generate content",
        content="Test output",
        system="You are a helpful assistant",
        user_id="user-123",
        task_type="content_generation",
        max_tokens=500,
        temperature=0.8,
        json_mode=True,
    )
    assert result["content"] == "Test output"


@pytest.mark.asyncio
async def test_real_llm_client_sends_correct_payload():
    """call_contentforge_llm sends correct JSON to the gateway."""
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": "Generated title: Premium Widget Pro",
        "provider": "anthropic",
        "model": "claude-3-haiku",
        "input_tokens": 50,
        "output_tokens": 10,
        "cost_usd": 0.001,
        "cached": False,
        "latency_ms": 250,
    }
    mock_response.raise_for_status = MagicMock()

    with patch("ecomm_core.llm_client.httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client_instance

        result = await call_contentforge_llm(
            prompt="Generate a product title for Widget Pro",
            system="You are an SEO expert.",
            user_id="user-uuid-123",
            task_type="content_generation",
            max_tokens=100,
            temperature=0.5,
        )

        # Verify the response
        assert result["content"] == "Generated title: Premium Widget Pro"
        assert result["provider"] == "anthropic"

        # Verify the POST call was made with correct payload
        call_args = mock_client_instance.post.call_args
        payload = call_args[1]["json"] if "json" in call_args[1] else call_args.kwargs["json"]
        assert payload["prompt"] == "Generate a product title for Widget Pro"
        assert payload["system"] == "You are an SEO expert."
        assert payload["user_id"] == "user-uuid-123"
        assert payload["service"] == "contentforge"
        assert payload["task_type"] == "content_generation"
        assert payload["max_tokens"] == 100
        assert payload["temperature"] == 0.5


@pytest.mark.asyncio
async def test_real_llm_client_sends_service_key_header():
    """call_contentforge_llm sends X-Service-Key header when configured."""
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": "Test",
        "provider": "mock",
        "model": "test",
        "input_tokens": 5,
        "output_tokens": 1,
        "cost_usd": 0.0,
        "cached": False,
        "latency_ms": 10,
    }
    mock_response.raise_for_status = MagicMock()

    with patch("ecomm_core.llm_client.httpx.AsyncClient") as MockClient, \
         patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.service_name = "contentforge"
        mock_settings.llm_gateway_url = "http://test-gateway:8200"
        mock_settings.llm_gateway_key = "test-service-key-123"

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client_instance

        await call_contentforge_llm(prompt="Test prompt")

        call_args = mock_client_instance.post.call_args
        headers = call_args[1].get("headers", call_args.kwargs.get("headers", {}))
        assert headers.get("X-Service-Key") == "test-service-key-123"
