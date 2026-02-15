"""
Customer LLM override model.

Allows per-customer or per-service provider and model overrides.
When a customer has an override, their requests route to that
provider/model instead of the global default.

For Developers:
    Overrides are checked in order: customer+service → customer → service → global.
    The ``service_name`` field is optional; if null, the override applies to all services.

For QA Engineers:
    Test that creating an override for a user changes their LLM routing.
    Verify fallback behavior when the override provider is disabled.

For Project Managers:
    This lets the admin give specific customers a different AI model,
    e.g., a premium customer gets Claude Opus while free users get Haiku.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CustomerOverride(Base):
    """
    Per-customer LLM provider/model override.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: The customer's user ID from the service.
        service_name: Optional service restriction (null = all services).
        provider_name: Override provider (must match a ProviderConfig.name).
        model_name: Override model identifier.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
    """

    __tablename__ = "llm_customer_overrides"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    service_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
