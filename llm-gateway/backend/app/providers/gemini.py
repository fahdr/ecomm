"""
Google Gemini provider implementation.

Uses the Gemini REST API for Google AI models.

For Developers:
    Uses the generativelanguage.googleapis.com endpoint with API key auth.
    Maps Gemini's ``usageMetadata`` to standard token counts.

For QA Engineers:
    Test with mock responses matching Gemini's generateContent format.
"""

import httpx

from app.providers.base import AbstractLLMProvider, GenerationResult, ProviderError


class GeminiProvider(AbstractLLMProvider):
    """Google Gemini API provider."""

    PROVIDER_NAME = "gemini"
    DEFAULT_MODEL = "gemini-2.0-flash"
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

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
        Generate content using the Gemini API.

        Args:
            prompt: User message text.
            system: Optional system instruction.
            model: Model ID (default: gemini-2.0-flash).
            max_tokens: Max output tokens.
            temperature: Sampling temperature.
            json_mode: If True, request JSON MIME type.

        Returns:
            GenerationResult with content and usage stats.
        """
        model = model or self.DEFAULT_MODEL
        url = f"{self.base_url or self.BASE_URL}/{model}:generateContent?key={self.api_key}"

        payload: dict = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, json=payload)
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

        candidates = data.get("candidates", [])
        content = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts)

        usage = data.get("usageMetadata", {})
        return GenerationResult(
            content=content,
            input_tokens=usage.get("promptTokenCount", 0),
            output_tokens=usage.get("candidatesTokenCount", 0),
            model=model,
            provider=self.PROVIDER_NAME,
            raw_response=data,
        )

    async def test_connection(self) -> bool:
        """Test the API key with a minimal request."""
        try:
            result = await self.generate(
                prompt="Say 'ok'", max_tokens=5, temperature=0.0
            )
            return bool(result.content)
        except ProviderError:
            return False
