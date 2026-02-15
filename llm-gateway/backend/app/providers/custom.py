"""
Custom OpenAI-compatible provider.

Supports any LLM endpoint that implements the OpenAI Chat Completions API
(e.g., local vLLM, Ollama, LiteLLM proxy, etc.).

For Developers:
    The ``base_url`` must be set in the ProviderConfig to point at the
    custom endpoint. Authentication uses Bearer token (API key).

For QA Engineers:
    Test with a mock OpenAI-compatible server.
"""

from app.providers.openai_provider import OpenAIProvider


class CustomProvider(OpenAIProvider):
    """
    Custom OpenAI-compatible provider.

    base_url must be set in the ProviderConfig. Inherits all
    OpenAI request/response handling.
    """

    PROVIDER_NAME = "custom"
    DEFAULT_MODEL = "default"
    DEFAULT_URL = "http://localhost:8080/v1/chat/completions"
