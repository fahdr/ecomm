"""
Configuration for the LLM Gateway microservice.

Centralizes all environment variables and defaults for the gateway.
Admin-configurable provider API keys are stored in the database, not here.

For Developers:
    This uses pydantic-settings to load from environment variables.
    DATABASE_URL should point to the gateway's own database.

For QA Engineers:
    The service runs on port 8200 by default.
    REDIS_URL is used for response caching and rate limiting.

For Project Managers:
    The LLM Gateway is the single point of contact for all AI calls.
    API keys for providers (OpenAI, Anthropic, etc.) are managed via
    the admin dashboard, not hardcoded here.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Gateway configuration loaded from environment variables.

    Attributes:
        service_name: Identifier for health checks and logging.
        service_port: HTTP port the gateway listens on.
        database_url: Async PostgreSQL connection string.
        redis_url: Redis connection for caching and rate limiting.
        service_key: Shared secret that downstream services use to authenticate.
        debug: Enable verbose SQL logging and debug endpoints.
        cache_ttl_seconds: Default TTL for cached LLM responses.
        max_retries: Max retries on transient provider errors.
        default_provider: Fallback provider when no override is configured.
        default_model: Fallback model for the default provider.
    """

    service_name: str = "llm-gateway"
    service_port: int = 8200
    database_url: str = "postgresql+asyncpg://dropship:dropship_dev@db:5432/dropshipping"
    redis_url: str = "redis://redis:6379/3"
    service_key: str = "dev-gateway-key"
    debug: bool = False
    cache_ttl_seconds: int = 3600
    max_retries: int = 2
    default_provider: str = "claude"
    default_model: str = "claude-sonnet-4-5-20250929"

    model_config = {"env_prefix": "LLM_GATEWAY_"}


settings = Settings()
