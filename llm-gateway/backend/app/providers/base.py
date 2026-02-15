"""
Abstract base class for LLM providers.

All provider implementations (Claude, OpenAI, Gemini, etc.) must inherit
from AbstractLLMProvider and implement the ``generate`` method.

For Developers:
    Subclass this ABC and implement ``generate()``. The router service
    will call your provider based on configuration and overrides.
    Return a ``GenerationResult`` dataclass with token counts and content.

For QA Engineers:
    Each provider should be tested with mock HTTP responses to verify
    correct field mapping, error handling, and token counting.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class GenerationResult:
    """
    Result of an LLM generation request.

    Attributes:
        content: The generated text content.
        input_tokens: Number of tokens in the prompt.
        output_tokens: Number of tokens in the completion.
        model: The actual model used (may differ from requested).
        provider: The provider name.
        raw_response: Optional raw API response for debugging.
    """

    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    provider: str = ""
    raw_response: dict = field(default_factory=dict)


class ProviderError(Exception):
    """
    Raised when a provider fails to generate a response.

    Attributes:
        provider: Name of the provider that failed.
        status_code: HTTP status code from the provider (if applicable).
        message: Human-readable error message.
        retryable: Whether the caller should retry this request.
    """

    def __init__(
        self,
        provider: str,
        message: str,
        status_code: int | None = None,
        retryable: bool = False,
    ):
        self.provider = provider
        self.status_code = status_code
        self.retryable = retryable
        super().__init__(f"[{provider}] {message}")


class AbstractLLMProvider(ABC):
    """
    Abstract base for LLM provider integrations.

    Args:
        api_key: The provider's API key.
        base_url: Optional custom endpoint URL.
        extra_config: Optional provider-specific settings.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        extra_config: dict | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.extra_config = extra_config or {}

    @abstractmethod
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
        Generate a completion from the LLM.

        Args:
            prompt: The user message / prompt text.
            system: Optional system message.
            model: Model identifier to use.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (0.0 - 2.0).
            json_mode: Whether to request structured JSON output.

        Returns:
            GenerationResult with content and token counts.

        Raises:
            ProviderError: If the generation fails.
        """
        ...

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test that the provider is reachable and the API key is valid.

        Returns:
            True if the connection is healthy.

        Raises:
            ProviderError: If the connection test fails.
        """
        ...
