"""
LLM Provider configuration model.

Stores API keys and settings for each AI provider (Anthropic, OpenAI, etc.).
Admin manages these via the Super Admin Dashboard.

For Developers:
    API keys are stored encrypted. The ``models`` JSON field lists available
    models for each provider. Rate limits are per-provider, not per-model.

For QA Engineers:
    Test CRUD via /api/v1/providers endpoints.
    Verify that disabling a provider prevents generation requests.

For Project Managers:
    Each provider config represents one AI vendor. The admin adds their
    API key, selects which models to enable, and sets rate limits.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProviderConfig(Base):
    """
    Configuration for an LLM provider.

    Attributes:
        id: Unique identifier (UUID v4).
        name: Provider identifier (claude, openai, gemini, llama, mistral, custom).
        display_name: Human-readable label (e.g., "Anthropic Claude").
        api_key_encrypted: Encrypted API key for the provider.
        base_url: Custom endpoint URL (for OpenAI-compatible providers).
        models: JSON list of available model identifiers.
        is_enabled: Whether this provider accepts requests.
        rate_limit_rpm: Requests per minute limit for this provider.
        rate_limit_tpm: Tokens per minute limit for this provider.
        priority: Ordering priority for fallback routing (lower = preferred).
        extra_config: Additional provider-specific configuration.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
    """

    __tablename__ = "llm_provider_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    models: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    rate_limit_tpm: Mapped[int] = mapped_column(Integer, default=100000, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    extra_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
