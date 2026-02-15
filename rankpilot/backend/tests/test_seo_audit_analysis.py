"""
Tests for the real SEO page analysis service.

Covers the ``analyze_page_html`` function which parses raw HTML to
extract SEO-relevant data and generate scores with actionable issues.

For Developers:
    These tests provide HTML strings directly to ``analyze_page_html``
    instead of making HTTP requests. This tests the pure parsing logic
    without network dependencies.

For QA Engineers:
    These tests verify:
    - Title tag extraction and scoring.
    - Meta description extraction and scoring.
    - Heading hierarchy detection (H1, H2, H3).
    - Image alt text detection.
    - Link classification (internal vs external).
    - Word count estimation.
    - Canonical URL and Open Graph tag extraction.
    - Viewport meta tag detection (mobile score).
    - Overall score is a weighted average in 0-100 range.
    - Issue severity classification (critical, warning, info).
"""

import pytest

from app.services.audit_service import analyze_page_html, PageAnalysis


# ── Well-Formed HTML Fixtures ──────────────────────────────────────────


GOOD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Best SEO Tools for 2025</title>
    <meta name="description" content="Discover the top SEO tools that professionals use to improve search rankings and drive organic traffic in 2025.">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta property="og:title" content="Best SEO Tools for 2025">
    <meta property="og:description" content="Top SEO tools guide">
    <meta property="og:image" content="https://example.com/og-image.jpg">
    <link rel="canonical" href="https://example.com/seo-tools">
</head>
<body>
    <h1>The Best SEO Tools for 2025</h1>
    <p>Search engine optimization is a critical aspect of digital marketing.
    In this comprehensive guide, we review the best tools available to help
    you improve your website's visibility in search results. We cover keyword
    research tools, technical SEO analyzers, content optimization platforms,
    and link building tools that professional SEO practitioners rely on every day.
    These tools range from free options for beginners to enterprise solutions
    for large organizations with complex SEO needs and multiple domains to manage.
    Whether you are just starting out or looking to upgrade your toolkit, this
    guide has something valuable for everyone in the SEO community.</p>

    <h2>Keyword Research Tools</h2>
    <p>Good keyword research is the foundation of any SEO strategy.</p>
    <img src="/images/tools.jpg" alt="SEO keyword research tools">

    <h2>Technical SEO Analyzers</h2>
    <p>Technical SEO ensures your site is crawlable and indexable.</p>
    <img src="/images/tech-seo.jpg" alt="Technical SEO dashboard">

    <h3>Free Options</h3>
    <p>Several free tools offer solid technical SEO analysis capabilities.</p>

    <a href="/about">About Us</a>
    <a href="/products">Our Products</a>
    <a href="https://external-site.com/resource">External Resource</a>
</body>
</html>
"""

POOR_HTML = """
<html>
<head>
</head>
<body>
    <p>Short page.</p>
    <img src="/broken.jpg">
    <img src="/another.jpg">
</body>
</html>
"""

MULTI_H1_HTML = """
<html>
<head>
    <title>Test Page</title>
    <meta name="description" content="A test page with multiple H1 tags.">
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
    <h1>First Heading</h1>
    <h1>Second Heading</h1>
    <p>Some content about testing pages with duplicate H1 elements on a single page for SEO analysis purposes and scoring verification in the test suite to ensure the parser correctly detects and reports this common issue.</p>
</body>
</html>
"""


# ── Title Tag Tests ────────────────────────────────────────────────────


def test_analyze_extracts_title():
    """analyze_page_html extracts the title tag content."""
    analysis = analyze_page_html(GOOD_HTML, "https://example.com/seo-tools")
    assert analysis.title == "Best SEO Tools for 2025"


def test_analyze_missing_title_lowers_meta_score():
    """analyze_page_html with missing title tag produces a low meta_score."""
    analysis = analyze_page_html(POOR_HTML, "https://example.com/bad")
    assert analysis.title == ""
    assert analysis.meta_score < 60


# ── Meta Description Tests ──────────────────────────────────────────────


def test_analyze_extracts_meta_description():
    """analyze_page_html extracts the meta description content."""
    analysis = analyze_page_html(GOOD_HTML, "https://example.com/seo-tools")
    assert "top SEO tools" in analysis.meta_description


def test_analyze_missing_meta_description():
    """analyze_page_html flags missing meta description as critical."""
    analysis = analyze_page_html(POOR_HTML, "https://example.com/bad")
    assert analysis.meta_description == ""
    critical_issues = [i for i in analysis.issues if i["severity"] == "critical"]
    meta_issues = [i for i in critical_issues if i["category"] == "meta_tags"]
    assert len(meta_issues) > 0


# ── Heading Hierarchy Tests ──────────────────────────────────────────────


def test_analyze_extracts_headings():
    """analyze_page_html extracts H1, H2, and H3 heading tags."""
    analysis = analyze_page_html(GOOD_HTML, "https://example.com/seo-tools")
    assert len(analysis.h1_tags) == 1
    assert "Best SEO Tools" in analysis.h1_tags[0]
    assert len(analysis.h2_tags) == 2
    assert len(analysis.h3_tags) == 1


def test_analyze_detects_multiple_h1():
    """analyze_page_html flags multiple H1 tags as a warning."""
    analysis = analyze_page_html(MULTI_H1_HTML, "https://example.com/multi")
    assert len(analysis.h1_tags) == 2
    content_issues = [i for i in analysis.issues if i["category"] == "content"]
    h1_issues = [i for i in content_issues if "H1" in i["message"]]
    assert len(h1_issues) >= 1


def test_analyze_missing_h1():
    """analyze_page_html flags missing H1 heading as critical."""
    analysis = analyze_page_html(POOR_HTML, "https://example.com/bad")
    assert len(analysis.h1_tags) == 0
    critical_content = [
        i for i in analysis.issues
        if i["severity"] == "critical" and i["category"] == "content"
    ]
    assert len(critical_content) > 0


# ── Image Alt Text Tests ─────────────────────────────────────────────────


def test_analyze_extracts_image_alt_texts():
    """analyze_page_html extracts alt texts from images."""
    analysis = analyze_page_html(GOOD_HTML, "https://example.com/seo-tools")
    assert len(analysis.image_alt_texts) == 2
    assert analysis.images_without_alt == 0


def test_analyze_detects_missing_alt():
    """analyze_page_html counts images missing alt text."""
    analysis = analyze_page_html(POOR_HTML, "https://example.com/bad")
    assert analysis.images_without_alt == 2


# ── Link Classification Tests ────────────────────────────────────────────


def test_analyze_classifies_links():
    """analyze_page_html classifies links as internal or external."""
    analysis = analyze_page_html(GOOD_HTML, "https://example.com/seo-tools")
    assert len(analysis.internal_links) >= 2  # /about, /products
    assert len(analysis.external_links) >= 1  # external-site.com


# ── Word Count Tests ─────────────────────────────────────────────────────


def test_analyze_counts_words():
    """analyze_page_html calculates a reasonable word count."""
    analysis = analyze_page_html(GOOD_HTML, "https://example.com/seo-tools")
    assert analysis.word_count > 50  # Several paragraphs of content


def test_analyze_thin_content_flagged():
    """analyze_page_html flags thin content as a warning."""
    analysis = analyze_page_html(POOR_HTML, "https://example.com/bad")
    assert analysis.word_count < 300
    content_issues = [i for i in analysis.issues if i["category"] == "content"]
    thin_issues = [i for i in content_issues if "thin" in i["message"].lower() or "word" in i["message"].lower()]
    assert len(thin_issues) >= 1


# ── Canonical URL Tests ──────────────────────────────────────────────────


def test_analyze_extracts_canonical():
    """analyze_page_html extracts the canonical URL."""
    analysis = analyze_page_html(GOOD_HTML, "https://example.com/seo-tools")
    assert analysis.canonical_url == "https://example.com/seo-tools"


# ── Open Graph Tests ─────────────────────────────────────────────────────


def test_analyze_extracts_og_tags():
    """analyze_page_html extracts Open Graph meta tags."""
    analysis = analyze_page_html(GOOD_HTML, "https://example.com/seo-tools")
    assert "og:title" in analysis.og_tags
    assert "og:description" in analysis.og_tags
    assert "og:image" in analysis.og_tags


def test_analyze_missing_og_tags_noted():
    """analyze_page_html reports missing Open Graph tags as info issue."""
    analysis = analyze_page_html(POOR_HTML, "https://example.com/bad")
    assert len(analysis.og_tags) == 0
    info_issues = [i for i in analysis.issues if i["severity"] == "info"]
    og_issues = [i for i in info_issues if "open graph" in i["message"].lower()]
    assert len(og_issues) >= 1


# ── Viewport / Mobile Tests ──────────────────────────────────────────────


def test_analyze_viewport_present_good_mobile_score():
    """analyze_page_html with viewport meta tag gives good mobile score."""
    analysis = analyze_page_html(GOOD_HTML, "https://example.com/seo-tools")
    assert analysis.mobile_score >= 80


def test_analyze_missing_viewport_lowers_mobile_score():
    """analyze_page_html without viewport tag gives poor mobile score."""
    analysis = analyze_page_html(POOR_HTML, "https://example.com/bad")
    assert analysis.mobile_score < 80


# ── Overall Score Tests ──────────────────────────────────────────────────


def test_analyze_good_page_high_score():
    """analyze_page_html for a well-optimized page produces a high overall score."""
    analysis = analyze_page_html(GOOD_HTML, "https://example.com/seo-tools")
    assert analysis.overall_score >= 60
    assert 0 <= analysis.overall_score <= 100


def test_analyze_poor_page_low_score():
    """analyze_page_html for a poorly-optimized page produces a low overall score."""
    analysis = analyze_page_html(POOR_HTML, "https://example.com/bad")
    assert analysis.overall_score < 60
    assert 0 <= analysis.overall_score <= 100


# ── Issue Structure Tests ────────────────────────────────────────────────


def test_issues_have_required_fields():
    """All issues returned by analyze_page_html have severity, category, and message."""
    analysis = analyze_page_html(POOR_HTML, "https://example.com/bad")
    assert len(analysis.issues) > 0
    for issue in analysis.issues:
        assert "severity" in issue
        assert "category" in issue
        assert "message" in issue
        assert issue["severity"] in ("critical", "warning", "info")


# ── Empty HTML Test ──────────────────────────────────────────────────────


def test_analyze_empty_html():
    """analyze_page_html handles empty HTML gracefully."""
    analysis = analyze_page_html("", "")
    assert isinstance(analysis, PageAnalysis)
    assert analysis.overall_score >= 0
