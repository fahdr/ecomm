"""
Core research service for TrendScout.

Handles CRUD operations for research runs, results, watchlist items,
and source configurations. Enforces plan-based resource limits.

For Developers:
    All functions accept an AsyncSession and operate within the caller's
    transaction. Use `await db.flush()` after mutations to get IDs without
    committing. The `check_run_limit` function counts runs in the current
    billing period and compares against the plan's max_items.

    Watchlist operations enforce the max_secondary plan limit.

For Project Managers:
    This service is the central business logic layer. It sits between
    the API routes and the database models, enforcing plan limits and
    business rules.

For QA Engineers:
    Test plan limit enforcement by creating runs/watchlist items up to
    the limit and verifying the next attempt is rejected with 403.
    Test pagination with varying page/per_page values.
    Test cascading deletes when runs or watchlist items are removed.

For End Users:
    The research service powers all product research functionality:
    starting runs, viewing results, managing your watchlist, and
    configuring data sources.
"""

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants.plans import PLAN_LIMITS
from app.models.research import ResearchResult, ResearchRun
from app.models.source_config import SourceConfig
from app.models.store_connection import StoreConnection
from app.models.user import User
from app.models.watchlist import WatchlistItem
from app.utils.helpers import get_current_billing_period

logger = logging.getLogger(__name__)


# ─── Research Runs ───────────────────────────────────────────────────

async def check_run_limit(db: AsyncSession, user: User) -> bool:
    """
    Check whether the user has remaining research runs in the current period.

    Counts runs created by this user within the current billing month
    and compares against the plan's max_items limit.

    Args:
        db: Async database session.
        user: The authenticated user.

    Returns:
        True if the user can create another run, False if limit reached.
    """
    plan_limits = PLAN_LIMITS[user.plan]
    if plan_limits.max_items == -1:
        return True  # Unlimited

    period_start, period_end = get_current_billing_period()
    result = await db.execute(
        select(func.count(ResearchRun.id)).where(
            ResearchRun.user_id == user.id,
            ResearchRun.created_at >= datetime.combine(period_start, datetime.min.time()),
            ResearchRun.created_at < datetime.combine(period_end, datetime.min.time()),
        )
    )
    count = result.scalar_one()
    return count < plan_limits.max_items


async def get_run_count_this_period(db: AsyncSession, user_id: uuid.UUID) -> int:
    """
    Get the number of research runs created by the user this billing period.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Count of runs in the current billing period.
    """
    period_start, period_end = get_current_billing_period()
    result = await db.execute(
        select(func.count(ResearchRun.id)).where(
            ResearchRun.user_id == user_id,
            ResearchRun.created_at >= datetime.combine(period_start, datetime.min.time()),
            ResearchRun.created_at < datetime.combine(period_end, datetime.min.time()),
        )
    )
    return result.scalar_one()


async def create_research_run(
    db: AsyncSession,
    user: User,
    keywords: list[str],
    sources: list[str],
    score_config: dict | None = None,
) -> ResearchRun:
    """
    Create a new research run and prepare it for background execution.

    Validates plan limits before creation. The actual data fetching and
    scoring happens in the Celery task dispatched by the API route.

    Args:
        db: Async database session.
        user: The authenticated user creating the run.
        keywords: List of search keywords to research.
        sources: List of data source identifiers to scan.
        score_config: Optional custom scoring weight overrides.

    Returns:
        The newly created ResearchRun in 'pending' status.

    Raises:
        ValueError: If the user has exceeded their plan's run limit.
    """
    can_run = await check_run_limit(db, user)
    if not can_run:
        raise ValueError(
            f"Research run limit reached for {user.plan.value} plan. "
            f"Upgrade your plan for more runs."
        )

    # Validate sources
    valid_sources = {"aliexpress", "tiktok", "google_trends", "reddit"}
    sanitized_sources = [s for s in sources if s in valid_sources]
    if not sanitized_sources:
        sanitized_sources = ["aliexpress", "google_trends"]

    run = ResearchRun(
        user_id=user.id,
        keywords=[k.strip() for k in keywords if k.strip()],
        sources=sanitized_sources,
        score_config=score_config,
        status="pending",
    )
    db.add(run)
    await db.flush()
    # Eagerly load the results relationship so it's available outside
    # the async session context (prevents MissingGreenlet during
    # FastAPI response serialization).
    await db.refresh(run, attribute_names=["results"])
    return run


async def get_research_runs(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[ResearchRun], int]:
    """
    Get a paginated list of research runs for a user.

    Ordered by creation date (newest first). Does not load results —
    use `get_research_run` for full details.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        page: Page number (1-indexed).
        per_page: Items per page.

    Returns:
        Tuple of (list of ResearchRun, total count).
    """
    # Count total
    count_result = await db.execute(
        select(func.count(ResearchRun.id)).where(
            ResearchRun.user_id == user_id
        )
    )
    total = count_result.scalar_one()

    # Fetch page with eagerly loaded results to prevent MissingGreenlet
    # during FastAPI response serialization.
    offset = (page - 1) * per_page
    result = await db.execute(
        select(ResearchRun)
        .options(selectinload(ResearchRun.results))
        .where(ResearchRun.user_id == user_id)
        .order_by(ResearchRun.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    runs = list(result.scalars().all())
    return runs, total


async def get_research_run(
    db: AsyncSession,
    run_id: uuid.UUID,
) -> ResearchRun | None:
    """
    Get a single research run with its results eagerly loaded.

    Args:
        db: Async database session.
        run_id: The run's UUID.

    Returns:
        The ResearchRun if found, None otherwise.
    """
    result = await db.execute(
        select(ResearchRun)
        .options(selectinload(ResearchRun.results))
        .where(ResearchRun.id == run_id)
    )
    return result.scalar_one_or_none()


async def get_result(
    db: AsyncSession,
    result_id: uuid.UUID,
) -> ResearchResult | None:
    """
    Get a single research result by ID.

    Args:
        db: Async database session.
        result_id: The result's UUID.

    Returns:
        The ResearchResult if found, None otherwise.
    """
    result = await db.execute(
        select(ResearchResult).where(ResearchResult.id == result_id)
    )
    return result.scalar_one_or_none()


async def delete_research_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """
    Delete a research run and all its results.

    Only the owning user can delete their runs. Results are cascade-deleted
    by the database foreign key constraint.

    Args:
        db: Async database session.
        run_id: The run's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        True if deleted, False if not found or not owned by user.
    """
    result = await db.execute(
        select(ResearchRun).where(
            ResearchRun.id == run_id,
            ResearchRun.user_id == user_id,
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        return False

    await db.delete(run)
    await db.flush()
    return True


# ─── Enhanced Research Pipeline ──────────────────────────────────────


async def run_product_research(
    db: AsyncSession,
    user_id: uuid.UUID,
    research_run_id: uuid.UUID,
    keywords: list[str],
    config: dict | None = None,
) -> list[ResearchResult]:
    """
    Execute the full product research pipeline for a given run.

    Steps:
        1. Fetch active store connections for product matching.
        2. Generate candidate products from connected stores and keywords.
        3. Score each product using configurable weights.
        4. Call the LLM Gateway for structured AI analysis.
        5. Store scored results in the database.
        6. Update the ResearchRun status to 'completed'.

    For Developers:
        This replaces the mock Celery task logic with a real async pipeline.
        If the LLM Gateway is unavailable, it falls back to mock analysis
        (see ``app.services.ai_analysis_service``).

        The function is designed to be called either from an async task
        runner or directly in tests.

    For Project Managers:
        This is the core research engine.  Each call consumes one research
        run from the user's plan quota.

    For QA Engineers:
        Mock ``call_llm`` and the store connection product fetcher to test
        the pipeline in isolation.  Verify run status transitions from
        'running' to 'completed' (or 'failed' on error).

    For End Users:
        When you start a research run, this is the logic that discovers
        products, scores them, and generates AI insights.

    Args:
        db: Async database session.
        user_id: UUID of the user running the research.
        research_run_id: UUID of the ResearchRun to populate.
        keywords: List of search keywords.
        config: Optional scoring weight overrides.

    Returns:
        List of created ResearchResult objects.
    """
    from app.services.scoring_service import score_product
    from app.services.ai_analysis_service import analyze_product

    # Mark run as running
    run_result = await db.execute(
        select(ResearchRun).where(ResearchRun.id == research_run_id)
    )
    run = run_result.scalar_one_or_none()
    if not run:
        logger.error(f"Research run not found: {research_run_id}")
        return []

    run.status = "running"
    await db.flush()

    all_results: list[ResearchResult] = []

    try:
        # Fetch active store connections for product data
        active_connections = await get_active_connections(db, user_id)

        # Generate candidate products from connected stores
        candidate_products = _generate_candidates_from_connections(
            active_connections, keywords
        )

        # Score and analyze each candidate
        for product_data in candidate_products:
            # Score product using enhanced scoring
            product_score = score_product(product_data.get("raw_data", product_data), config)

            # Attempt LLM analysis, fall back to mock
            try:
                from app.services.llm_client import call_llm, LLMGatewayError

                llm_prompt = _build_analysis_prompt(product_data, product_score)
                llm_response = await call_llm(
                    prompt=llm_prompt,
                    system="You are a dropshipping product analyst. Return JSON only.",
                    user_id=str(user_id),
                    task_type="product_analysis",
                )
                ai_analysis = _parse_llm_analysis(llm_response)
            except Exception as exc:
                logger.warning(f"LLM analysis failed, using mock: {exc}")
                ai_analysis = await analyze_product({
                    "product_title": product_data.get("product_title", "Unknown"),
                    "price": product_data.get("price", 0),
                    "source": product_data.get("source", "unknown"),
                    "score": product_score,
                    "raw_data": product_data.get("raw_data", {}),
                })

            result = ResearchResult(
                run_id=research_run_id,
                source=product_data.get("source", "platform"),
                product_title=product_data.get("product_title", "Unknown Product"),
                product_url=product_data.get("product_url", ""),
                image_url=product_data.get("image_url"),
                price=product_data.get("price"),
                currency=product_data.get("currency", "USD"),
                score=product_score,
                ai_analysis=ai_analysis,
                raw_data=product_data.get("raw_data", {}),
            )
            db.add(result)
            all_results.append(result)

        # Mark run as completed
        run.status = "completed"
        run.results_count = len(all_results)
        run.completed_at = datetime.now(UTC).replace(tzinfo=None)
        await db.flush()

        logger.info(
            f"Research run {research_run_id} completed with {len(all_results)} results"
        )

    except Exception as exc:
        logger.error(f"Research run {research_run_id} failed: {exc}")
        run.status = "failed"
        run.error_message = str(exc)[:1000]
        run.completed_at = datetime.now(UTC).replace(tzinfo=None)
        await db.flush()

    return all_results


def _generate_candidates_from_connections(
    connections: list[StoreConnection],
    keywords: list[str],
) -> list[dict]:
    """
    Generate candidate product data dicts from store connections and keywords.

    For Developers:
        In a real implementation, this would call each store's API to
        search for products matching the keywords.  Currently generates
        simulated product data based on the connection platform and
        keywords for demonstration purposes.

    Args:
        connections: List of active StoreConnection objects.
        keywords: Search keywords to match.

    Returns:
        List of product data dicts ready for scoring.
    """
    import hashlib
    import random

    candidates = []

    for conn in connections:
        keyword_str = " ".join(keywords)
        seed_str = f"{conn.store_url}_{keyword_str}_{conn.platform}"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        # Generate 3-5 products per connection
        count = rng.randint(3, 5)
        for i in range(count):
            price = round(rng.uniform(5.99, 79.99), 2)
            supplier_cost = round(price * rng.uniform(0.2, 0.6), 2)
            title = f"{keywords[0].title()} from {conn.platform.title()} #{i+1}"

            candidates.append({
                "product_title": title,
                "product_url": f"{conn.store_url}/products/{rng.randint(1000, 9999)}",
                "image_url": f"{conn.store_url}/images/{rng.randint(1000, 9999)}.jpg",
                "price": price,
                "supplier_cost": supplier_cost,
                "sell_price": round(price * rng.uniform(1.5, 3.0), 2),
                "currency": "USD",
                "source": conn.platform,
                "raw_data": {
                    "market": {
                        "search_volume": rng.randint(500, 100_000),
                        "order_count": rng.randint(10, 10_000),
                        "growth_rate": round(rng.uniform(-5, 60), 1),
                    },
                    "competition": {
                        "seller_count": rng.randint(3, 200),
                        "saturation": round(rng.uniform(0.1, 0.9), 2),
                        "avg_review_rating": round(rng.uniform(3.5, 4.9), 1),
                    },
                    "seo": {
                        "keyword_relevance": round(rng.uniform(0.3, 0.95), 2),
                        "search_position": rng.randint(1, 80),
                        "content_quality": round(rng.uniform(0.3, 0.9), 2),
                    },
                    "fundamentals": {
                        "price": price,
                        "margin_percent": round((1 - supplier_cost / price) * 100, 1),
                        "shipping_days": rng.randint(3, 30),
                        "weight_kg": round(rng.uniform(0.1, 3.0), 2),
                    },
                },
            })

    return candidates


def _build_analysis_prompt(product_data: dict, score: float) -> str:
    """
    Build the LLM prompt for structured product analysis.

    Args:
        product_data: Product data dict.
        score: Composite score from the scoring service.

    Returns:
        Formatted prompt string for the LLM Gateway.
    """
    title = product_data.get("product_title", "Unknown")
    price = product_data.get("price", "N/A")
    currency = product_data.get("currency", "USD")
    source = product_data.get("source", "unknown")
    raw_str = str(product_data.get("raw_data", {}))[:1500]

    return f"""Analyze this product for dropshipping potential.

Product: {title}
Price: {price} {currency}
Source: {source}
Score: {score}/100
Data: {raw_str}

Return a JSON object with these keys:
1. "summary": 2-3 sentence analysis
2. "opportunity_score": integer 0-100
3. "risk_factors": list of 3 risk strings
4. "recommended_price_range": {{"low": float, "high": float, "currency": str}}
5. "target_audience": one sentence
6. "marketing_angles": list of 3 strategy strings

Return ONLY valid JSON."""


def _parse_llm_analysis(llm_response: dict) -> dict:
    """
    Parse the LLM Gateway response into a structured analysis dict.

    Attempts to extract the content from the gateway response format
    and parse it as JSON.  Falls back to wrapping the response as-is
    if JSON parsing fails.

    Args:
        llm_response: Raw response dict from the LLM Gateway.

    Returns:
        Parsed analysis dict.
    """
    content = llm_response.get("content", "")

    # Try to parse as JSON
    try:
        if isinstance(content, str):
            # Strip markdown code fences if present
            cleaned = content.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            analysis = json.loads(cleaned)
            if isinstance(analysis, dict):
                return analysis
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: wrap raw content
    return {
        "summary": str(content)[:500] if content else "Analysis unavailable",
        "opportunity_score": 50,
        "risk_factors": ["Analysis parsing failed"],
        "recommended_price_range": {"low": 0, "high": 0, "currency": "USD"},
        "target_audience": "General consumers",
        "marketing_angles": ["Standard digital marketing"],
    }


# ─── Watchlist ───────────────────────────────────────────────────────

async def check_watchlist_limit(db: AsyncSession, user: User) -> bool:
    """
    Check whether the user has remaining watchlist capacity.

    Args:
        db: Async database session.
        user: The authenticated user.

    Returns:
        True if the user can add another item, False if limit reached.
    """
    plan_limits = PLAN_LIMITS[user.plan]
    if plan_limits.max_secondary == -1:
        return True  # Unlimited

    result = await db.execute(
        select(func.count(WatchlistItem.id)).where(
            WatchlistItem.user_id == user.id
        )
    )
    count = result.scalar_one()
    return count < plan_limits.max_secondary


async def get_watchlist_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    """
    Get the total number of watchlist items for a user.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Total count of watchlist items.
    """
    result = await db.execute(
        select(func.count(WatchlistItem.id)).where(
            WatchlistItem.user_id == user_id
        )
    )
    return result.scalar_one()


async def add_to_watchlist(
    db: AsyncSession,
    user: User,
    result_id: uuid.UUID,
    notes: str | None = None,
) -> WatchlistItem:
    """
    Add a research result to the user's watchlist.

    Checks plan limits and prevents duplicate entries for the same result.

    Args:
        db: Async database session.
        user: The authenticated user.
        result_id: UUID of the ResearchResult to save.
        notes: Optional notes.

    Returns:
        The newly created WatchlistItem.

    Raises:
        ValueError: If plan limit reached or result already in watchlist.
    """
    # Check plan limit
    can_add = await check_watchlist_limit(db, user)
    if not can_add:
        raise ValueError(
            f"Watchlist limit reached for {user.plan.value} plan. "
            f"Upgrade your plan for more watchlist items."
        )

    # Check for duplicate
    existing = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user.id,
            WatchlistItem.result_id == result_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("This result is already in your watchlist")

    # Verify result exists
    res = await db.execute(
        select(ResearchResult).where(ResearchResult.id == result_id)
    )
    if not res.scalar_one_or_none():
        raise ValueError("Research result not found")

    item = WatchlistItem(
        user_id=user.id,
        result_id=result_id,
        notes=notes,
        status="watching",
    )
    db.add(item)
    await db.flush()

    # Re-fetch with the result relationship eagerly loaded to prevent
    # MissingGreenlet during FastAPI response serialization.
    refreshed = await db.execute(
        select(WatchlistItem)
        .options(selectinload(WatchlistItem.result))
        .where(WatchlistItem.id == item.id)
    )
    return refreshed.scalar_one()


async def get_watchlist_items(
    db: AsyncSession,
    user_id: uuid.UUID,
    status: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[WatchlistItem], int]:
    """
    Get a paginated list of watchlist items for a user.

    Optionally filter by status (watching, imported, dismissed).

    Args:
        db: Async database session.
        user_id: The user's UUID.
        status: Optional status filter.
        page: Page number (1-indexed).
        per_page: Items per page.

    Returns:
        Tuple of (list of WatchlistItem, total count).
    """
    # Build base query
    base_filter = [WatchlistItem.user_id == user_id]
    if status:
        base_filter.append(WatchlistItem.status == status)

    # Count total
    count_result = await db.execute(
        select(func.count(WatchlistItem.id)).where(*base_filter)
    )
    total = count_result.scalar_one()

    # Fetch page with eagerly loaded result relationship
    offset = (page - 1) * per_page
    result = await db.execute(
        select(WatchlistItem)
        .options(selectinload(WatchlistItem.result))
        .where(*base_filter)
        .order_by(WatchlistItem.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    items = list(result.scalars().all())
    return items, total


async def update_watchlist_item(
    db: AsyncSession,
    item_id: uuid.UUID,
    user_id: uuid.UUID,
    status: str | None = None,
    notes: str | None = ...,
) -> WatchlistItem | None:
    """
    Update a watchlist item's status and/or notes.

    Uses the Ellipsis sentinel pattern: passing notes=... means "not provided"
    (leave unchanged), while notes=None explicitly clears the notes field.

    Args:
        db: Async database session.
        item_id: The watchlist item's UUID.
        user_id: The requesting user's UUID (for ownership check).
        status: New status value (optional).
        notes: New notes value (Ellipsis = unchanged, None = clear).

    Returns:
        The updated WatchlistItem, or None if not found/not owned.
    """
    result = await db.execute(
        select(WatchlistItem)
        .options(selectinload(WatchlistItem.result))
        .where(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == user_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        return None

    valid_statuses = {"watching", "imported", "dismissed"}
    if status and status in valid_statuses:
        item.status = status
    if notes is not ...:
        item.notes = notes

    await db.flush()
    # Refresh the entire object to load the server-updated `updated_at`
    # value and ensure all attributes (including the result relationship)
    # are accessible outside the async session context.
    await db.refresh(item)
    # Also eagerly load the result relationship for response serialization.
    refreshed = await db.execute(
        select(WatchlistItem)
        .options(selectinload(WatchlistItem.result))
        .where(WatchlistItem.id == item.id)
    )
    return refreshed.scalar_one()


async def delete_watchlist_item(
    db: AsyncSession,
    item_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """
    Remove an item from the user's watchlist.

    Args:
        db: Async database session.
        item_id: The watchlist item's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        True if deleted, False if not found or not owned.
    """
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == user_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        return False

    await db.delete(item)
    await db.flush()
    return True


# ─── Source Configs ──────────────────────────────────────────────────

async def create_source_config(
    db: AsyncSession,
    user_id: uuid.UUID,
    source_type: str,
    credentials: dict,
    settings: dict,
) -> SourceConfig:
    """
    Create a new source configuration for the user.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        source_type: External source identifier.
        credentials: Source-specific authentication credentials.
        settings: Source-specific settings.

    Returns:
        The newly created SourceConfig.
    """
    config = SourceConfig(
        user_id=user_id,
        source_type=source_type,
        credentials=credentials,
        settings=settings,
    )
    db.add(config)
    await db.flush()
    return config


async def get_source_configs(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[SourceConfig]:
    """
    Get all source configurations for a user.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        List of all SourceConfig records for the user.
    """
    result = await db.execute(
        select(SourceConfig)
        .where(SourceConfig.user_id == user_id)
        .order_by(SourceConfig.source_type)
    )
    return list(result.scalars().all())


async def update_source_config(
    db: AsyncSession,
    config_id: uuid.UUID,
    user_id: uuid.UUID,
    credentials: dict | None = None,
    settings: dict | None = None,
    is_active: bool | None = None,
) -> SourceConfig | None:
    """
    Update an existing source configuration.

    Args:
        db: Async database session.
        config_id: The config's UUID.
        user_id: The requesting user's UUID (for ownership check).
        credentials: Updated credentials (optional).
        settings: Updated settings (optional).
        is_active: Toggle active state (optional).

    Returns:
        The updated SourceConfig, or None if not found/not owned.
    """
    result = await db.execute(
        select(SourceConfig).where(
            SourceConfig.id == config_id,
            SourceConfig.user_id == user_id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        return None

    if credentials is not None:
        config.credentials = credentials
    if settings is not None:
        config.settings = settings
    if is_active is not None:
        config.is_active = is_active

    await db.flush()
    # Refresh to load the server-updated `updated_at` value, preventing
    # MissingGreenlet when the attribute is accessed during serialization.
    await db.refresh(config)
    return config


async def delete_source_config(
    db: AsyncSession,
    config_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """
    Delete a source configuration.

    Args:
        db: Async database session.
        config_id: The config's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        True if deleted, False if not found or not owned.
    """
    result = await db.execute(
        select(SourceConfig).where(
            SourceConfig.id == config_id,
            SourceConfig.user_id == user_id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        return False

    await db.delete(config)
    await db.flush()
    return True


# ─── Store Connections ──────────────────────────────────────────────


VALID_PLATFORMS = {"shopify", "woocommerce", "platform"}
"""
Valid store platform identifiers for StoreConnection.

For QA Engineers:
    Use these values when testing connection creation.  Other values
    should be rejected with HTTP 400.
"""


async def create_store_connection(
    db: AsyncSession,
    user_id: uuid.UUID,
    platform: str,
    store_url: str,
    api_key_encrypted: str,
    api_secret_encrypted: str | None = None,
) -> StoreConnection:
    """
    Create a new store connection for the user.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        platform: Store platform identifier ('shopify', 'woocommerce', 'platform').
        store_url: Base URL of the connected store.
        api_key_encrypted: Encrypted API key.
        api_secret_encrypted: Encrypted API secret (optional).

    Returns:
        The newly created StoreConnection.

    Raises:
        ValueError: If the platform is not valid.
    """
    if platform not in VALID_PLATFORMS:
        raise ValueError(
            f"Invalid platform. Valid platforms: {', '.join(sorted(VALID_PLATFORMS))}"
        )

    connection = StoreConnection(
        user_id=user_id,
        platform=platform,
        store_url=store_url,
        api_key_encrypted=api_key_encrypted,
        api_secret_encrypted=api_secret_encrypted,
    )
    db.add(connection)
    await db.flush()
    return connection


async def get_store_connections(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[StoreConnection]:
    """
    Get all store connections for a user.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        List of StoreConnection records ordered by platform name.
    """
    result = await db.execute(
        select(StoreConnection)
        .where(StoreConnection.user_id == user_id)
        .order_by(StoreConnection.platform)
    )
    return list(result.scalars().all())


async def get_store_connection(
    db: AsyncSession,
    connection_id: uuid.UUID,
    user_id: uuid.UUID,
) -> StoreConnection | None:
    """
    Get a single store connection by ID, scoped to the user.

    Args:
        db: Async database session.
        connection_id: The connection's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        The StoreConnection if found and owned by user, None otherwise.
    """
    result = await db.execute(
        select(StoreConnection).where(
            StoreConnection.id == connection_id,
            StoreConnection.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_store_connection(
    db: AsyncSession,
    connection_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """
    Delete a store connection.

    Args:
        db: Async database session.
        connection_id: The connection's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        True if deleted, False if not found or not owned.
    """
    connection = await get_store_connection(db, connection_id, user_id)
    if not connection:
        return False

    await db.delete(connection)
    await db.flush()
    return True


async def test_store_connection(
    db: AsyncSession,
    connection_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple[bool, str]:
    """
    Test connectivity to a store connection.

    Attempts a lightweight health check against the store's API.
    Currently returns a simulated success for supported platforms.

    For Developers:
        Replace the mock logic with real HTTP calls to each platform's
        health/ping endpoint once the store integrations are built.

    Args:
        db: Async database session.
        connection_id: The connection's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        Tuple of (success: bool, message: str).
    """
    connection = await get_store_connection(db, connection_id, user_id)
    if not connection:
        return False, "Connection not found"

    if not connection.is_active:
        return False, "Connection is disabled"

    # Simulate platform-specific connectivity test
    if connection.platform == "shopify":
        return True, f"Successfully connected to Shopify store at {connection.store_url}"
    elif connection.platform == "woocommerce":
        return True, f"Successfully connected to WooCommerce store at {connection.store_url}"
    elif connection.platform == "platform":
        return True, f"Successfully connected to platform store at {connection.store_url}"
    else:
        return False, f"Unsupported platform: {connection.platform}"


async def get_active_connections(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[StoreConnection]:
    """
    Get all active store connections for a user.

    For Developers:
        Used by the research service to find connected stores
        that can provide product data for keyword matching.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        List of active StoreConnection records.
    """
    result = await db.execute(
        select(StoreConnection).where(
            StoreConnection.user_id == user_id,
            StoreConnection.is_active == True,  # noqa: E712
        )
    )
    return list(result.scalars().all())
