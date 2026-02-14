"""
SEO audit service for the RankPilot engine.

Provides site auditing functionality that analyzes a site against
SEO best practices and generates a health score with categorized
issues and actionable recommendations. Includes real page analysis
via ``analyze_page()`` that fetches and parses HTML content.

For Developers:
    ``analyze_page(url)`` performs real HTTP fetching and HTML parsing
    to extract SEO-relevant data (title, meta, headings, links, images).
    ``run_audit()`` still uses mock data for the full site audit (as it
    would require a crawling infrastructure). Use ``analyze_page()`` for
    single-page analysis in the audit detail view.
    Issues are categorized by severity (critical, warning, info) and
    category (meta_tags, performance, content, technical, mobile).

For QA Engineers:
    Test ``analyze_page()`` with mock HTTP responses to verify parsing.
    Test audit creation and listing. Verify score is 0-100, issues
    have required fields (severity, category, message), and pagination works.

For Project Managers:
    SEO audits provide ongoing value and engagement. Users return
    regularly to check their score improvements. The single-page
    analysis adds concrete, actionable data per URL.

For End Users:
    Run audits to get a health score and specific recommendations
    for improving your website's search engine rankings. Analyze
    individual pages for detailed SEO insights.
"""

import re
import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.seo_audit import SeoAudit
from app.models.site import Site


# ── Page Analysis (Real Implementation) ─────────────────────────────────


@dataclass
class PageAnalysis:
    """
    Result of analyzing a single web page for SEO factors.

    Attributes:
        url: The analyzed page URL.
        title: Content of the <title> tag (empty if missing).
        meta_description: Content of the <meta name='description'> tag.
        h1_tags: List of H1 heading texts found on the page.
        h2_tags: List of H2 heading texts found on the page.
        h3_tags: List of H3 heading texts found on the page.
        image_alt_texts: List of alt texts from <img> tags.
        images_without_alt: Count of images missing alt attributes.
        internal_links: List of internal link URLs (same domain).
        external_links: List of external link URLs (different domain).
        word_count: Approximate number of words in the page body text.
        canonical_url: Content of <link rel='canonical'> (if present).
        og_tags: Dict of Open Graph meta tags found (property -> content).
        meta_score: Score for meta tag quality (0-100).
        content_score: Score for content quality (0-100).
        technical_score: Score for technical SEO factors (0-100).
        mobile_score: Score for mobile-friendliness (0-100).
        performance_score: Score for performance factors (0-100).
        overall_score: Weighted average of all category scores (0-100).
        issues: List of issue dicts with severity, category, and message.
    """

    url: str = ""
    title: str = ""
    meta_description: str = ""
    h1_tags: list[str] = field(default_factory=list)
    h2_tags: list[str] = field(default_factory=list)
    h3_tags: list[str] = field(default_factory=list)
    image_alt_texts: list[str] = field(default_factory=list)
    images_without_alt: int = 0
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    word_count: int = 0
    canonical_url: str = ""
    og_tags: dict[str, str] = field(default_factory=dict)
    meta_score: int = 0
    content_score: int = 0
    technical_score: int = 0
    mobile_score: int = 0
    performance_score: int = 0
    overall_score: int = 0
    issues: list[dict] = field(default_factory=list)


class _SEOHTMLParser(HTMLParser):
    """
    Custom HTML parser that extracts SEO-relevant elements from a page.

    Collects title tag, meta tags, headings (h1-h3), image alt texts,
    links (href), canonical URL, and Open Graph tags. Tracks body text
    content for word count calculation.

    For Developers:
        Inherits from html.parser.HTMLParser (stdlib). Does not require
        any external dependencies like BeautifulSoup or lxml.
    """

    def __init__(self, base_domain: str = ""):
        """
        Initialize the SEO HTML parser.

        Args:
            base_domain: The domain of the page being parsed, used to
                         classify links as internal vs external.
        """
        super().__init__()
        self.base_domain = base_domain
        self.title = ""
        self.meta_description = ""
        self.h1_tags: list[str] = []
        self.h2_tags: list[str] = []
        self.h3_tags: list[str] = []
        self.image_alt_texts: list[str] = []
        self.images_without_alt: int = 0
        self.internal_links: list[str] = []
        self.external_links: list[str] = []
        self.canonical_url: str = ""
        self.og_tags: dict[str, str] = {}
        self.has_viewport: bool = False
        self.body_text_parts: list[str] = []

        # Parser state tracking
        self._in_title: bool = False
        self._in_h1: bool = False
        self._in_h2: bool = False
        self._in_h3: bool = False
        self._in_body: bool = False
        self._in_script: bool = False
        self._in_style: bool = False
        self._current_heading_text: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Process opening HTML tags to extract SEO data."""
        attrs_dict = {k: v for k, v in attrs if v is not None}
        tag_lower = tag.lower()

        if tag_lower == "title":
            self._in_title = True
        elif tag_lower == "body":
            self._in_body = True
        elif tag_lower == "script":
            self._in_script = True
        elif tag_lower == "style":
            self._in_style = True
        elif tag_lower == "meta":
            name = attrs_dict.get("name", "").lower()
            prop = attrs_dict.get("property", "").lower()
            content = attrs_dict.get("content", "")

            if name == "description":
                self.meta_description = content
            elif name == "viewport":
                self.has_viewport = True
            elif prop.startswith("og:"):
                self.og_tags[prop] = content
        elif tag_lower == "link":
            rel = attrs_dict.get("rel", "").lower()
            href = attrs_dict.get("href", "")
            if rel == "canonical" and href:
                self.canonical_url = href
        elif tag_lower == "h1":
            self._in_h1 = True
            self._current_heading_text = ""
        elif tag_lower == "h2":
            self._in_h2 = True
            self._current_heading_text = ""
        elif tag_lower == "h3":
            self._in_h3 = True
            self._current_heading_text = ""
        elif tag_lower == "img":
            alt = attrs_dict.get("alt")
            if alt is not None and alt.strip():
                self.image_alt_texts.append(alt.strip())
            else:
                self.images_without_alt += 1
        elif tag_lower == "a":
            href = attrs_dict.get("href", "")
            if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                if self._is_internal_link(href):
                    self.internal_links.append(href)
                else:
                    self.external_links.append(href)

    def handle_endtag(self, tag: str) -> None:
        """Process closing HTML tags and finalize collected data."""
        tag_lower = tag.lower()

        if tag_lower == "title":
            self._in_title = False
        elif tag_lower == "body":
            self._in_body = False
        elif tag_lower == "script":
            self._in_script = False
        elif tag_lower == "style":
            self._in_style = False
        elif tag_lower == "h1":
            self._in_h1 = False
            if self._current_heading_text.strip():
                self.h1_tags.append(self._current_heading_text.strip())
        elif tag_lower == "h2":
            self._in_h2 = False
            if self._current_heading_text.strip():
                self.h2_tags.append(self._current_heading_text.strip())
        elif tag_lower == "h3":
            self._in_h3 = False
            if self._current_heading_text.strip():
                self.h3_tags.append(self._current_heading_text.strip())

    def handle_data(self, data: str) -> None:
        """Process text content within HTML elements."""
        if self._in_title:
            self.title += data
        if self._in_h1 or self._in_h2 or self._in_h3:
            self._current_heading_text += data
        if self._in_body and not self._in_script and not self._in_style:
            stripped = data.strip()
            if stripped:
                self.body_text_parts.append(stripped)

    def _is_internal_link(self, href: str) -> bool:
        """
        Determine if a link is internal (same domain) or external.

        Args:
            href: The href attribute value from an anchor tag.

        Returns:
            True if the link points to the same domain, False otherwise.
        """
        if href.startswith("/"):
            return True
        if self.base_domain and self.base_domain in href:
            return True
        if not href.startswith("http"):
            return True
        return False

    def get_word_count(self) -> int:
        """
        Calculate the approximate word count from collected body text.

        Returns:
            Number of words found in the page body.
        """
        full_text = " ".join(self.body_text_parts)
        words = full_text.split()
        return len(words)


def _extract_domain(url: str) -> str:
    """
    Extract the domain from a URL string.

    Args:
        url: A full URL (e.g., 'https://example.com/path').

    Returns:
        The domain portion (e.g., 'example.com').
    """
    # Remove protocol
    domain = re.sub(r"^https?://", "", url)
    # Remove path
    domain = domain.split("/")[0]
    # Remove port
    domain = domain.split(":")[0]
    return domain


def _score_meta(parser: _SEOHTMLParser) -> tuple[int, list[dict]]:
    """
    Score the page's meta tag quality (0-100).

    Evaluates: title tag presence and length, meta description presence
    and length, Open Graph tags, and canonical URL.

    Args:
        parser: The populated HTML parser instance.

    Returns:
        Tuple of (score, list of issue dicts).
    """
    score = 100
    issues: list[dict] = []

    # Title tag checks
    if not parser.title.strip():
        score -= 25
        issues.append({
            "severity": "critical",
            "category": "meta_tags",
            "message": "Missing <title> tag",
        })
    elif len(parser.title.strip()) > 60:
        score -= 10
        issues.append({
            "severity": "warning",
            "category": "meta_tags",
            "message": f"Title tag too long ({len(parser.title.strip())} chars, recommended max 60)",
        })
    elif len(parser.title.strip()) < 10:
        score -= 10
        issues.append({
            "severity": "warning",
            "category": "meta_tags",
            "message": f"Title tag too short ({len(parser.title.strip())} chars, recommended 10-60)",
        })

    # Meta description checks
    if not parser.meta_description:
        score -= 20
        issues.append({
            "severity": "critical",
            "category": "meta_tags",
            "message": "Missing meta description",
        })
    elif len(parser.meta_description) > 160:
        score -= 5
        issues.append({
            "severity": "warning",
            "category": "meta_tags",
            "message": f"Meta description too long ({len(parser.meta_description)} chars, recommended max 160)",
        })
    elif len(parser.meta_description) < 50:
        score -= 5
        issues.append({
            "severity": "warning",
            "category": "meta_tags",
            "message": f"Meta description too short ({len(parser.meta_description)} chars, recommended 50-160)",
        })

    # Open Graph checks
    if not parser.og_tags:
        score -= 10
        issues.append({
            "severity": "info",
            "category": "meta_tags",
            "message": "No Open Graph tags found — social sharing will use defaults",
        })

    # Canonical URL check
    if not parser.canonical_url:
        score -= 5
        issues.append({
            "severity": "info",
            "category": "meta_tags",
            "message": "No canonical URL specified",
        })

    return max(0, score), issues


def _score_content(parser: _SEOHTMLParser) -> tuple[int, list[dict]]:
    """
    Score the page's content quality (0-100).

    Evaluates: heading structure, word count, and heading hierarchy.

    Args:
        parser: The populated HTML parser instance.

    Returns:
        Tuple of (score, list of issue dicts).
    """
    score = 100
    issues: list[dict] = []
    word_count = parser.get_word_count()

    # H1 tag checks
    if len(parser.h1_tags) == 0:
        score -= 25
        issues.append({
            "severity": "critical",
            "category": "content",
            "message": "Missing H1 heading tag",
        })
    elif len(parser.h1_tags) > 1:
        score -= 15
        issues.append({
            "severity": "warning",
            "category": "content",
            "message": f"Multiple H1 tags found ({len(parser.h1_tags)}) — use exactly one per page",
        })

    # Word count check (check more severe condition first)
    if word_count < 100:
        score -= 30
        issues.append({
            "severity": "critical",
            "category": "content",
            "message": f"Very thin content ({word_count} words) — search engines may not index this page",
        })
    elif word_count < 300:
        score -= 20
        issues.append({
            "severity": "warning",
            "category": "content",
            "message": f"Thin content detected ({word_count} words) — aim for 300+ words",
        })

    # Heading hierarchy check
    if parser.h1_tags and not parser.h2_tags:
        score -= 10
        issues.append({
            "severity": "info",
            "category": "content",
            "message": "No H2 subheadings found — consider adding for better structure",
        })

    return max(0, score), issues


def _score_technical(parser: _SEOHTMLParser) -> tuple[int, list[dict]]:
    """
    Score the page's technical SEO factors (0-100).

    Evaluates: image alt texts, canonical URL, link structure.

    Args:
        parser: The populated HTML parser instance.

    Returns:
        Tuple of (score, list of issue dicts).
    """
    score = 100
    issues: list[dict] = []

    # Image alt text checks
    if parser.images_without_alt > 0:
        penalty = min(25, parser.images_without_alt * 5)
        score -= penalty
        issues.append({
            "severity": "warning",
            "category": "technical",
            "message": f"{parser.images_without_alt} image(s) missing alt text",
        })

    # Internal links check
    if len(parser.internal_links) == 0:
        score -= 10
        issues.append({
            "severity": "info",
            "category": "technical",
            "message": "No internal links found — add navigation links for better crawlability",
        })

    return max(0, score), issues


def _score_mobile(parser: _SEOHTMLParser) -> tuple[int, list[dict]]:
    """
    Score the page's mobile-friendliness (0-100).

    Evaluates: viewport meta tag presence.

    Args:
        parser: The populated HTML parser instance.

    Returns:
        Tuple of (score, list of issue dicts).
    """
    score = 100
    issues: list[dict] = []

    if not parser.has_viewport:
        score -= 30
        issues.append({
            "severity": "critical",
            "category": "mobile",
            "message": "Missing viewport meta tag — page may not render correctly on mobile",
        })

    return max(0, score), issues


def analyze_page_html(html: str, url: str = "") -> PageAnalysis:
    """
    Analyze raw HTML content for SEO factors.

    Parses the HTML, extracts SEO-relevant elements, scores each category,
    and generates an actionable issue list. This is the pure function that
    does not perform any HTTP requests.

    Args:
        html: The raw HTML content to analyze.
        url: The page URL (used for domain extraction and link classification).

    Returns:
        A PageAnalysis dataclass with all extracted data, scores, and issues.
    """
    domain = _extract_domain(url) if url else ""
    parser = _SEOHTMLParser(base_domain=domain)

    try:
        parser.feed(html)
    except Exception:
        # Malformed HTML — return minimal analysis
        pass

    # Calculate category scores and collect issues
    meta_score, meta_issues = _score_meta(parser)
    content_score, content_issues = _score_content(parser)
    technical_score, technical_issues = _score_technical(parser)
    mobile_score, mobile_issues = _score_mobile(parser)

    # Performance score is estimated (no real timing data without JS)
    performance_score = 70  # Default baseline
    performance_issues: list[dict] = []
    if len(html) > 500_000:
        performance_score -= 20
        performance_issues.append({
            "severity": "warning",
            "category": "performance",
            "message": f"Large page size ({len(html) // 1024}KB) — consider reducing content",
        })

    # Weighted overall score
    overall_score = round(
        meta_score * 0.25
        + content_score * 0.25
        + technical_score * 0.20
        + mobile_score * 0.15
        + performance_score * 0.15
    )

    all_issues = meta_issues + content_issues + technical_issues + mobile_issues + performance_issues

    return PageAnalysis(
        url=url,
        title=parser.title.strip(),
        meta_description=parser.meta_description,
        h1_tags=parser.h1_tags,
        h2_tags=parser.h2_tags,
        h3_tags=parser.h3_tags,
        image_alt_texts=parser.image_alt_texts,
        images_without_alt=parser.images_without_alt,
        internal_links=parser.internal_links,
        external_links=parser.external_links,
        word_count=parser.get_word_count(),
        canonical_url=parser.canonical_url,
        og_tags=parser.og_tags,
        meta_score=meta_score,
        content_score=content_score,
        technical_score=technical_score,
        mobile_score=mobile_score,
        performance_score=performance_score,
        overall_score=overall_score,
        issues=all_issues,
    )


async def analyze_page(url: str, timeout: float = 15.0) -> PageAnalysis:
    """
    Fetch a web page and analyze it for SEO factors.

    Makes an HTTP GET request to the URL, then parses the HTML to extract
    SEO-relevant data and generate scores and issues.

    Args:
        url: The full URL of the page to analyze (must start with http/https).
        timeout: HTTP request timeout in seconds.

    Returns:
        A PageAnalysis dataclass with all extracted data, scores, and issues.

    Raises:
        httpx.HTTPError: If the page cannot be fetched.
    """
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "RankPilot-SEOBot/1.0"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        html = response.text

    return analyze_page_html(html, url)


# ── Mock Audit (Database-Backed) ──────────────────────────────────────


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

    # Update site's last_crawled timestamp (naive datetime for non-tz column)
    site.last_crawled = datetime.now(UTC).replace(tzinfo=None)
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
