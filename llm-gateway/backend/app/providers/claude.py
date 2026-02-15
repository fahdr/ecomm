"""
Anthropic Claude provider implementation.

Uses the Anthropic SDK to call Claude models (Haiku, Sonnet, Opus).

For Developers:
    Requires ``anthropic`` SDK. The API key is passed at construction time
    from the ProviderConfig. Supports JSON mode via tool-use or system prompts.

For QA Engineers:
    Test with mock responses matching the Anthropic Messages API format.
    Verify token counts come from ``usage.input_tokens`` and ``usage.output_tokens``.
"""

import httpx

from app.providers.base import AbstractLLMProvider, GenerationResult, ProviderError


class ClaudeProvider(AbstractLLMProvider):
    """
    Anthropic Claude LLM provider.

    Uses the Messages API at https://api.anthropic.com/v1/messages.
    """

    PROVIDER_NAME = "claude"
    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
    API_URL = "https://api.anthropic.com/v1/messages"

    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> GenerationResult:
        """
        Generate a completion using the Anthropic Messages API.

        Args:
            prompt: User message text.
            system: Optional system message.
            model: Model ID (default: claude-sonnet-4-5-20250929).
            max_tokens: Max completion tokens.
            temperature: Sampling temperature.
            json_mode: If True, append JSON instruction to system.

        Returns:
            GenerationResult with content and usage stats.
        """
        model = model or self.DEFAULT_MODEL
        sys_msg = system
        if json_mode and system:
            sys_msg += "\n\nRespond with valid JSON only."
        elif json_mode:
            sys_msg = "Respond with valid JSON only."

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if sys_msg:
            payload["system"] = sys_msg

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(self.API_URL, json=payload, headers=headers)
                if resp.status_code != 200:
                    raise ProviderError(
                        self.PROVIDER_NAME,
                        f"API returned {resp.status_code}: {resp.text}",
                        status_code=resp.status_code,
                        retryable=resp.status_code in (429, 500, 502, 503),
                    )
                data = resp.json()
        except httpx.HTTPError as e:
            raise ProviderError(
                self.PROVIDER_NAME, f"HTTP error: {e}", retryable=True
            ) from e

        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        usage = data.get("usage", {})
        return GenerationResult(
            content=content,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            model=data.get("model", model),
            provider=self.PROVIDER_NAME,
            raw_response=data,
        )

    async def test_connection(self) -> bool:
        """Test the API key with a minimal request."""
        try:
            result = await self.generate(
                prompt="Say 'ok'",
                model=self.DEFAULT_MODEL,
                max_tokens=5,
                temperature=0.0,
            )
            return bool(result.content)
        except ProviderError:
            return False
