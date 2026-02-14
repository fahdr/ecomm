"""
Service health snapshot model for the Super Admin Dashboard.

Records point-in-time health check results for each monitored service.
The health monitor pings each service periodically and stores the result
in this table for historical trending and alerting.

For Developers:
    Each row represents one health check for one service. The ``status``
    column stores one of ``healthy``, ``degraded``, or ``down``.
    The ``response_time_ms`` is nullable for cases where the service
    did not respond at all (status = ``down``).

    Indexes on ``service_name`` and ``checked_at`` support efficient
    queries for recent health history per service.

For QA Engineers:
    Test via ``GET /api/v1/admin/health/services`` (live pings) and
    ``GET /api/v1/admin/health/history`` (stored snapshots).
    Mock the httpx calls to simulate healthy, degraded, and down states.

For Project Managers:
    Health snapshots enable the admin dashboard to show uptime trends,
    response time graphs, and alert on degraded or down services.

For End Users:
    Health monitoring ensures the platform services remain reliable.
    Admins use this data to detect and resolve issues before they
    impact the customer experience.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ServiceHealthSnapshot(Base):
    """
    A point-in-time health check result for a monitored service.

    Attributes:
        id: Unique identifier (UUID v4), auto-generated.
        service_name: Name of the checked service (e.g., ``llm-gateway``).
        status: Health status — ``healthy``, ``degraded``, or ``down``.
        response_time_ms: Response time in milliseconds (None if down).
        checked_at: Timestamp when the health check was performed.
    """

    __tablename__ = "admin_health_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    service_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    response_time_ms: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
