"""
Tests for standalone Schema.org JSON-LD generators.

Covers the product, FAQ, breadcrumb, and aggregate rating schema
generators that produce valid JSON-LD structured data.

For Developers:
    These tests validate the structure of generated JSON-LD objects.
    Each generator function is pure (no DB or HTTP dependencies).

For QA Engineers:
    These tests verify:
    - Product schema includes @context, @type, offers, and optional fields.
    - FAQ schema includes mainEntity with Question/Answer pairs.
    - Breadcrumb schema includes itemListElement with correct positions.
    - Aggregate rating schema includes ratingValue and reviewCount.
    - All schemas include the correct @context ('https://schema.org').
"""

import pytest

from app.services.schema_service import (
    generate_product_schema,
    generate_faq_schema,
    generate_breadcrumb_schema,
    generate_aggregate_rating_schema,
)


# ── Product Schema Tests ─────────────────────────────────────────────────


def test_product_schema_basic():
    """generate_product_schema returns valid Product schema with required fields."""
    schema = generate_product_schema({"name": "SEO Tool Pro"})
    assert schema["@context"] == "https://schema.org"
    assert schema["@type"] == "Product"
    assert schema["name"] == "SEO Tool Pro"
    assert "offers" in schema


def test_product_schema_with_all_fields():
    """generate_product_schema includes all optional fields when provided."""
    schema = generate_product_schema({
        "name": "SEO Tool Pro",
        "description": "The best SEO tool available",
        "image": "https://example.com/tool.jpg",
        "price": 29.99,
        "currency": "EUR",
        "availability": "InStock",
        "url": "https://example.com/products/seo-tool",
        "brand": "SEOBrand",
        "sku": "SKU-001",
        "rating_value": 4.7,
        "review_count": 150,
    })

    assert schema["description"] == "The best SEO tool available"
    assert schema["image"] == "https://example.com/tool.jpg"
    assert schema["sku"] == "SKU-001"
    assert schema["brand"]["@type"] == "Brand"
    assert schema["brand"]["name"] == "SEOBrand"
    assert schema["offers"]["price"] == "29.99"
    assert schema["offers"]["priceCurrency"] == "EUR"
    assert "InStock" in schema["offers"]["availability"]
    assert schema["aggregateRating"]["ratingValue"] == "4.7"
    assert schema["aggregateRating"]["reviewCount"] == "150"


def test_product_schema_without_rating():
    """generate_product_schema omits aggregateRating when not provided."""
    schema = generate_product_schema({"name": "Basic Product"})
    assert "aggregateRating" not in schema


def test_product_schema_default_currency():
    """generate_product_schema defaults to USD currency."""
    schema = generate_product_schema({"name": "Product", "price": 10})
    assert schema["offers"]["priceCurrency"] == "USD"


# ── FAQ Schema Tests ─────────────────────────────────────────────────────


def test_faq_schema_basic():
    """generate_faq_schema returns valid FAQPage schema."""
    faqs = [
        {"question": "What is SEO?", "answer": "SEO stands for Search Engine Optimization."},
        {"question": "How long does SEO take?", "answer": "SEO results typically take 3-6 months."},
    ]
    schema = generate_faq_schema(faqs)

    assert schema["@context"] == "https://schema.org"
    assert schema["@type"] == "FAQPage"
    assert len(schema["mainEntity"]) == 2
    assert schema["mainEntity"][0]["@type"] == "Question"
    assert schema["mainEntity"][0]["name"] == "What is SEO?"
    assert schema["mainEntity"][0]["acceptedAnswer"]["@type"] == "Answer"
    assert "Search Engine Optimization" in schema["mainEntity"][0]["acceptedAnswer"]["text"]


def test_faq_schema_empty_list():
    """generate_faq_schema with empty list returns FAQPage with no entities."""
    schema = generate_faq_schema([])
    assert schema["@type"] == "FAQPage"
    assert schema["mainEntity"] == []


def test_faq_schema_skips_incomplete_entries():
    """generate_faq_schema skips entries missing question or answer."""
    faqs = [
        {"question": "Valid?", "answer": "Yes."},
        {"question": "", "answer": "Missing question"},
        {"question": "Missing answer", "answer": ""},
    ]
    schema = generate_faq_schema(faqs)
    assert len(schema["mainEntity"]) == 1


# ── Breadcrumb Schema Tests ──────────────────────────────────────────────


def test_breadcrumb_schema_basic():
    """generate_breadcrumb_schema returns valid BreadcrumbList schema."""
    breadcrumbs = [
        {"name": "Home", "url": "https://example.com/"},
        {"name": "Products", "url": "https://example.com/products"},
        {"name": "SEO Tool", "url": "https://example.com/products/seo-tool"},
    ]
    schema = generate_breadcrumb_schema(breadcrumbs)

    assert schema["@context"] == "https://schema.org"
    assert schema["@type"] == "BreadcrumbList"
    assert len(schema["itemListElement"]) == 3

    # Check positions are sequential
    for i, item in enumerate(schema["itemListElement"], start=1):
        assert item["@type"] == "ListItem"
        assert item["position"] == i


def test_breadcrumb_schema_single_item():
    """generate_breadcrumb_schema works with a single breadcrumb."""
    schema = generate_breadcrumb_schema([{"name": "Home", "url": "https://example.com/"}])
    assert len(schema["itemListElement"]) == 1
    assert schema["itemListElement"][0]["position"] == 1


def test_breadcrumb_schema_empty():
    """generate_breadcrumb_schema with empty list returns empty BreadcrumbList."""
    schema = generate_breadcrumb_schema([])
    assert schema["@type"] == "BreadcrumbList"
    assert schema["itemListElement"] == []


# ── Aggregate Rating Schema Tests ────────────────────────────────────────


def test_aggregate_rating_schema():
    """generate_aggregate_rating_schema returns valid AggregateRating schema."""
    schema = generate_aggregate_rating_schema(4.5, 200)

    assert schema["@context"] == "https://schema.org"
    assert schema["@type"] == "AggregateRating"
    assert schema["ratingValue"] == "4.5"
    assert schema["reviewCount"] == "200"
    assert schema["bestRating"] == "5"
    assert schema["worstRating"] == "1"


def test_aggregate_rating_schema_edge_values():
    """generate_aggregate_rating_schema handles edge rating values."""
    schema = generate_aggregate_rating_schema(1.0, 1)
    assert schema["ratingValue"] == "1.0"
    assert schema["reviewCount"] == "1"
