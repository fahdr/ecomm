"""
Mistral AI provider implementation.

Uses Mistral's OpenAI-compatible Chat Completions endpoint.

For Developers:
    Mistral's API is OpenAI-compatible, so we inherit from OpenAIProvider.
    The default endpoint is ``https://api.mistral.ai/v1/chat/completions``.

For QA Engineers:
    Response format matches OpenAI. Test with Mistral-specific models.
"""

from app.providers.openai_provider import OpenAIProvider


class MistralProvider(OpenAIProvider):
    """
    Mistral AI provider.

    Inherits from OpenAIProvider since Mistral's API is OpenAI-compatible.
    """

    PROVIDER_NAME = "mistral"
    DEFAULT_MODEL = "mistral-large-latest"
    DEFAULT_URL = "https://api.mistral.ai/v1/chat/completions"
