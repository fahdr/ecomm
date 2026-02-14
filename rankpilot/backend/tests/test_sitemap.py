"""
Tests for XML sitemap generation.

Covers the ``generate_xml_sitemap`` function which produces valid
XML sitemaps conforming to the Sitemap protocol 0.9 specification.

For Developers:
    These tests validate XML structure directly via string assertions.
    No XML parser is used — we check for expected tag patterns.

For QA Engineers:
    These tests verify:
    - XML declaration and urlset namespace are present.
    - URL entries contain <loc> elements.
    - Optional fields (lastmod, changefreq, priority) are included when provided.
    - Empty URL list produces a valid but empty sitemap.
    - Special characters in URLs are properly XML-escaped.
    - URLs without 'loc' are skipped.
"""

import pytest

from app.services.sitemap_service import generate_xml_sitemap


def test_sitemap_basic():
    """generate_xml_sitemap produces valid XML with urlset namespace."""
    urls = [{"loc": "https://example.com/"}]
    xml = generate_xml_sitemap(urls)

    assert '<?xml version="1.0"' in xml
    assert 'encoding="UTF-8"' in xml
    assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in xml
    assert "</urlset>" in xml
    assert "<url>" in xml
    assert "<loc>https://example.com/</loc>" in xml


def test_sitemap_multiple_urls():
    """generate_xml_sitemap includes all provided URLs."""
    urls = [
        {"loc": "https://example.com/"},
        {"loc": "https://example.com/products"},
        {"loc": "https://example.com/about"},
    ]
    xml = generate_xml_sitemap(urls)

    assert xml.count("<url>") == 3
    assert xml.count("</url>") == 3
    assert "https://example.com/" in xml
    assert "https://example.com/products" in xml
    assert "https://example.com/about" in xml


def test_sitemap_with_optional_fields():
    """generate_xml_sitemap includes lastmod, changefreq, and priority when provided."""
    urls = [
        {
            "loc": "https://example.com/",
            "lastmod": "2025-01-15",
            "changefreq": "daily",
            "priority": "1.0",
        }
    ]
    xml = generate_xml_sitemap(urls)

    assert "<lastmod>2025-01-15</lastmod>" in xml
    assert "<changefreq>daily</changefreq>" in xml
    assert "<priority>1.0</priority>" in xml


def test_sitemap_partial_optional_fields():
    """generate_xml_sitemap only includes provided optional fields."""
    urls = [
        {"loc": "https://example.com/", "priority": "0.8"}
    ]
    xml = generate_xml_sitemap(urls)

    assert "<loc>https://example.com/</loc>" in xml
    assert "<priority>0.8</priority>" in xml
    assert "<lastmod>" not in xml
    assert "<changefreq>" not in xml


def test_sitemap_empty_list():
    """generate_xml_sitemap with empty list produces valid empty sitemap."""
    xml = generate_xml_sitemap([])

    assert '<?xml version="1.0"' in xml
    assert "<urlset" in xml
    assert "</urlset>" in xml
    assert "<url>" not in xml


def test_sitemap_skips_entries_without_loc():
    """generate_xml_sitemap skips URL entries that have no 'loc' field."""
    urls = [
        {"loc": "https://example.com/"},
        {"changefreq": "daily"},  # No loc
        {"loc": ""},  # Empty loc
    ]
    xml = generate_xml_sitemap(urls)

    assert xml.count("<url>") == 1


def test_sitemap_escapes_special_characters():
    """generate_xml_sitemap properly escapes XML special characters in URLs."""
    urls = [{"loc": "https://example.com/search?q=test&lang=en"}]
    xml = generate_xml_sitemap(urls)

    assert "&amp;" in xml
    assert "&lang" not in xml.replace("&amp;", "")
