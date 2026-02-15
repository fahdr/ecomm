"""
LLM usage log model.

Records every LLM API call for cost tracking, analytics, and debugging.
Each row represents one generation request with token counts and cost.

For Developers:
    Logs are append-only. The ``cost_usd`` is calculated from per-provider
    pricing at the time of the request. ``latency_ms`` tracks end-to-end
    time including network overhead.

For QA Engineers:
    Verify that every /generate call creates a usage log entry.
    Check that cached responses still log (with cached=True).

For Project Managers:
    Usage logs power the cost dashboard. They show which services/customers
    consume the most AI, enabling cost allocation and budget alerts.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UsageLog(Base):
    """
    Record of a single LLM generation request.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: The requesting customer's user ID.
        service_name: Which ecomm service made the request.
        task_type: Caller-defined task label (e.g., "product_analysis").
        provider_name: Provider that handled the request.
        model_name: Specific model used.
        input_tokens: Number of input/prompt tokens.
        output_tokens: Number of output/completion tokens.
        cost_usd: Estimated cost in USD.
        latency_ms: End-to-end latency in milliseconds.
        cached: Whether the response came from cache.
        error: Error message if the request failed.
        created_at: Request timestamp.
    """

    __tablename__ = "llm_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
