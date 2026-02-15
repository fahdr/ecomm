"""
Template service unit tests.

Tests the prompt template registry, template retrieval, and template
listing functions.

For Developers:
    These tests verify the template_service module's in-memory registry
    without database dependencies. They ensure all 10+ template styles
    are registered and accessible.

For QA Engineers:
    Run with: ``pytest tests/test_template_service.py -v``
    Tests verify:
    - All 10 template styles are registered
    - get_template returns valid PromptTemplate for each style/type combo
    - get_template falls back to default for unknown style names
    - get_template returns None for unknown content types
    - list_template_names returns sorted list
    - All templates have required fields populated
"""

import pytest

from app.services.template_service import (
    ALL_CONTENT_TYPES,
    DEFAULT_TEMPLATE_NAME,
    TEMPLATE_REGISTRY,
    PromptTemplate,
    get_all_templates_for_style,
    get_template,
    list_content_types,
    list_template_names,
)


def test_registry_has_ten_or_more_styles():
    """Template registry contains at least 10 template styles."""
    names = list_template_names()
    assert len(names) >= 10, f"Expected 10+ styles, got {len(names)}: {names}"


def test_list_template_names_sorted():
    """list_template_names returns alphabetically sorted names."""
    names = list_template_names()
    assert names == sorted(names)


def test_list_content_types():
    """list_content_types returns all supported types including social_caption."""
    types = list_content_types()
    assert "title" in types
    assert "description" in types
    assert "meta_description" in types
    assert "keywords" in types
    assert "bullet_points" in types
    assert "social_caption" in types


def test_all_styles_have_all_content_types():
    """Every registered style provides templates for all content types."""
    for style_name, style_templates in TEMPLATE_REGISTRY.items():
        for ct in ALL_CONTENT_TYPES:
            assert ct in style_templates, (
                f"Style '{style_name}' is missing content type '{ct}'"
            )


def test_get_template_returns_prompt_template():
    """get_template returns a PromptTemplate instance for known style/type."""
    tmpl = get_template("amazon_style", "title")
    assert isinstance(tmpl, PromptTemplate)
    assert tmpl.style_name == "amazon_style"
    assert tmpl.content_type == "title"


def test_get_template_fallback_to_default():
    """get_template falls back to default style for unknown style name."""
    tmpl = get_template("nonexistent_style_xyz", "title")
    assert tmpl is not None
    assert tmpl.style_name == DEFAULT_TEMPLATE_NAME


def test_get_template_returns_none_for_unknown_content_type():
    """get_template returns None for content types not in any style."""
    tmpl = get_template("amazon_style", "nonexistent_content_type_xyz")
    assert tmpl is None


def test_all_templates_have_required_fields():
    """Every template has non-empty system_prompt and user_prompt_template."""
    for style_name, style_templates in TEMPLATE_REGISTRY.items():
        for ct, tmpl in style_templates.items():
            assert tmpl.system_prompt, (
                f"{style_name}/{ct} has empty system_prompt"
            )
            assert tmpl.user_prompt_template, (
                f"{style_name}/{ct} has empty user_prompt_template"
            )
            assert tmpl.output_format, (
                f"{style_name}/{ct} has empty output_format"
            )
            assert tmpl.max_tokens > 0, (
                f"{style_name}/{ct} has invalid max_tokens: {tmpl.max_tokens}"
            )
            assert 0.0 <= tmpl.temperature <= 1.0, (
                f"{style_name}/{ct} has invalid temperature: {tmpl.temperature}"
            )


def test_get_all_templates_for_style():
    """get_all_templates_for_style returns all content types for a style."""
    templates = get_all_templates_for_style("luxury_brand")
    assert len(templates) == len(ALL_CONTENT_TYPES)
    for ct in ALL_CONTENT_TYPES:
        assert ct in templates


def test_get_all_templates_for_unknown_style():
    """get_all_templates_for_style returns empty dict for unknown style."""
    templates = get_all_templates_for_style("nonexistent_xyz")
    assert templates == {}


def test_template_prompt_has_placeholders():
    """User prompt templates contain product data placeholders."""
    tmpl = get_template("shopify_seo", "description")
    assert tmpl is not None
    assert "{product_name}" in tmpl.user_prompt_template
    assert "{product_features}" in tmpl.user_prompt_template


def test_specific_styles_exist():
    """Verify all 10 required template styles are registered."""
    expected_styles = [
        "amazon_style",
        "shopify_seo",
        "luxury_brand",
        "technical_spec",
        "casual_friendly",
        "minimalist",
        "storytelling",
        "feature_focused",
        "benefit_driven",
        "comparison",
    ]
    registered = list_template_names()
    for style in expected_styles:
        assert style in registered, f"Missing required style: {style}"


def test_default_template_name_is_registered():
    """The DEFAULT_TEMPLATE_NAME actually exists in the registry."""
    assert DEFAULT_TEMPLATE_NAME in TEMPLATE_REGISTRY
