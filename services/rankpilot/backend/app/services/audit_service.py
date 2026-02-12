"""
SEO audit service for the RankPilot engine.

Provides site auditing functionality that analyzes a site against
SEO best practices and generates a health score with categorized
issues and actionable recommendations.

For Developers:
    The `run_audit` function generates mock audit data. In production,
    it would crawl the site, analyze page structure, check meta tags,
    evaluate performance, and assess technical SEO factors.
    Issues are categorized by severity (critical, warning, info) and
    category (meta_tags, performance, content, technical, mobile).

For QA Engineers:
    Test audit creation and listing. Verify score is 0-100, issues
    have required fields (severity, category, message), and pagination works.

For Project Managers:
    SEO audits provide ongoing value and engagement. Users return
    regularly to check their score improvements.

For End Users:
    Run audits to get a health score and specific recommendations
    for improving your website's search engine rankings.
"""

import random
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.seo_audit import SeoAudit
from app.models.site import Site


# Mock issue templates for realistic audit results
_ISSUE_TEMPLATES = [
    {
        "severity": "critical",
        "category": "meta_tags",
        "message": "Missing meta description on 3 pages",
        "page_url": "/products",
    },
    {
        "severity": "critical",
        "category": "performance",
        "message": "Page load time exceeds 5 seconds on mobile",
        "page_url": "/",
    },
    {
        "severity": "critical",
        "category": "technical",
        "message": "Multiple H1 tags found on homepage",
        "page_url": "/",
    },
    {
        "severity": "warning",
        "category": "content",
        "message": "Thin content detected: page has less than 300 words",
        "page_url": "/about",
    },
    {
        "severity": "warning",
        "category": "meta_tags",
        "message": "Title tag too long (>60 characters) on blog pages",
        "page_url": "/blog",
    },
    {
        "severity": "warning",
        "category": "technical",
        "message": "Missing alt text on 12 images",
        "page_url": "/gallery",
    },
    {
        "severity": "warning",
        "category": "mobile",
        "message": "Viewport not configured for mobile responsiveness",
        "page_url": "/contact",
    },
    {
        "severity": "warning",
        "category": "performance",
        "message": "Uncompressed images adding 2.3MB to page weight",
        "page_url": "/products",
    },
    {
        "severity": "info",
        "category": "content",
        "message": "Consider adding FAQ schema markup to Q&A pages",
        "page_url": "/faq",
    },
    {
        "severity": "info",
        "category": "technical",
        "message": "XML sitemap found but last modified 90+ days ago",
        "page_url": "/sitemap.xml",
    },
    {
        "severity": "info",
        "category": "meta_tags",
        "message": "Open Graph tags missing on product pages",
        "page_url": "/products",
    },
    {
        "severity": "info",
        "category": "performance",
        "message": "Browser caching not configured for static assets",
        "page_url": "/",
    },
]

_RECOMMENDATION_TEMPLATES = [
    "Add unique meta descriptions to all pages (aim for 150-160 characters).",
    "Optimize images using WebP format and lazy loading for faster page loads.",
    "Implement structured data (JSON-LD) for products, articles, and FAQs.",
    "Ensure all pages have exactly one H1 tag that includes the primary keyword.",
    "Add alt text to all images describing their content for accessibility and SEO.",
    "Configure browser caching headers for static assets (CSS, JS, images).",
    "Create an XML sitemap and submit it to Google Search Console.",
    "Implement HTTPS across all pages for security and SEO ranking signals.",
    "Improve Core Web Vitals: optimize LCP, FID, and CLS metrics.",
    "Add internal links between related content pages to improve crawlability.",
    "Ensure mobile-responsive design with proper viewport meta tag.",
    "Reduce server response time to under 200ms with caching and CDN.",
]


async def run_audit(
    db: AsyncSession,
    site: Site,
) -> SeoAudit:
    """
    Run an SEO audit on a site (mock implementation).

    In production, this would crawl the site's pages, analyze HTML structure,
    check meta tags, evaluate performance metrics, and test mobile compatibility.
    The mock generates realistic-looking audit data.

    Args:
        db: Async database session.
        site: The Site to audit.

    Returns:
        The newly created SeoAudit with score, issues, and recommendations.
    """
    # Generate random but realistic audit data
    num_issues = random.randint(3, 8)
    issues = random.sample(_ISSUE_TEMPLATES, min(num_issues, len(_ISSUE_TEMPLATES)))

    num_recommendations = random.randint(3, 6)
    recommendations = random.sample(
        _RECOMMENDATION_TEMPLATES,
        min(num_recommendations, len(_RECOMMENDATION_TEMPLATES)),
    )

    # Calculate score based on issues (more critical issues = lower score)
    critical_count = sum(1 for i in issues if i["severity"] == "critical")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")
    base_score = 100.0
    base_score -= critical_count * 15
    base_score -= warning_count * 5
    overall_score = max(0.0, min(100.0, base_score + random.uniform(-5, 5)))
    overall_score = round(overall_score, 1)

    pages_crawled = random.randint(5, 50)

    audit = SeoAudit(
        site_id=site.id,
        overall_score=overall_score,
        issues=issues,
        recommendations=recommendations,
        pages_crawled=pages_crawled,
    )
    db.add(audit)

    # Update site's last_crawled timestamp
    site.last_crawled = datetime.now(UTC)
    await db.flush()

    return audit


async def get_audit(
    db: AsyncSession,
    audit_id: uuid.UUID,
) -> SeoAudit | None:
    """
    Get a single SEO audit by ID.

    Args:
        db: Async database session.
        audit_id: The audit's UUID.

    Returns:
        The SeoAudit if found, None otherwise.
    """
    result = await db.execute(
        select(SeoAudit).where(SeoAudit.id == audit_id)
    )
    return result.scalar_one_or_none()


async def list_audits(
    db: AsyncSession,
    site_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[SeoAudit], int]:
    """
    List SEO audits for a site with pagination.

    Args:
        db: Async database session.
        site_id: The site's UUID.
        page: Page number (1-indexed).
        per_page: Items per page.

    Returns:
        Tuple of (list of SeoAudits, total count).
    """
    count_result = await db.execute(
        select(func.count())
        .select_from(SeoAudit)
        .where(SeoAudit.site_id == site_id)
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * per_page
    result = await db.execute(
        select(SeoAudit)
        .where(SeoAudit.site_id == site_id)
        .order_by(SeoAudit.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    audits = list(result.scalars().all())
    return audits, total
