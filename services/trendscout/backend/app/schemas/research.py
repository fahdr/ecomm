"""
Pydantic schemas for research runs, results, watchlist, and source configs.

Defines request/response data structures for all TrendScout feature endpoints.
All schemas use Pydantic v2 with strict validation.

For Developers:
    - Create schemas validate user input with constraints (min_length, etc.).
    - Response schemas use `from_attributes = True` for ORM-to-Pydantic mapping.
    - Paginated responses follow the standard envelope:
      { "items": [...], "total": N, "page": 1, "per_page": 20 }
    - Single-item responses use: { "data": <T>, "error": null }

For Project Managers:
    These schemas define the API contract for all research-related endpoints.
    Changes here affect both the backend validation and the dashboard integration.

For QA Engineers:
    Test validation by sending invalid payloads (empty keywords, bad source
    names, negative scores). Verify that response shapes match these schemas.

For End Users:
    These data structures describe the information you send when creating
    research runs and the format of the results you receive back.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ─── Research Run Schemas ────────────────────────────────────────────

class ResearchRunCreate(BaseModel):
    """
    Request body for creating a new research run.

    Attributes:
        keywords: List of search terms to research (1-10 keywords).
        sources: List of data source identifiers to scan. Valid values:
                 'aliexpress', 'tiktok', 'google_trends', 'reddit'.
        score_config: Optional custom scoring weight overrides. Keys are
                      dimension names with float values summing to ~1.0.
    """

    keywords: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Search keywords (1-10 terms)",
    )
    sources: list[str] = Field(
        default=["aliexpress", "google_trends"],
        min_length=1,
        description="Data sources to scan",
    )
    score_config: dict | None = Field(
        default=None,
        description="Optional scoring weight overrides",
    )


class ResearchResultResponse(BaseModel):
    """
    Response schema for a single research result.

    Attributes:
        id: Result unique identifier.
        run_id: Parent research run identifier.
        source: Data source that yielded this result.
        product_title: Product name/title.
        product_url: Direct URL to the product listing.
        image_url: Product image URL (optional).
        price: Product price (optional).
        currency: Price currency code.
        score: Composite weighted score (0-100).
        ai_analysis: AI-generated analysis (optional).
        raw_data: Original source data.
        created_at: Timestamp when the result was stored.
    """

    id: uuid.UUID
    run_id: uuid.UUID
    source: str
    product_title: str
    product_url: str
    image_url: str | None
    price: float | None
    currency: str
    score: float
    ai_analysis: dict | None
    raw_data: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class ResearchRunResponse(BaseModel):
    """
    Response schema for a research run with optional inline results.

    Attributes:
        id: Run unique identifier.
        user_id: Owning user identifier.
        keywords: List of search keywords used.
        sources: List of data sources scanned.
        status: Current run status (pending, running, completed, failed).
        score_config: Scoring weight configuration used.
        results_count: Total number of results found.
        error_message: Error description if status is 'failed'.
        created_at: Run creation timestamp.
        completed_at: Run completion timestamp (if finished).
        results: Inline list of results (present on detail endpoint).
    """

    id: uuid.UUID
    user_id: uuid.UUID
    keywords: list[str]
    sources: list[str]
    status: str
    score_config: dict | None
    results_count: int
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    results: list[ResearchResultResponse] = []

    model_config = {"from_attributes": True}


class ResearchRunListResponse(BaseModel):
    """
    Paginated list of research runs.

    Attributes:
        items: List of research runs for the current page.
        total: Total number of runs matching the query.
        page: Current page number (1-indexed).
        per_page: Number of items per page.
    """

    items: list[ResearchRunResponse]
    total: int
    page: int
    per_page: int


class ResearchResultListResponse(BaseModel):
    """
    Paginated list of research results.

    Attributes:
        items: List of research results for the current page.
        total: Total number of results matching the query.
        page: Current page number (1-indexed).
        per_page: Number of items per page.
    """

    items: list[ResearchResultResponse]
    total: int
    page: int
    per_page: int


# ─── Watchlist Schemas ───────────────────────────────────────────────

class WatchlistItemCreate(BaseModel):
    """
    Request body for adding a research result to the watchlist.

    Attributes:
        result_id: UUID of the ResearchResult to save.
        notes: Optional notes about why this product is interesting.
    """

    result_id: uuid.UUID
    notes: str | None = None


class WatchlistItemUpdate(BaseModel):
    """
    Request body for updating a watchlist item.

    Attributes:
        status: New tracking status ('watching', 'imported', 'dismissed').
        notes: Updated notes (optional — omit to leave unchanged).
    """

    status: str | None = Field(
        default=None,
        description="New status: watching, imported, or dismissed",
    )
    notes: str | None = Field(
        default=None,
        description="Updated notes",
    )


class WatchlistResultSnapshot(BaseModel):
    """
    Inline snapshot of the linked ResearchResult for watchlist display.

    Attributes:
        id: Result unique identifier.
        source: Data source that found this product.
        product_title: Product name.
        product_url: Product listing URL.
        image_url: Product image URL.
        price: Product price.
        currency: Price currency code.
        score: Composite score (0-100).
    """

    id: uuid.UUID
    source: str
    product_title: str
    product_url: str
    image_url: str | None
    price: float | None
    currency: str
    score: float

    model_config = {"from_attributes": True}


class WatchlistItemResponse(BaseModel):
    """
    Response schema for a single watchlist item.

    Attributes:
        id: Watchlist item unique identifier.
        user_id: Owning user identifier.
        result_id: Linked ResearchResult identifier.
        status: Current tracking status.
        notes: User's notes.
        created_at: When the item was added.
        updated_at: When the item was last modified.
        result: Inline result snapshot for display.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    result_id: uuid.UUID
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
    result: WatchlistResultSnapshot | None = None

    model_config = {"from_attributes": True}


class WatchlistListResponse(BaseModel):
    """
    Paginated list of watchlist items.

    Attributes:
        items: List of watchlist items for the current page.
        total: Total number of items matching the query.
        page: Current page number (1-indexed).
        per_page: Number of items per page.
    """

    items: list[WatchlistItemResponse]
    total: int
    page: int
    per_page: int


# ─── Source Config Schemas ───────────────────────────────────────────

class SourceConfigCreate(BaseModel):
    """
    Request body for adding a new source configuration.

    Attributes:
        source_type: External source identifier ('aliexpress', 'tiktok',
                     'google_trends', 'reddit').
        credentials: Source-specific authentication credentials (API keys, tokens).
        settings: Source-specific settings (region, categories, language).
    """

    source_type: str = Field(
        ...,
        description="Source identifier: aliexpress, tiktok, google_trends, reddit",
    )
    credentials: dict = Field(
        default_factory=dict,
        description="API keys, OAuth tokens, etc.",
    )
    settings: dict = Field(
        default_factory=dict,
        description="Region, category filters, language, etc.",
    )


class SourceConfigUpdate(BaseModel):
    """
    Request body for updating an existing source configuration.

    Attributes:
        credentials: Updated credentials (optional — omit to leave unchanged).
        settings: Updated settings (optional — omit to leave unchanged).
        is_active: Toggle source active/inactive (optional).
    """

    credentials: dict | None = None
    settings: dict | None = None
    is_active: bool | None = None


class SourceConfigResponse(BaseModel):
    """
    Response schema for a source configuration.

    Note: credentials are redacted — only key names are returned, not values.

    Attributes:
        id: Config unique identifier.
        user_id: Owning user identifier.
        source_type: External source identifier.
        has_credentials: Whether credentials have been configured.
        settings: Source-specific settings.
        is_active: Whether the source is enabled.
        created_at: Config creation timestamp.
        updated_at: Last modification timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    source_type: str
    has_credentials: bool
    settings: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SourceConfigListResponse(BaseModel):
    """
    List of source configurations (not paginated — users have few configs).

    Attributes:
        items: All source configurations for the user.
    """

    items: list[SourceConfigResponse]
