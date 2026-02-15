"""
Pydantic schemas for content generation, templates, and image processing.

Defines request/response models for all ContentForge feature endpoints.
Handles validation of user input for generation jobs, templates, and images.

For Developers:
    All schemas use Pydantic v2 with `model_config = {"from_attributes": True}`
    for ORM model serialization. Nested schemas (e.g., GeneratedContentResponse
    inside GenerationJobResponse) are resolved via `from_attributes`.

    Pagination follows the standard `{ items, total, page, per_page }` envelope.

For QA Engineers:
    Test validation rules:
    - GenerationJobCreate requires either source_url or source_data
    - TemplateCreate requires name and tone
    - BulkGenerationRequest requires at least one URL or CSV data
    - content_types must be from the allowed set

For Project Managers:
    These schemas define the API contract for all content generation features.
    Changes here affect both the backend validation and dashboard integration.

For End Users:
    These define what data you send when generating content and what you
    receive back. The API docs at /docs show these schemas interactively.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# Valid content types that can be generated
VALID_CONTENT_TYPES = [
    "title",
    "description",
    "meta_description",
    "keywords",
    "bullet_points",
    "social_caption",
]

# Valid tone options for templates
VALID_TONES = ["professional", "casual", "luxury", "playful", "technical"]

# Valid style options for templates
VALID_STYLES = ["concise", "detailed", "storytelling", "list-based"]


# ── Generated Content Schemas ──────────────────────────────────────


class GeneratedContentResponse(BaseModel):
    """
    Response schema for a single piece of generated content.

    Attributes:
        id: Content record UUID.
        job_id: Parent generation job UUID.
        content_type: Type of content (title, description, etc.).
        content: The generated text.
        version: Version number for regeneration tracking.
        word_count: Number of words in the content.
        created_at: Creation timestamp.
    """

    id: uuid.UUID
    job_id: uuid.UUID
    content_type: str
    content: str
    version: int
    word_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class GeneratedContentUpdate(BaseModel):
    """
    Request schema for editing generated content.

    Attributes:
        content: The updated text content.
    """

    content: str = Field(..., min_length=1, description="Updated content text")


# ── Image Job Schemas ──────────────────────────────────────────────


class ImageJobResponse(BaseModel):
    """
    Response schema for an image processing record.

    Attributes:
        id: Image job UUID.
        job_id: Parent generation job UUID.
        original_url: Source image URL.
        optimized_url: Processed image URL (null if pending).
        format: Output format (e.g., "webp").
        width: Image width in pixels.
        height: Image height in pixels.
        size_bytes: File size in bytes.
        status: Processing status.
        error_message: Error details if failed.
        created_at: Creation timestamp.
    """

    id: uuid.UUID
    job_id: uuid.UUID
    original_url: str
    optimized_url: str | None
    format: str
    width: int | None
    height: int | None
    size_bytes: int | None
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Generation Job Schemas ─────────────────────────────────────────


class GenerationJobCreate(BaseModel):
    """
    Request schema for creating a content generation job.

    Provide either `source_url` for URL-based scraping or `source_data`
    for manual product data entry. Optionally attach a template.

    Attributes:
        source_url: Product page URL to scrape (optional).
        source_type: Input method — "url", "csv", or "manual" (default "manual").
        source_data: Product data dict (name, price, features, etc.).
        template_id: UUID of the template to use (optional — uses default).
        content_types: Which content types to generate (defaults to all).
        image_urls: Product image URLs to process (optional).
    """

    source_url: str | None = Field(None, description="Product URL to scrape")
    source_type: str = Field("manual", description="Input method: url, csv, or manual")
    source_data: dict = Field(
        default_factory=dict,
        description="Product data (name, price, description, features, etc.)",
    )
    template_id: uuid.UUID | None = Field(None, description="Template UUID to use")
    content_types: list[str] = Field(
        default_factory=lambda: list(VALID_CONTENT_TYPES),
        description="Content types to generate",
    )
    image_urls: list[str] = Field(
        default_factory=list,
        description="Product image URLs to optimize",
    )


class GenerationJobResponse(BaseModel):
    """
    Response schema for a generation job with its content and images.

    Attributes:
        id: Job UUID.
        user_id: Owning user UUID.
        source_url: Input product URL (if URL-based).
        source_type: Input method used.
        source_data: Raw input data.
        template_id: Template UUID used (if any).
        status: Current job status.
        error_message: Error details if failed.
        created_at: Job creation timestamp.
        completed_at: Completion timestamp.
        content_items: List of generated content pieces.
        image_items: List of processed images.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    source_url: str | None
    source_type: str
    source_data: dict
    template_id: uuid.UUID | None
    status: str
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    content_items: list[GeneratedContentResponse] = []
    image_items: list[ImageJobResponse] = []

    model_config = {"from_attributes": True}


class BulkGenerationRequest(BaseModel):
    """
    Request schema for bulk content generation from multiple URLs or CSV.

    Provide either a list of URLs or raw CSV text. Each URL or CSV row
    creates a separate generation job.

    Attributes:
        urls: List of product page URLs to generate content for.
        csv_data: Raw CSV text with product data (one product per row).
        template_id: Template UUID to apply to all jobs.
        content_types: Content types to generate for all jobs.
    """

    urls: list[str] = Field(
        default_factory=list,
        description="Product URLs for bulk generation",
    )
    csv_data: str | None = Field(None, description="CSV text with product data")
    template_id: uuid.UUID | None = Field(None, description="Template for all jobs")
    content_types: list[str] = Field(
        default_factory=lambda: list(VALID_CONTENT_TYPES),
        description="Content types to generate",
    )


# ── Template Schemas ───────────────────────────────────────────────


class TemplateCreate(BaseModel):
    """
    Request schema for creating a custom content template.

    Attributes:
        name: Template display name.
        description: Optional description of the template's purpose.
        tone: Writing tone (professional, casual, luxury, playful, technical).
        style: Content structure (concise, detailed, storytelling, list-based).
        prompt_override: Optional custom AI prompt.
        content_types: Which content types this template generates.
    """

    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: str | None = Field(None, description="Template description")
    tone: str = Field("professional", description="Writing tone")
    style: str = Field("detailed", description="Content structure style")
    prompt_override: str | None = Field(None, description="Custom AI prompt override")
    content_types: list[str] = Field(
        default_factory=lambda: list(VALID_CONTENT_TYPES),
        description="Content types to generate",
    )


class TemplateUpdate(BaseModel):
    """
    Request schema for updating a custom template.

    All fields are optional — only provided fields are updated.

    Attributes:
        name: Updated template name.
        description: Updated description.
        tone: Updated writing tone.
        style: Updated content structure.
        prompt_override: Updated custom AI prompt.
        content_types: Updated content type list.
    """

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    tone: str | None = None
    style: str | None = None
    prompt_override: str | None = None
    content_types: list[str] | None = None


class TemplateResponse(BaseModel):
    """
    Response schema for a content template.

    Attributes:
        id: Template UUID.
        user_id: Owning user UUID (null for system templates).
        name: Template display name.
        description: Template description.
        tone: Writing tone setting.
        style: Content structure setting.
        prompt_override: Custom AI prompt (if any).
        content_types: Content types this template generates.
        is_default: Whether this is the default template.
        is_system: Whether this is a system template.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID | None
    name: str
    description: str | None
    tone: str
    style: str
    prompt_override: str | None
    content_types: list[str]
    is_default: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Pagination Schemas ─────────────────────────────────────────────


class PaginatedGenerationJobs(BaseModel):
    """
    Paginated list of generation jobs.

    Attributes:
        items: List of generation job records.
        total: Total number of matching records.
        page: Current page number.
        per_page: Number of items per page.
    """

    items: list[GenerationJobResponse]
    total: int
    page: int
    per_page: int


class PaginatedImages(BaseModel):
    """
    Paginated list of image processing records.

    Attributes:
        items: List of image job records.
        total: Total number of matching records.
        page: Current page number.
        per_page: Number of items per page.
    """

    items: list[ImageJobResponse]
    total: int
    page: int
    per_page: int


# ── Store Connection Schemas ──────────────────────────────────────────

# Valid e-commerce platforms
VALID_PLATFORMS = ["shopify", "woocommerce", "platform"]


class StoreConnectionCreate(BaseModel):
    """
    Request schema for connecting an external e-commerce store.

    Attributes:
        platform: E-commerce platform — 'shopify', 'woocommerce', or 'platform'.
        store_url: The store's public URL (e.g., 'mystore.myshopify.com').
        api_key: API key for store authentication.
        api_secret: API secret for store authentication (optional for some platforms).
    """

    platform: str = Field(
        ..., description="E-commerce platform: shopify, woocommerce, or platform"
    )
    store_url: str = Field(
        ..., min_length=1, description="Store URL (e.g., mystore.myshopify.com)"
    )
    api_key: str = Field(
        ..., min_length=1, description="Store API key"
    )
    api_secret: str = Field(
        "", description="Store API secret (optional for some platforms)"
    )


class StoreConnectionResponse(BaseModel):
    """
    Response schema for a store connection.

    Note: API credentials are never returned in responses for security.

    Attributes:
        id: Connection UUID.
        user_id: Owning user UUID.
        platform: Connected platform name.
        store_url: Store URL.
        is_active: Whether the connection is active.
        last_synced_at: Timestamp of last successful sync.
        created_at: Connection creation timestamp.
        updated_at: Last modification timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    platform: str
    store_url: str
    is_active: bool
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StoreConnectionTestResult(BaseModel):
    """
    Response schema for testing a store connection.

    Attributes:
        connection_id: The connection UUID that was tested.
        success: Whether the connectivity test passed.
        message: Human-readable result message.
        store_name: The store's display name (if retrieved successfully).
        product_count: Number of products in the store (if retrieved).
    """

    connection_id: uuid.UUID
    success: bool
    message: str
    store_name: str | None = None
    product_count: int | None = None


# ── Bulk Generation v2 Schemas ────────────────────────────────────────


class BulkGenerationV2Request(BaseModel):
    """
    Request schema for bulk content generation (v2).

    Supports generating content for a list of product data dicts,
    or for all products from a connected store.

    Attributes:
        products: List of product data dicts to generate content for.
        connection_id: Optional store connection ID to pull all products from.
        template_name: Prompt template style name (e.g., 'amazon_style').
        content_types: Content types to generate for all products.
    """

    products: list[dict] = Field(
        default_factory=list,
        description="List of product data dicts (name, price, features, etc.)",
    )
    connection_id: uuid.UUID | None = Field(
        None,
        description="Store connection UUID — generate for all connected store products",
    )
    template_name: str = Field(
        "shopify_seo",
        description="Prompt template style name",
    )
    content_types: list[str] = Field(
        default_factory=lambda: list(VALID_CONTENT_TYPES),
        description="Content types to generate",
    )


class BulkGenerationStatusResponse(BaseModel):
    """
    Response schema for a bulk generation request.

    Attributes:
        total_products: Number of products queued for generation.
        jobs_created: Number of generation jobs successfully created.
        jobs: List of created generation job responses.
        errors: List of error messages for any failed product generations.
    """

    total_products: int
    jobs_created: int
    jobs: list[GenerationJobResponse] = []
    errors: list[str] = []


# ── Export Schemas ────────────────────────────────────────────────────


class ExportContentRequest(BaseModel):
    """
    Request schema for exporting generated content to a connected store.

    Attributes:
        connection_id: The store connection UUID to export to.
        product_id: The external product ID in the connected store.
        field_mapping: Optional mapping of content_type to store field name.
            Defaults to standard field names per platform.
    """

    connection_id: uuid.UUID = Field(
        ..., description="Store connection UUID to export to"
    )
    product_id: str = Field(
        ..., min_length=1, description="External product ID in the connected store"
    )
    field_mapping: dict[str, str] | None = Field(
        None,
        description="Optional mapping: content_type -> store field name",
    )


class ExportContentResponse(BaseModel):
    """
    Response schema for a content export operation.

    Attributes:
        success: Whether the export succeeded.
        job_id: The generation job UUID that was exported.
        connection_id: The store connection UUID used.
        product_id: The external product ID that was updated.
        fields_updated: List of content types that were exported.
        message: Human-readable status message.
    """

    success: bool
    job_id: uuid.UUID
    connection_id: uuid.UUID
    product_id: str
    fields_updated: list[str] = []
    message: str


# ── A/B Variant Schemas ──────────────────────────────────────────────


class ABVariantRequest(BaseModel):
    """
    Request schema for generating A/B test content variants.

    Generates multiple alternative versions of a single content type
    for split-testing on your store.

    Attributes:
        product_data: Product information dict.
        content_type: The content type to generate variants for.
        template_name: Prompt template style name.
        count: Number of variants to generate (default 3, max 5).
    """

    product_data: dict = Field(
        ..., description="Product data (name, price, features, etc.)"
    )
    content_type: str = Field(
        "title", description="Content type to generate variants for"
    )
    template_name: str = Field(
        "shopify_seo", description="Prompt template style"
    )
    count: int = Field(
        3, ge=1, le=5, description="Number of variants (1-5)"
    )


class ABVariantResponse(BaseModel):
    """
    Response schema for A/B test variants.

    Attributes:
        content_type: The content type that was varied.
        variants: List of variant content strings.
        template_name: The template style used.
    """

    content_type: str
    variants: list[str]
    template_name: str
