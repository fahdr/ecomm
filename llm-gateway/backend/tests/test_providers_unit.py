"""
Unit tests for LLM provider implementations.

Tests each provider's response parsing with mocked HTTP responses.

For Developers:
    Uses respx to mock httpx calls. Each test verifies that the provider
    correctly maps the API response to a GenerationResult.

For QA Engineers:
    Covers: Claude, OpenAI, Gemini response parsing and error handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.base import GenerationResult, ProviderError
from app.providers.claude import ClaudeProvider
from app.providers.gemini import GeminiProvider
from app.providers.llama import LlamaProvider
from app.providers.mistral import MistralProvider
from app.providers.openai_provider import OpenAIProvider


@pytest.mark.asyncio
async def test_claude_generate():
    """Claude provider parses Messages API response correctly."""
    provider = ClaudeProvider(api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "content": [{"type": "text", "text": "Hello from Claude"}],
        "model": "claude-sonnet-4-5-20250929",
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await provider.generate(prompt="Hi", model="claude-sonnet-4-5-20250929")

    assert isinstance(result, GenerationResult)
    assert result.content == "Hello from Claude"
    assert result.input_tokens == 10
    assert result.output_tokens == 5
    assert result.provider == "claude"


@pytest.mark.asyncio
async def test_claude_error():
    """Claude provider raises ProviderError on API error."""
    provider = ClaudeProvider(api_key="bad-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(ProviderError) as exc:
            await provider.generate(prompt="Hi")
        assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_openai_generate():
    """OpenAI provider parses Chat Completions response correctly."""
    provider = OpenAIProvider(api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Hello from OpenAI"}}],
        "model": "gpt-4o",
        "usage": {"prompt_tokens": 15, "completion_tokens": 8},
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await provider.generate(prompt="Hi", model="gpt-4o")

    assert result.content == "Hello from OpenAI"
    assert result.input_tokens == 15
    assert result.output_tokens == 8
    assert result.provider == "openai"


@pytest.mark.asyncio
async def test_gemini_generate():
    """Gemini provider parses generateContent response correctly."""
    provider = GeminiProvider(api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"text": "Hello from Gemini"}]}}
        ],
        "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 6},
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await provider.generate(prompt="Hi")

    assert result.content == "Hello from Gemini"
    assert result.input_tokens == 12
    assert result.output_tokens == 6
    assert result.provider == "gemini"


@pytest.mark.asyncio
async def test_llama_inherits_openai():
    """Llama provider uses OpenAI-compatible API."""
    provider = LlamaProvider(api_key="test-key")
    assert provider.PROVIDER_NAME == "llama"
    assert "together.xyz" in provider.DEFAULT_URL


@pytest.mark.asyncio
async def test_mistral_inherits_openai():
    """Mistral provider uses OpenAI-compatible API."""
    provider = MistralProvider(api_key="test-key")
    assert provider.PROVIDER_NAME == "mistral"
    assert "mistral.ai" in provider.DEFAULT_URL


@pytest.mark.asyncio
async def test_claude_json_mode():
    """Claude provider appends JSON instruction in json_mode."""
    provider = ClaudeProvider(api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "content": [{"type": "text", "text": '{"result": "ok"}'}],
        "model": "claude-sonnet-4-5-20250929",
        "usage": {"input_tokens": 20, "output_tokens": 10},
    }

    with patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
        result = await provider.generate(
            prompt="Return JSON", system="Be helpful", json_mode=True
        )

    assert result.content == '{"result": "ok"}'
    # Verify system message was modified
    call_args = mock_post.call_args
    payload = call_args.kwargs.get("json") or call_args[1].get("json")
    assert "Respond with valid JSON only" in payload["system"]


@pytest.mark.asyncio
async def test_retryable_error():
    """429 and 5xx errors are marked as retryable."""
    provider = ClaudeProvider(api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Rate limited"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(ProviderError) as exc:
            await provider.generate(prompt="Hi")
        assert exc.value.retryable is True
