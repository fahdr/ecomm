"""
Research run and result models for TrendScout product research.

A ResearchRun represents a single execution of the product-research pipeline.
Each run produces zero or more ResearchResult records, one per discovered
product across the requested data sources.

For Developers:
    ResearchRun tracks the lifecycle of a research job (pending -> running ->
    completed / failed). Keywords and sources are stored as PostgreSQL ARRAY
    columns for flexible querying. The score_config JSON column lets users
    customize the weighting of each scoring dimension.

    ResearchResult stores one discovered product. The `score` is the final
    weighted composite (0-100), `ai_analysis` holds Claude-generated insights,
    and `raw_data` preserves the original source payload for debugging.

For Project Managers:
    Research runs are the primary metered resource. Each plan tier allows a
    fixed number of runs per billing period (see constants/plans.py).
    Results are immutable once created — users add promising results to
    their Watchlist for tracking.

For QA Engineers:
    Test the full lifecycle: create run -> Celery task executes -> run
    status moves to 'completed' with results. Verify plan limits are
    enforced (free = 5 runs/month). Confirm cascading deletes remove
    results when a run is deleted.

For End Users:
    Start a research run by entering keywords and selecting data sources.
    Results appear when the run completes. Each result includes a composite
    score and optional AI analysis highlighting opportunity and risk.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ResearchRun(Base):
    """
    A single execution of the product-research pipeline.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the user who created this run.
        keywords: List of search keywords/phrases to research.
        sources: List of data source identifiers to scan
                 (e.g. 'aliexpress', 'tiktok', 'google_trends', 'reddit').
        status: Pipeline status — 'pending', 'running', 'completed', or 'failed'.
        score_config: Optional JSON overrides for scoring weights. Keys are
                      dimension names ('social', 'market', 'competition', 'seo',
                      'fundamentals') with float values summing to 1.0.
        results_count: Denormalized count of ResearchResult rows for fast display.
        error_message: Human-readable error if status == 'failed'.
        created_at: Timestamp when the run was created.
        completed_at: Timestamp when the run finished (completed or failed).
        results: One-to-many relationship to ResearchResult.
        owner: Back-reference to the owning User.
    """

    __tablename__ = "research_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False
    )
    sources: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )
    score_config: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    results_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    # Relationships
    results: Mapped[list["ResearchResult"]] = relationship(
        "ResearchResult",
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    owner = relationship("User", backref="research_runs", lazy="selectin")


class ResearchResult(Base):
    """
    A single product discovered during a research run.

    Attributes:
        id: Unique identifier (UUID v4).
        run_id: Foreign key to the parent ResearchRun.
        source: Data source that yielded this result
                (e.g. 'aliexpress', 'tiktok', 'google_trends', 'reddit').
        product_title: Human-readable product name/title.
        product_url: Direct URL to the product listing.
        image_url: URL to the product thumbnail/image (optional).
        price: Product price in the specified currency (optional).
        currency: ISO 4217 currency code (default 'USD').
        score: Composite weighted score from 0 to 100.
        ai_analysis: AI-generated analysis dict with keys: summary,
                     opportunity_score, risk_factors, recommended_price_range,
                     target_audience, marketing_angles (optional).
        raw_data: Original scraped/fetched data preserved for debugging.
        created_at: Timestamp when the result was stored.
        run: Back-reference to the parent ResearchRun.
    """

    __tablename__ = "research_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    product_title: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    product_url: Mapped[str] = mapped_column(
        String(2000), nullable=False
    )
    image_url: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )
    price: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    currency: Mapped[str] = mapped_column(
        String(3), default="USD", nullable=False
    )
    score: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False, index=True
    )
    ai_analysis: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    raw_data: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    run: Mapped["ResearchRun"] = relationship(
        "ResearchRun", back_populates="results"
    )
