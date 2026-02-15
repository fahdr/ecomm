"""
LLM routing service.

Determines which provider and model to use for each request based on:
1. Customer+service-specific override
2. Customer-wide override
3. Service-level default
4. Global default from settings

For Developers:
    Call ``resolve_provider()`` to get a configured provider instance
    and model name. The function checks overrides in the database,
    falling back to the global config.

For QA Engineers:
    Test override priority: customer+service > customer > global.
    Verify that disabled providers are skipped.

For Project Managers:
    This is the "brain" that decides which AI handles each request.
    Admin controls routing through the Super Admin Dashboard.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.customer_override import CustomerOverride
from app.models.provider_config import ProviderConfig
from app.providers.base import AbstractLLMProvider, ProviderError
from app.providers.claude import ClaudeProvider
from app.providers.custom import CustomProvider
from app.providers.gemini import GeminiProvider
from app.providers.llama import LlamaProvider
from app.providers.mistral import MistralProvider
from app.providers.openai_provider import OpenAIProvider

PROVIDER_MAP: dict[str, type[AbstractLLMProvider]] = {
    "claude": ClaudeProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "llama": LlamaProvider,
    "mistral": MistralProvider,
    "custom": CustomProvider,
}


def _create_provider(config: ProviderConfig) -> AbstractLLMProvider:
    """
    Instantiate a provider from a ProviderConfig record.

    Args:
        config: The provider configuration from the database.

    Returns:
        Configured provider instance.

    Raises:
        ProviderError: If the provider type is unknown.
    """
    cls = PROVIDER_MAP.get(config.name)
    if not cls:
        raise ProviderError(config.name, f"Unknown provider type: {config.name}")
    return cls(
        api_key=config.api_key_encrypted,
        base_url=config.base_url,
        extra_config=config.extra_config,
    )


async def resolve_provider(
    db: AsyncSession,
    user_id: str,
    service_name: str,
) -> tuple[AbstractLLMProvider, str]:
    """
    Resolve the provider and model for a given user and service.

    Checks overrides in priority order:
    1. User + service-specific override
    2. User-wide override (service_name is null)
    3. Global default from settings

    Args:
        db: Database session.
        user_id: The requesting user's ID.
        service_name: The calling service name.

    Returns:
        Tuple of (provider_instance, model_name).

    Raises:
        ProviderError: If no enabled provider is found.
    """
    # Check for customer override (service-specific first, then generic)
    override = await db.execute(
        select(CustomerOverride)
        .where(
            CustomerOverride.user_id == user_id,
            CustomerOverride.service_name == service_name,
        )
        .limit(1)
    )
    override_row = override.scalar_one_or_none()

    if not override_row:
        override = await db.execute(
            select(CustomerOverride)
            .where(
                CustomerOverride.user_id == user_id,
                CustomerOverride.service_name.is_(None),
            )
            .limit(1)
        )
        override_row = override.scalar_one_or_none()

    if override_row:
        provider_name = override_row.provider_name
        model_name = override_row.model_name
    else:
        provider_name = settings.default_provider
        model_name = settings.default_model

    # Fetch provider config from DB
    config_result = await db.execute(
        select(ProviderConfig).where(
            ProviderConfig.name == provider_name,
            ProviderConfig.is_enabled.is_(True),
        )
    )
    config = config_result.scalar_one_or_none()

    if not config:
        raise ProviderError(
            provider_name,
            f"Provider '{provider_name}' is not configured or is disabled",
        )

    provider = _create_provider(config)
    return provider, model_name


async def get_all_providers(db: AsyncSession) -> list[ProviderConfig]:
    """
    Fetch all provider configurations, ordered by priority.

    Args:
        db: Database session.

    Returns:
        List of ProviderConfig records.
    """
    result = await db.execute(
        select(ProviderConfig).order_by(ProviderConfig.priority)
    )
    return list(result.scalars().all())
