"""
Content generation service — core business logic for creating and managing
content generation jobs, checking plan limits, and producing AI content.

Supports both mock generation (for tests and development) and real
LLM-powered generation via the centralized LLM Gateway.

For Developers:
    This service coordinates the content generation workflow:
    1. ``create_generation_job()`` — validates input, checks plan limits, creates job
    2. ``generate_content()`` — produces LLM-powered content for each content type
    3. ``generate_mock_content()`` — fallback mock content (no LLM needed)
    4. ``generate_ab_variants()`` — produces multiple A/B test variants
    5. ``get_generation_jobs()`` — paginated listing for the history page
    6. ``get_generation_job()`` — single job with all content and images

    The ``generate_content()`` function calls the LLM Gateway via the
    template service to build specialized prompts per content type.
    When the gateway is unavailable, it falls back to ``generate_mock_content()``.

    Plan limit checking uses the PLAN_LIMITS from constants/plans.py.
    The count of jobs in the current billing period determines usage.

For QA Engineers:
    Test plan limit enforcement:
    - Free tier: 10 generations/month — 11th should fail with 403
    - Pro tier: 200 generations/month
    - Enterprise: unlimited (-1)
    Test generation with different source types (url, manual, csv).
    Test LLM generation by mocking ``app.services.llm_client.call_contentforge_llm``.
    Test A/B variant generation returns the requested number of variants.

For Project Managers:
    This is the revenue-driving feature. Each generation uses one monthly
    credit. The quality of generated content directly impacts user satisfaction.
    Real LLM generation produces higher-quality, more varied content than
    the mock generator.

For End Users:
    Content generation creates optimized product listings from your input.
    You can generate from a URL, paste product details, or upload CSV data.
    Choose from 10+ template styles to match your brand voice.
"""

import logging
import uuid
from datetime import datetime, date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.plans import PLAN_LIMITS
from app.models.generation import GeneratedContent, GenerationJob
from app.models.image_job import ImageJob
from app.models.template import Template
from app.models.user import User
from app.services.template_service import (
    DEFAULT_TEMPLATE_NAME,
    get_template,
)

logger = logging.getLogger(__name__)


async def count_monthly_generations(db: AsyncSession, user_id: uuid.UUID) -> int:
    """
    Count how many generation jobs the user has created this billing month.

    The billing month is defined as the 1st of the current month through
    the 1st of the next month (UTC).

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Number of generation jobs created in the current billing month.
    """
    today = date.today()
    period_start = datetime(today.year, today.month, 1)

    result = await db.execute(
        select(func.count(GenerationJob.id)).where(
            GenerationJob.user_id == user_id,
            GenerationJob.created_at >= period_start,
        )
    )
    return result.scalar() or 0


async def count_monthly_images(db: AsyncSession, user_id: uuid.UUID) -> int:
    """
    Count how many image jobs the user has created this billing month.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Number of image jobs created in the current billing month.
    """
    today = date.today()
    period_start = datetime(today.year, today.month, 1)

    result = await db.execute(
        select(func.count(ImageJob.id))
        .join(GenerationJob, ImageJob.job_id == GenerationJob.id)
        .where(
            GenerationJob.user_id == user_id,
            ImageJob.created_at >= period_start,
        )
    )
    return result.scalar() or 0


async def create_generation_job(
    db: AsyncSession, user: User, data: dict
) -> GenerationJob:
    """
    Create a new content generation job after checking plan limits.

    Validates that the user has not exceeded their monthly generation quota.
    Creates the GenerationJob record with status "pending" and optionally
    creates ImageJob records for any provided image URLs.

    Args:
        db: Async database session.
        user: The authenticated user creating the job.
        data: Dict with source_url, source_type, source_data, template_id,
              content_types, and image_urls.

    Returns:
        The newly created GenerationJob.

    Raises:
        ValueError: If the user has exceeded their plan's generation limit.
    """
    # Check generation limit
    plan_limits = PLAN_LIMITS[user.plan]
    if plan_limits.max_items != -1:  # -1 = unlimited
        current_count = await count_monthly_generations(db, user.id)
        if current_count >= plan_limits.max_items:
            raise ValueError(
                f"Monthly generation limit reached ({plan_limits.max_items}). "
                "Upgrade your plan for more generations."
            )

    # Check image limit if images are requested
    image_urls = data.get("image_urls", [])
    if image_urls and plan_limits.max_secondary != -1:
        current_images = await count_monthly_images(db, user.id)
        if current_images + len(image_urls) > plan_limits.max_secondary:
            remaining = max(0, plan_limits.max_secondary - current_images)
            raise ValueError(
                f"Image limit would be exceeded. {remaining} images remaining this month."
            )

    # Determine source data
    source_data = data.get("source_data", {})
    source_url = data.get("source_url")
    source_type = data.get("source_type", "manual")

    # If URL provided, include it in source data
    if source_url and source_type == "url":
        source_data["url"] = source_url

    job = GenerationJob(
        user_id=user.id,
        source_url=source_url,
        source_type=source_type,
        source_data=source_data,
        template_id=data.get("template_id"),
        status="pending",
    )
    db.add(job)
    await db.flush()

    # Create image jobs if URLs are provided
    for url in image_urls:
        image_job = ImageJob(
            job_id=job.id,
            original_url=url,
            status="pending",
        )
        db.add(image_job)

    await db.flush()
    # Refresh to load relationships
    await db.refresh(job)
    return job


async def get_generation_jobs(
    db: AsyncSession, user_id: uuid.UUID, page: int = 1, per_page: int = 20
) -> dict:
    """
    Get a paginated list of generation jobs for a user.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        page: Page number (1-indexed).
        per_page: Number of items per page.

    Returns:
        Dict with items (list of GenerationJob), total, page, per_page.
    """
    # Count total
    count_result = await db.execute(
        select(func.count(GenerationJob.id)).where(
            GenerationJob.user_id == user_id
        )
    )
    total = count_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * per_page
    result = await db.execute(
        select(GenerationJob)
        .where(GenerationJob.user_id == user_id)
        .order_by(GenerationJob.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    items = list(result.scalars().all())

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


async def get_generation_job(
    db: AsyncSession, job_id: uuid.UUID
) -> GenerationJob | None:
    """
    Get a single generation job by ID, including content and image items.

    Args:
        db: Async database session.
        job_id: The job's UUID.

    Returns:
        The GenerationJob with relationships loaded, or None if not found.
    """
    result = await db.execute(
        select(GenerationJob).where(GenerationJob.id == job_id)
    )
    return result.scalar_one_or_none()


async def delete_generation_job(
    db: AsyncSession, job_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """
    Delete a generation job and all its content and image records.

    Only the owning user can delete their jobs.

    Args:
        db: Async database session.
        job_id: The job's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        True if deleted, False if not found or not owned.
    """
    result = await db.execute(
        select(GenerationJob).where(
            GenerationJob.id == job_id,
            GenerationJob.user_id == user_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        return False

    await db.delete(job)
    await db.flush()
    return True


async def update_generated_content(
    db: AsyncSession, content_id: uuid.UUID, user_id: uuid.UUID, new_content: str
) -> GeneratedContent | None:
    """
    Update the text of a generated content record.

    Verifies ownership via the parent job before allowing the edit.

    Args:
        db: Async database session.
        content_id: The content record UUID.
        user_id: The requesting user's UUID (for ownership check).
        new_content: The updated text content.

    Returns:
        The updated GeneratedContent, or None if not found or not owned.
    """
    result = await db.execute(
        select(GeneratedContent).where(GeneratedContent.id == content_id)
    )
    content = result.scalar_one_or_none()
    if not content:
        return None

    # Check ownership via job
    job_result = await db.execute(
        select(GenerationJob).where(
            GenerationJob.id == content.job_id,
            GenerationJob.user_id == user_id,
        )
    )
    if not job_result.scalar_one_or_none():
        return None

    content.content = new_content
    content.word_count = len(new_content.split())
    await db.flush()
    return content


def generate_mock_content(
    product_data: dict, content_type: str, tone: str = "professional", style: str = "detailed"
) -> str:
    """
    Generate mock AI content for a given content type and product data.

    This function produces realistic mock content without calling an actual
    AI API. It uses the product data to create contextually relevant text.
    Replace this with real AI calls (e.g., Claude API) in production.

    Args:
        product_data: Dict with product information (name, price, features, etc.).
        content_type: Type of content to generate — "title", "description",
            "meta_description", "keywords", or "bullet_points".
        tone: Writing tone from the template (professional, casual, etc.).
        style: Content structure from the template (concise, detailed, etc.).

    Returns:
        Generated text content as a string.
    """
    product_name = product_data.get("name", "Premium Product")
    product_price = product_data.get("price", "29.99")
    product_category = product_data.get("category", "Electronics")
    product_features = product_data.get("features", ["High Quality", "Durable", "Modern Design"])

    if isinstance(product_features, str):
        product_features = [f.strip() for f in product_features.split(",")]

    if content_type == "title":
        tone_prefixes = {
            "professional": f"{product_name} — Premium {product_category}",
            "casual": f"Check Out the Amazing {product_name}!",
            "luxury": f"Exquisite {product_name} | Luxury {product_category} Collection",
            "playful": f"Meet Your New Favorite: {product_name}",
            "technical": f"{product_name}: Advanced {product_category} Solution",
        }
        return tone_prefixes.get(tone, f"{product_name} — {product_category}")

    elif content_type == "description":
        features_text = ", ".join(product_features[:5]) if product_features else "premium quality"
        descriptions = {
            "professional": (
                f"Introducing the {product_name}, a meticulously crafted {product_category.lower()} "
                f"designed for discerning customers who demand excellence. Featuring {features_text}, "
                f"this product delivers outstanding performance and reliability. "
                f"Built with premium materials and precision engineering, the {product_name} "
                f"sets a new standard in its category. Whether for personal or professional use, "
                f"it provides the perfect balance of form and function. "
                f"Available now at ${product_price}."
            ),
            "casual": (
                f"Looking for an awesome {product_category.lower()}? The {product_name} has got you covered! "
                f"With {features_text}, it's everything you need and more. "
                f"We designed it to be super easy to use and built to last. "
                f"Grab yours today for just ${product_price} and see what all the hype is about!"
            ),
            "luxury": (
                f"Discover the artistry of the {product_name} — where impeccable craftsmanship meets "
                f"visionary design. Each piece in our {product_category.lower()} collection embodies "
                f"sophistication, featuring {features_text}. "
                f"Curated for those who appreciate the finer things, this masterwork represents "
                f"the pinnacle of {product_category.lower()} excellence. Investment: ${product_price}."
            ),
        }
        return descriptions.get(tone, descriptions["professional"])

    elif content_type == "meta_description":
        return (
            f"Shop the {product_name} — {product_category.lower()} featuring "
            f"{', '.join(product_features[:3]) if product_features else 'top quality'}. "
            f"Starting at ${product_price}. Free shipping available."
        )[:160]

    elif content_type == "keywords":
        base_keywords = [
            product_name.lower(),
            product_category.lower(),
            f"buy {product_name.lower()}",
            f"best {product_category.lower()}",
            f"{product_category.lower()} online",
        ]
        feature_keywords = [f.lower().strip() for f in product_features[:5]]
        all_keywords = base_keywords + feature_keywords
        return ", ".join(all_keywords[:10])

    elif content_type == "bullet_points":
        bullet_items = []
        if product_features:
            for feature in product_features[:5]:
                bullet_items.append(f"- {feature.strip()}")
        # Pad to at least 5 bullet points
        defaults = [
            f"- Premium {product_category.lower()} quality materials",
            "- Easy setup and intuitive operation",
            "- Backed by our satisfaction guarantee",
            "- Fast, free shipping on all orders",
            f"- Exceptional value at ${product_price}",
        ]
        while len(bullet_items) < 5:
            bullet_items.append(defaults[len(bullet_items)])
        return "\n".join(bullet_items[:7])

    elif content_type == "social_caption":
        return (
            f"Check out {product_name} — the {product_category.lower()} "
            f"everyone is talking about! "
            f"Features: {', '.join(product_features[:3]) if product_features else 'top quality'}. "
            f"Only ${product_price}! #shopnow #{product_category.lower().replace(' ', '')}"
        )

    return f"Generated {content_type} content for {product_name}"


def _build_product_prompt_vars(product_data: dict) -> dict[str, str]:
    """
    Extract and format product data into template placeholder values.

    Normalizes product features (list or comma-separated string) into a
    consistent comma-separated string for template interpolation.

    Args:
        product_data: Raw product data dict from the generation job.

    Returns:
        Dict with keys matching prompt template placeholders:
        product_name, product_price, product_category, product_features,
        product_description.
    """
    features = product_data.get("features", [])
    if isinstance(features, list):
        features_str = ", ".join(str(f) for f in features)
    else:
        features_str = str(features)

    return {
        "product_name": product_data.get("name", "Premium Product"),
        "product_price": str(product_data.get("price", "29.99")),
        "product_category": product_data.get("category", "General"),
        "product_features": features_str or "high quality, durable",
        "product_description": product_data.get("description", ""),
    }


async def generate_content(
    db: AsyncSession,
    user_id: uuid.UUID,
    product_data: dict,
    content_types: list[str],
    template_name: str = "",
) -> list[dict]:
    """
    Generate LLM-powered content for a product using the template system.

    Builds specialized prompts per content type from the template registry,
    calls the LLM Gateway, and returns structured content items. Falls back
    to mock generation if the LLM gateway is unavailable.

    Args:
        db: Async database session (for future template DB lookups).
        user_id: The requesting user's UUID (for LLM cost tracking).
        product_data: Product information dict (name, price, features, etc.).
        content_types: List of content types to generate.
        template_name: Prompt template style name (e.g., 'amazon_style').
            Falls back to DEFAULT_TEMPLATE_NAME if empty or not found.

    Returns:
        List of dicts, each with 'content_type', 'content' (text),
        'word_count', and 'version' (always 1).
    """
    from app.services.llm_client import call_contentforge_llm

    if not template_name:
        template_name = DEFAULT_TEMPLATE_NAME

    prompt_vars = _build_product_prompt_vars(product_data)
    results = []

    for ct in content_types:
        tmpl = get_template(template_name, ct)

        if tmpl:
            # Fill in the prompt template with product data
            user_prompt = tmpl.user_prompt_template.format(**prompt_vars)
            system_prompt = (
                f"{tmpl.system_prompt}\n\n"
                f"Output format: {tmpl.output_format}"
            )

            try:
                llm_response = await call_contentforge_llm(
                    prompt=user_prompt,
                    system=system_prompt,
                    user_id=str(user_id),
                    task_type="content_generation",
                    max_tokens=tmpl.max_tokens,
                    temperature=tmpl.temperature,
                )
                text = llm_response.get("content", "")
            except Exception as e:
                logger.warning(
                    "LLM gateway call failed for %s/%s, falling back to mock: %s",
                    template_name, ct, e,
                )
                text = generate_mock_content(product_data, ct)
        else:
            # No template found for this content type; use mock
            text = generate_mock_content(product_data, ct)

        results.append({
            "content_type": ct,
            "content": text,
            "word_count": len(text.split()),
            "version": 1,
        })

    return results


async def generate_ab_variants(
    db: AsyncSession,
    user_id: uuid.UUID,
    product_data: dict,
    content_type: str = "title",
    template_name: str = "",
    count: int = 3,
) -> list[str]:
    """
    Generate multiple A/B test variants of a single content type.

    Produces ``count`` distinct variants using slightly varied temperatures
    and prompts so each variant has a different character while maintaining
    the same template style.

    Args:
        db: Async database session.
        user_id: The requesting user's UUID (for LLM cost tracking).
        product_data: Product information dict.
        content_type: The content type to generate variants for (default 'title').
        template_name: Prompt template style name.
        count: Number of variants to generate (1-5, default 3).

    Returns:
        List of variant content strings. Length equals ``count``.
    """
    from app.services.llm_client import call_contentforge_llm

    if not template_name:
        template_name = DEFAULT_TEMPLATE_NAME

    prompt_vars = _build_product_prompt_vars(product_data)
    tmpl = get_template(template_name, content_type)

    variants = []
    for i in range(count):
        if tmpl:
            user_prompt = tmpl.user_prompt_template.format(**prompt_vars)
            system_prompt = (
                f"{tmpl.system_prompt}\n\n"
                f"Output format: {tmpl.output_format}\n\n"
                f"Generate variant {i + 1} of {count}. Make each variant "
                f"distinctly different in approach while maintaining the same "
                f"quality and style."
            )

            try:
                # Vary temperature slightly per variant for diversity
                temp = min(1.0, tmpl.temperature + (i * 0.1))
                llm_response = await call_contentforge_llm(
                    prompt=user_prompt,
                    system=system_prompt,
                    user_id=str(user_id),
                    task_type="ab_testing",
                    max_tokens=tmpl.max_tokens,
                    temperature=temp,
                )
                variants.append(llm_response.get("content", ""))
            except Exception as e:
                logger.warning(
                    "LLM failed for A/B variant %d: %s", i + 1, e,
                )
                # Fallback: generate mock with slight variation
                mock_text = generate_mock_content(product_data, content_type)
                variants.append(f"{mock_text} (variant {i + 1})")
        else:
            mock_text = generate_mock_content(product_data, content_type)
            variants.append(f"{mock_text} (variant {i + 1})")

    return variants


async def process_generation(
    db: AsyncSession, job_id: uuid.UUID
) -> GenerationJob | None:
    """
    Process a generation job: generate content for all requested types
    and process any associated images.

    This is called by the Celery task. It transitions the job through
    pending -> processing -> completed (or failed on error).

    Args:
        db: Async database session.
        job_id: The generation job UUID to process.

    Returns:
        The updated GenerationJob, or None if not found.
    """
    result = await db.execute(
        select(GenerationJob).where(GenerationJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        return None

    try:
        job.status = "processing"
        await db.flush()

        # Determine template settings
        tone = "professional"
        style = "detailed"
        content_types = ["title", "description", "meta_description", "keywords", "bullet_points"]

        if job.template_id:
            template_result = await db.execute(
                select(Template).where(Template.id == job.template_id)
            )
            template = template_result.scalar_one_or_none()
            if template:
                tone = template.tone
                style = template.style
                content_types = template.content_types

        # Use content_types from source_data if provided
        if "content_types" in job.source_data:
            content_types = job.source_data["content_types"]

        # Generate content for each type
        product_data = dict(job.source_data)
        for ct in content_types:
            text = generate_mock_content(product_data, ct, tone, style)
            content_record = GeneratedContent(
                job_id=job.id,
                content_type=ct,
                content=text,
                version=1,
                word_count=len(text.split()),
            )
            db.add(content_record)

        # Process images (mock)
        for image_job in job.image_items:
            image_job.status = "completed"
            image_job.optimized_url = image_job.original_url.replace(
                ".", "_optimized.", 1
            )
            image_job.format = "webp"
            image_job.width = 800
            image_job.height = 600
            image_job.size_bytes = 45_000  # Mock 45KB optimized size

        job.status = "completed"
        job.completed_at = datetime.now(tz=None)
        await db.flush()
        await db.refresh(job)
        return job

    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.now(tz=None)
        await db.flush()
        return job
