"""
OpenAI provider implementation.

Uses the OpenAI Chat Completions API for GPT models.

For Developers:
    Works with any OpenAI-compatible API (Azure, local, etc.) via base_url.
    JSON mode uses ``response_format: { type: "json_object" }``.

For QA Engineers:
    Verify that token counts map to ``usage.prompt_tokens`` and
    ``usage.completion_tokens`` in the OpenAI response format.
"""

import httpx

from app.providers.base import AbstractLLMProvider, GenerationResult, ProviderError


class OpenAIProvider(AbstractLLMProvider):
    """
    OpenAI Chat Completions API provider.

    Also compatible with Azure OpenAI and other OpenAI-compatible endpoints.
    """

    PROVIDER_NAME = "openai"
    DEFAULT_MODEL = "gpt-4o"
    DEFAULT_URL = "https://api.openai.com/v1/chat/completions"

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
        Generate a completion using the OpenAI Chat Completions API.

        Args:
            prompt: User message text.
            system: Optional system message.
            model: Model ID (default: gpt-4o).
            max_tokens: Max completion tokens.
            temperature: Sampling temperature.
            json_mode: If True, use JSON response format.

        Returns:
            GenerationResult with content and usage stats.
        """
        model = model or self.DEFAULT_MODEL
        url = self.base_url or self.DEFAULT_URL

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
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

        choices = data.get("choices", [])
        content = choices[0]["message"]["content"] if choices else ""

        usage = data.get("usage", {})
        return GenerationResult(
            content=content,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
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
