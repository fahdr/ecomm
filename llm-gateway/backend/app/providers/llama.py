"""
Llama provider via Together AI / OpenAI-compatible API.

Uses Together AI's OpenAI-compatible endpoint for Meta Llama models.

For Developers:
    Together AI uses the same Chat Completions format as OpenAI.
    Set ``base_url`` to ``https://api.together.xyz/v1/chat/completions``.

For QA Engineers:
    Response format is identical to OpenAI. Test token count mapping.
"""

from app.providers.openai_provider import OpenAIProvider


class LlamaProvider(OpenAIProvider):
    """
    Meta Llama provider via Together AI.

    Inherits from OpenAIProvider since Together AI is OpenAI-compatible.
    """

    PROVIDER_NAME = "llama"
    DEFAULT_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    DEFAULT_URL = "https://api.together.xyz/v1/chat/completions"
