"""
Celery tasks for executing product research pipelines.

The `run_research` task is the main entry point, dispatched by the
POST /api/v1/research/runs endpoint. It fetches mock product data from
each requested source, scores the results, optionally runs AI analysis,
and stores everything in the database.

For Developers:
    This task uses synchronous database access (via the sync database URL)
    because Celery workers run in a synchronous event loop. Each source
    has its own mock data generator that returns 5-10 realistic products.

    Real API integrations will replace the mock generators in future
    iterations. The task structure (fetch -> score -> analyze -> store)
    will remain the same.

For Project Managers:
    Research tasks run in the background via Celery workers. Each task
    processes one research run. Average execution time with mock data is
    under 2 seconds. With real APIs, expect 10-30 seconds per run
    depending on the number of sources.

For QA Engineers:
    Test that the task transitions the run status from 'pending' to
    'running' to 'completed'. Verify results_count matches the actual
    number of stored results. Test failure handling (status = 'failed'
    with error_message).

For End Users:
    Research runs execute in the background. You will see results appear
    on the run detail page once processing completes (usually within
    a few seconds).
"""

import hashlib
import logging
import random
import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models.research import ResearchResult, ResearchRun
from app.services.scoring_service import calculate_score
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Synchronous engine for Celery tasks
sync_engine = create_engine(settings.database_url_sync)
SyncSessionFactory = sessionmaker(bind=sync_engine)


# ─── Mock Data Generators ────────────────────────────────────────────

def _generate_aliexpress_products(keywords: list[str]) -> list[dict]:
    """
    Generate mock AliExpress product data for the given keywords.

    Produces 5-8 realistic product entries with prices, ratings,
    order counts, and engagement metrics.

    Args:
        keywords: List of search keywords.

    Returns:
        List of product data dicts with source-specific fields.
    """
    keyword_str = " ".join(keywords)
    seed = int(hashlib.md5(keyword_str.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    products = []
    templates = [
        "{kw} Premium Quality Version",
        "{kw} Budget Friendly Option",
        "{kw} Hot Selling 2024 Edition",
        "{kw} Upgraded Pro Model",
        "{kw} Wholesale Bundle Pack",
        "{kw} Lightweight Portable Design",
        "{kw} Multi-Function Deluxe Set",
        "{kw} Eco-Friendly Sustainable Choice",
    ]

    count = rng.randint(5, 8)
    for i in range(count):
        template = templates[i % len(templates)]
        title = template.format(kw=keywords[0].title() if keywords else "Product")
        price = round(rng.uniform(3.99, 89.99), 2)
        orders = rng.randint(10, 15000)
        rating = round(rng.uniform(3.5, 5.0), 1)

        products.append({
            "product_title": title,
            "product_url": f"https://aliexpress.com/item/{rng.randint(1000000, 9999999)}.html",
            "image_url": f"https://ae-pic-a1.aliexpress-media.com/kf/{uuid.uuid4().hex[:16]}.jpg",
            "price": price,
            "currency": "USD",
            "raw_data": {
                "social": {
                    "likes": rng.randint(50, 8000),
                    "shares": rng.randint(10, 2000),
                    "views": rng.randint(500, 500000),
                    "comments": rng.randint(5, 1000),
                    "trending": rng.random() > 0.6,
                },
                "market": {
                    "search_volume": rng.randint(500, 80000),
                    "order_count": orders,
                    "growth_rate": round(rng.uniform(-5, 60), 1),
                },
                "competition": {
                    "seller_count": rng.randint(3, 300),
                    "saturation": round(rng.uniform(0.1, 0.9), 2),
                    "avg_review_rating": rating,
                },
                "seo": {
                    "keyword_relevance": round(rng.uniform(0.3, 0.95), 2),
                    "search_position": rng.randint(1, 80),
                    "content_quality": round(rng.uniform(0.3, 0.9), 2),
                },
                "fundamentals": {
                    "price": price,
                    "margin_percent": rng.randint(15, 70),
                    "shipping_days": rng.randint(5, 35),
                    "weight_kg": round(rng.uniform(0.1, 5.0), 2),
                },
            },
        })
    return products


def _generate_tiktok_products(keywords: list[str]) -> list[dict]:
    """
    Generate mock TikTok trending product data for the given keywords.

    Produces 5-7 products with high social engagement metrics
    reflecting TikTok's viral discovery nature.

    Args:
        keywords: List of search keywords.

    Returns:
        List of product data dicts with TikTok-specific metrics.
    """
    keyword_str = " ".join(keywords) + "_tiktok"
    seed = int(hashlib.md5(keyword_str.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    products = []
    templates = [
        "Viral {kw} - TikTok Made Me Buy It",
        "{kw} As Seen on TikTok",
        "Trending {kw} That Broke the Internet",
        "The {kw} Everyone Is Talking About",
        "Satisfying {kw} ASMR Favorite",
        "Game-Changing {kw} Discovery",
        "{kw} Life Hack Essential",
    ]

    count = rng.randint(5, 7)
    for i in range(count):
        template = templates[i % len(templates)]
        title = template.format(kw=keywords[0].title() if keywords else "Product")
        price = round(rng.uniform(9.99, 59.99), 2)

        products.append({
            "product_title": title,
            "product_url": f"https://tiktok.com/discover/{keywords[0].replace(' ', '-')}-{rng.randint(1000, 9999)}",
            "image_url": f"https://p16-sign.tiktokcdn-us.com/{uuid.uuid4().hex[:16]}.jpeg",
            "price": price,
            "currency": "USD",
            "raw_data": {
                "social": {
                    "likes": rng.randint(5000, 500000),
                    "shares": rng.randint(1000, 100000),
                    "views": rng.randint(100000, 10000000),
                    "comments": rng.randint(500, 50000),
                    "trending": rng.random() > 0.3,
                },
                "market": {
                    "search_volume": rng.randint(5000, 200000),
                    "order_count": rng.randint(100, 20000),
                    "growth_rate": round(rng.uniform(10, 80), 1),
                },
                "competition": {
                    "seller_count": rng.randint(5, 150),
                    "saturation": round(rng.uniform(0.2, 0.7), 2),
                    "avg_review_rating": round(rng.uniform(3.8, 4.8), 1),
                },
                "seo": {
                    "keyword_relevance": round(rng.uniform(0.5, 0.98), 2),
                    "search_position": rng.randint(1, 30),
                    "content_quality": round(rng.uniform(0.5, 0.95), 2),
                },
                "fundamentals": {
                    "price": price,
                    "margin_percent": rng.randint(30, 75),
                    "shipping_days": rng.randint(3, 20),
                    "weight_kg": round(rng.uniform(0.05, 2.0), 2),
                },
            },
        })
    return products


def _generate_google_trends_products(keywords: list[str]) -> list[dict]:
    """
    Generate mock Google Trends product data for the given keywords.

    Produces 5-7 products reflecting search trend data with
    strong SEO and market signals.

    Args:
        keywords: List of search keywords.

    Returns:
        List of product data dicts with Google Trends-specific metrics.
    """
    keyword_str = " ".join(keywords) + "_gtrends"
    seed = int(hashlib.md5(keyword_str.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    products = []
    templates = [
        "Top Trending: {kw}",
        "{kw} - Rising Search Interest",
        "Breakout Product: {kw}",
        "{kw} High-Demand Market Entry",
        "Search Surge: {kw}",
        "{kw} Emerging Niche Opportunity",
        "Fast-Growing {kw} Category",
    ]

    count = rng.randint(5, 7)
    for i in range(count):
        template = templates[i % len(templates)]
        title = template.format(kw=keywords[0].title() if keywords else "Product")
        price = round(rng.uniform(12.99, 149.99), 2)

        products.append({
            "product_title": title,
            "product_url": f"https://trends.google.com/trends/explore?q={keywords[0].replace(' ', '+')}",
            "image_url": None,
            "price": price,
            "currency": "USD",
            "raw_data": {
                "social": {
                    "likes": rng.randint(100, 5000),
                    "shares": rng.randint(50, 3000),
                    "views": rng.randint(10000, 1000000),
                    "comments": rng.randint(20, 2000),
                    "trending": rng.random() > 0.4,
                },
                "market": {
                    "search_volume": rng.randint(10000, 500000),
                    "order_count": rng.randint(500, 10000),
                    "growth_rate": round(rng.uniform(5, 45), 1),
                },
                "competition": {
                    "seller_count": rng.randint(10, 200),
                    "saturation": round(rng.uniform(0.15, 0.8), 2),
                    "avg_review_rating": round(rng.uniform(3.5, 4.7), 1),
                },
                "seo": {
                    "keyword_relevance": round(rng.uniform(0.6, 0.99), 2),
                    "search_position": rng.randint(1, 50),
                    "content_quality": round(rng.uniform(0.4, 0.95), 2),
                },
                "fundamentals": {
                    "price": price,
                    "margin_percent": rng.randint(20, 65),
                    "shipping_days": rng.randint(7, 28),
                    "weight_kg": round(rng.uniform(0.2, 4.0), 2),
                },
            },
        })
    return products


def _generate_reddit_products(keywords: list[str]) -> list[dict]:
    """
    Generate mock Reddit product discussion data for the given keywords.

    Produces 5-7 products discovered from Reddit discussions with
    community engagement metrics.

    Args:
        keywords: List of search keywords.

    Returns:
        List of product data dicts with Reddit-specific metrics.
    """
    keyword_str = " ".join(keywords) + "_reddit"
    seed = int(hashlib.md5(keyword_str.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    products = []
    templates = [
        "[r/BuyItForLife] Best {kw} I've Found",
        "[r/Dropshipping] High-Margin {kw} Opportunity",
        "[r/EntrepreneurRideAlong] {kw} Niche Report",
        "[r/AmazonSeller] {kw} Trending Pick",
        "[r/Ecommerce] Underrated {kw} Product",
        "[r/SideHustle] {kw} Winning Product Alert",
        "[r/ProductResearch] {kw} Deep Dive",
    ]

    count = rng.randint(5, 7)
    for i in range(count):
        template = templates[i % len(templates)]
        title = template.format(kw=keywords[0].title() if keywords else "Product")
        price = round(rng.uniform(7.99, 79.99), 2)

        products.append({
            "product_title": title,
            "product_url": f"https://reddit.com/r/dropshipping/comments/{uuid.uuid4().hex[:6]}",
            "image_url": None,
            "price": price,
            "currency": "USD",
            "raw_data": {
                "social": {
                    "likes": rng.randint(200, 15000),
                    "shares": rng.randint(50, 5000),
                    "views": rng.randint(5000, 500000),
                    "comments": rng.randint(100, 5000),
                    "trending": rng.random() > 0.5,
                },
                "market": {
                    "search_volume": rng.randint(2000, 100000),
                    "order_count": rng.randint(200, 8000),
                    "growth_rate": round(rng.uniform(0, 35), 1),
                },
                "competition": {
                    "seller_count": rng.randint(5, 250),
                    "saturation": round(rng.uniform(0.1, 0.85), 2),
                    "avg_review_rating": round(rng.uniform(3.2, 4.9), 1),
                },
                "seo": {
                    "keyword_relevance": round(rng.uniform(0.4, 0.9), 2),
                    "search_position": rng.randint(5, 70),
                    "content_quality": round(rng.uniform(0.3, 0.85), 2),
                },
                "fundamentals": {
                    "price": price,
                    "margin_percent": rng.randint(20, 60),
                    "shipping_days": rng.randint(5, 25),
                    "weight_kg": round(rng.uniform(0.1, 3.5), 2),
                },
            },
        })
    return products


# Map source names to their mock generators
SOURCE_GENERATORS = {
    "aliexpress": _generate_aliexpress_products,
    "tiktok": _generate_tiktok_products,
    "google_trends": _generate_google_trends_products,
    "reddit": _generate_reddit_products,
}


@celery_app.task(name="app.tasks.research_tasks.run_research", bind=True, max_retries=2)
def run_research(self, run_id: str) -> dict:
    """
    Execute a research run: fetch data from each source, score, analyze, and store.

    This is the main background task dispatched when a user creates a research run.
    It transitions the run through: pending -> running -> completed (or failed).

    Steps:
        1. Mark run as 'running'.
        2. For each requested source, generate mock product data.
        3. Score each product using the scoring service.
        4. Generate AI analysis for each product.
        5. Store all results in the database.
        6. Update run status to 'completed' with results_count.

    Args:
        self: Celery task instance (for retry support).
        run_id: UUID string of the ResearchRun to execute.

    Returns:
        Dict with run_id, status, and results_count.
    """
    logger.info(f"Starting research run: {run_id}")

    session = SyncSessionFactory()
    try:
        # Load the run
        run = session.query(ResearchRun).filter(
            ResearchRun.id == uuid.UUID(run_id)
        ).first()

        if not run:
            logger.error(f"Research run not found: {run_id}")
            return {"error": "Run not found"}

        # Mark as running
        run.status = "running"
        session.commit()

        all_results = []

        # Fetch products from each source
        for source_name in run.sources:
            generator = SOURCE_GENERATORS.get(source_name)
            if not generator:
                logger.warning(f"Unknown source: {source_name}, skipping")
                continue

            try:
                products = generator(run.keywords)
                for product_data in products:
                    # Score the product
                    score = calculate_score(
                        product_data.get("raw_data", {}),
                        run.score_config,
                    )

                    # Generate AI analysis (synchronous mock version)
                    ai_analysis = _generate_sync_mock_analysis(
                        product_data, score, source_name
                    )

                    # Create result record
                    result = ResearchResult(
                        run_id=run.id,
                        source=source_name,
                        product_title=product_data["product_title"],
                        product_url=product_data["product_url"],
                        image_url=product_data.get("image_url"),
                        price=product_data.get("price"),
                        currency=product_data.get("currency", "USD"),
                        score=score,
                        ai_analysis=ai_analysis,
                        raw_data=product_data.get("raw_data", {}),
                    )
                    session.add(result)
                    all_results.append(result)

            except Exception as e:
                logger.error(f"Error fetching from {source_name}: {e}")
                continue

        # Update run status
        run.status = "completed"
        run.results_count = len(all_results)
        run.completed_at = datetime.now(UTC)
        session.commit()

        logger.info(
            f"Research run {run_id} completed with {len(all_results)} results"
        )
        return {
            "run_id": run_id,
            "status": "completed",
            "results_count": len(all_results),
        }

    except Exception as e:
        session.rollback()
        logger.error(f"Research run {run_id} failed: {e}")

        # Try to mark as failed
        try:
            run = session.query(ResearchRun).filter(
                ResearchRun.id == uuid.UUID(run_id)
            ).first()
            if run:
                run.status = "failed"
                run.error_message = str(e)[:1000]
                run.completed_at = datetime.now(UTC)
                session.commit()
        except Exception:
            session.rollback()

        return {"run_id": run_id, "status": "failed", "error": str(e)}

    finally:
        session.close()


def _generate_sync_mock_analysis(
    product_data: dict,
    score: float,
    source: str,
) -> dict:
    """
    Generate synchronous mock AI analysis for use in Celery tasks.

    This is a simplified version of the async ai_analysis_service for
    use in the synchronous Celery worker context.

    Args:
        product_data: Product data dict.
        score: Composite score from the scoring service.
        source: Data source identifier.

    Returns:
        Analysis dict with summary, opportunity, risks, pricing,
        audience, and marketing angles.
    """
    title = product_data.get("product_title", "Unknown Product")
    price = product_data.get("price", 19.99)

    # Use title hash for deterministic variety
    title_hash = int(hashlib.md5(title.encode()).hexdigest()[:8], 16)
    variety = title_hash % 5

    opportunity = min(100, max(10, int(score * 0.9 + (variety * 4))))
    low_price = round(max(price * 1.5, price + 5), 2)
    high_price = round(max(price * 3.0, price + 20), 2)

    risk_pools = [
        ["High shipping times from overseas", "Quality control issues", "Seasonal demand swings"],
        ["Intense competition from established sellers", "Thin margins need high volume", "Customer expectations gap"],
        ["Regulatory compliance may be needed", "Supply chain disruptions possible", "Price wars erode margins"],
        ["Trend may be short-lived (fad risk)", "Significant ad spend required", "High returns rate for category"],
        ["IP concerns with generic products", "Logistics complexity for fragile items", "Currency fluctuations impact costs"],
    ]

    marketing_pools = [
        ["TikTok short-form video campaigns", "Comparison content vs premium brands", "Urgency-driven ad creative"],
        ["Lifestyle imagery and aspirational messaging", "Micro-influencer partnerships", "Retargeting for abandoned carts"],
        ["Highlight unique differentiating features", "Product bundling for higher AOV", "Seasonal gift guide placement"],
        ["Problem-solution messaging approach", "Unboxing and review content", "Geographic targeting low-comp markets"],
        ["User-generated content strategy", "Position as affordable premium", "Email marketing for retention"],
    ]

    audiences = [
        "Budget-conscious millennials aged 25-34",
        "Gen Z consumers aged 18-24 on social media",
        "Online shoppers aged 30-45 seeking value",
        "Tech-savvy consumers aged 22-38",
        "Gift shoppers aged 28-50",
    ]

    strength = "strong" if score >= 70 else "moderate" if score >= 40 else "limited"

    return {
        "summary": (
            f"'{title}' from {source} shows {strength} market potential "
            f"with a score of {score:.0f}/100. "
            f"{'Strong social signals and growing demand make this a promising pick.' if score >= 60 else 'Further validation recommended before investing heavily.'}"
        ),
        "opportunity_score": opportunity,
        "risk_factors": risk_pools[variety],
        "recommended_price_range": {
            "low": low_price,
            "high": high_price,
            "currency": product_data.get("currency", "USD"),
        },
        "target_audience": audiences[variety],
        "marketing_angles": marketing_pools[variety],
    }
