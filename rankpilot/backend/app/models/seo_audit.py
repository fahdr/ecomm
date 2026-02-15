"""
SEO audit model for site health assessments.

SEO audits crawl a site and evaluate it against SEO best practices,
generating a score (0-100) along with categorized issues and
actionable recommendations. Audits are stored as historical records.

For Developers:
    `overall_score` is a float from 0 to 100.
    `issues` is a JSON column storing a list of issue objects, each with
    'severity' (critical/warning/info), 'category', 'message', and 'page_url'.
    `recommendations` is a JSON column storing a list of recommendation strings.
    Audits are triggered by the `run_seo_audit` Celery task.

For QA Engineers:
    Test audit creation via POST /api/v1/audits/run.
    Verify that the score is between 0 and 100.
    Verify that issues contain severity, category, and message fields.
    Test audit history listing with pagination.

For Project Managers:
    SEO audits provide ongoing value — users can track improvement over time.
    The score acts as a simple KPI for SEO health.

For End Users:
    Run an SEO audit to get a health score for your website.
    View specific issues and recommendations to improve your ranking.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SeoAudit(Base):
    """
    An SEO health audit for a site.

    Attributes:
        id: Unique identifier (UUID v4).
        site_id: Foreign key to the audited site.
        overall_score: SEO health score from 0.0 to 100.0.
        issues: JSON list of issues found during the audit.
        recommendations: JSON list of actionable improvement recommendations.
        pages_crawled: Number of pages analyzed during the audit.
        created_at: Audit execution timestamp.
        site: Related Site record.
    """

    __tablename__ = "seo_audits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    issues: Mapped[dict] = mapped_column(JSON, default=[], nullable=False)
    recommendations: Mapped[dict] = mapped_column(JSON, default=[], nullable=False)
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    site = relationship("Site", back_populates="seo_audits", lazy="selectin")
