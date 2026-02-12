"""
Schema markup service for JSON-LD structured data generation.

Generates and manages JSON-LD (schema.org) structured data templates
for different page types. Supports Product, Article, FAQ, BreadcrumbList,
and Organization schema types.

For Developers:
    Each page_type has a default template generator. Custom templates
    are stored in the database and can be edited by the user. The
    `preview_schema` function renders a JSON-LD script tag.

For QA Engineers:
    Verify that generated JSON-LD is valid schema.org markup.
    Test each page_type generates the correct @type.
    Test the preview endpoint returns properly formatted JSON-LD.

For Project Managers:
    Schema markup helps sites appear with rich snippets in search results
    (star ratings, prices, FAQ dropdowns, etc.), increasing click-through rates.

For End Users:
    Add structured data to your pages to help search engines understand
    your content. This can improve how your site appears in search results.
"""

import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema_config import SchemaConfig


def generate_default_schema(page_type: str, domain: str = "example.com") -> dict:
    """
    Generate a default JSON-LD schema template for a given page type.

    Each template follows the schema.org specification and includes
    placeholder values that users should customize.

    Args:
        page_type: The schema.org type ('product', 'article', 'faq',
                   'breadcrumb', 'organization').
        domain: The site's domain for URL generation.

    Returns:
        A JSON-LD schema object with the @context, @type, and type-specific fields.

    Raises:
        ValueError: If page_type is not a supported schema type.
    """
    templates = {
        "product": {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Example Product",
            "description": "A high-quality product description for SEO.",
            "image": f"https://{domain}/images/product.jpg",
            "brand": {"@type": "Brand", "name": "Your Brand"},
            "offers": {
                "@type": "Offer",
                "price": "29.99",
                "priceCurrency": "USD",
                "availability": "https://schema.org/InStock",
                "url": f"https://{domain}/products/example",
            },
            "aggregateRating": {
                "@type": "AggregateRating",
                "ratingValue": "4.5",
                "reviewCount": "42",
            },
        },
        "article": {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "Article Headline",
            "description": "A brief description of the article content.",
            "image": f"https://{domain}/images/article.jpg",
            "author": {"@type": "Person", "name": "Author Name"},
            "publisher": {
                "@type": "Organization",
                "name": "Publisher Name",
                "logo": {
                    "@type": "ImageObject",
                    "url": f"https://{domain}/logo.png",
                },
            },
            "datePublished": "2024-01-01",
            "dateModified": "2024-01-15",
        },
        "faq": {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": "What is your return policy?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "We offer a 30-day return policy for all items.",
                    },
                },
                {
                    "@type": "Question",
                    "name": "How long does shipping take?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "Standard shipping takes 5-7 business days.",
                    },
                },
            ],
        },
        "breadcrumb": {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Home",
                    "item": f"https://{domain}/",
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "Products",
                    "item": f"https://{domain}/products",
                },
                {
                    "@type": "ListItem",
                    "position": 3,
                    "name": "Product Name",
                    "item": f"https://{domain}/products/example",
                },
            ],
        },
        "organization": {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Your Company Name",
            "url": f"https://{domain}",
            "logo": f"https://{domain}/logo.png",
            "description": "A brief description of your organization.",
            "contactPoint": {
                "@type": "ContactPoint",
                "telephone": "+1-555-000-0000",
                "contactType": "customer service",
                "email": f"support@{domain}",
            },
            "sameAs": [
                "https://twitter.com/yourcompany",
                "https://linkedin.com/company/yourcompany",
                "https://facebook.com/yourcompany",
            ],
        },
    }

    if page_type not in templates:
        raise ValueError(f"Unsupported schema type: {page_type}")

    return templates[page_type]


async def create_schema_config(
    db: AsyncSession,
    site_id: uuid.UUID,
    page_type: str,
    schema_json: dict | None = None,
    domain: str = "example.com",
) -> SchemaConfig:
    """
    Create a new schema markup configuration for a site.

    If no custom schema_json is provided, generates a default template
    based on the page_type.

    Args:
        db: Async database session.
        site_id: Parent site UUID.
        page_type: Schema.org type ('product', 'article', 'faq', 'breadcrumb', 'organization').
        schema_json: Custom JSON-LD template (optional, defaults to generated template).
        domain: Site domain for URL generation in default templates.

    Returns:
        The newly created SchemaConfig.
    """
    if schema_json is None:
        schema_json = generate_default_schema(page_type, domain)

    config = SchemaConfig(
        site_id=site_id,
        page_type=page_type,
        schema_json=schema_json,
    )
    db.add(config)
    await db.flush()
    return config


async def get_schema_config(
    db: AsyncSession,
    config_id: uuid.UUID,
) -> SchemaConfig | None:
    """
    Get a single schema configuration by ID.

    Args:
        db: Async database session.
        config_id: The schema config's UUID.

    Returns:
        The SchemaConfig if found, None otherwise.
    """
    result = await db.execute(
        select(SchemaConfig).where(SchemaConfig.id == config_id)
    )
    return result.scalar_one_or_none()


async def list_schema_configs(
    db: AsyncSession,
    site_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[SchemaConfig], int]:
    """
    List schema configurations for a site with pagination.

    Args:
        db: Async database session.
        site_id: The site's UUID.
        page: Page number (1-indexed).
        per_page: Items per page.

    Returns:
        Tuple of (list of SchemaConfigs, total count).
    """
    count_result = await db.execute(
        select(func.count())
        .select_from(SchemaConfig)
        .where(SchemaConfig.site_id == site_id)
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * per_page
    result = await db.execute(
        select(SchemaConfig)
        .where(SchemaConfig.site_id == site_id)
        .order_by(SchemaConfig.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    configs = list(result.scalars().all())
    return configs, total


async def update_schema_config(
    db: AsyncSession,
    config: SchemaConfig,
    schema_json: dict | None = None,
    is_active: bool | None = None,
) -> SchemaConfig:
    """
    Update a schema configuration.

    Args:
        db: Async database session.
        config: The SchemaConfig to update.
        schema_json: Updated JSON-LD template.
        is_active: Updated active status.

    Returns:
        The updated SchemaConfig.
    """
    if schema_json is not None:
        config.schema_json = schema_json
    if is_active is not None:
        config.is_active = is_active

    await db.flush()
    return config


async def delete_schema_config(
    db: AsyncSession,
    config: SchemaConfig,
) -> None:
    """
    Delete a schema configuration.

    Args:
        db: Async database session.
        config: The SchemaConfig to delete.
    """
    await db.delete(config)
    await db.flush()


def render_json_ld(schema_json: dict) -> str:
    """
    Render a JSON-LD schema object as an HTML script tag.

    Produces a properly formatted <script type="application/ld+json">
    tag ready to be embedded in an HTML page.

    Args:
        schema_json: The JSON-LD object to render.

    Returns:
        HTML script tag string with formatted JSON-LD.
    """
    formatted_json = json.dumps(schema_json, indent=2)
    return f'<script type="application/ld+json">\n{formatted_json}\n</script>'
