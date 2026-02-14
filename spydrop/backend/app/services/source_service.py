"""
Source matching service — find potential suppliers for competitor products.

Combines mock supplier matching with LLM-powered keyword extraction for
smarter product source identification. The LLM extracts product keywords
from titles and descriptions, which are then matched against known
supplier databases.

For Developers:
    Two main functions:
    - ``find_sources(db, product_id)`` — mock-based supplier matching
      (existing functionality, no LLM needed).
    - ``find_supplier_matches(db, user_id, product_title, product_description)``
      — LLM-powered keyword extraction + supplier matching.

    The LLM-powered path uses the centralized LLM Gateway via
    ``app.services.llm_client.call_llm`` to extract product keywords,
    then matches them against simulated supplier databases.

For QA Engineers:
    Test source finding via POST /api/v1/sources/{product_id}/find.
    Verify confidence scores are between 0 and 1, margins are calculated
    correctly, and existing matches are replaced on re-run.
    For LLM-powered matching, mock ``call_llm`` in tests.

For Project Managers:
    Source matching is a premium feature (Pro tier and above). The LLM
    integration improves match quality by understanding product semantics
    rather than just keyword matching.

For End Users:
    Find where competitors get their products and see potential profit
    margins. Use this to decide which products are worth selling.
"""

import json
import logging
import random
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competitor import CompetitorProduct
from app.models.source_match import SourceMatch

logger = logging.getLogger(__name__)

# Mock supplier data for generating realistic matches
_SUPPLIERS = [
    {"name": "AliExpress", "domain": "aliexpress.com"},
    {"name": "DHgate", "domain": "dhgate.com"},
    {"name": "1688", "domain": "1688.com"},
    {"name": "Made-in-China", "domain": "made-in-china.com"},
    {"name": "Global Sources", "domain": "globalsources.com"},
    {"name": "Alibaba", "domain": "alibaba.com"},
    {"name": "Banggood", "domain": "banggood.com"},
    {"name": "LightInTheBox", "domain": "lightinthebox.com"},
]

# Simulated supplier catalog for keyword-based matching
_SUPPLIER_CATALOG = [
    {"supplier": "AliExpress", "keywords": ["electronics", "gadget", "phone", "charger", "cable", "led", "smart", "wireless"], "base_domain": "aliexpress.com"},
    {"supplier": "DHgate", "keywords": ["fashion", "clothing", "shoes", "jewelry", "watch", "bag", "accessory"], "base_domain": "dhgate.com"},
    {"supplier": "1688", "keywords": ["bulk", "wholesale", "factory", "custom", "manufacturing", "raw"], "base_domain": "1688.com"},
    {"supplier": "Alibaba", "keywords": ["industrial", "machinery", "equipment", "tools", "hardware", "parts"], "base_domain": "alibaba.com"},
    {"supplier": "Banggood", "keywords": ["hobby", "drone", "rc", "outdoor", "camping", "sport", "fitness"], "base_domain": "banggood.com"},
    {"supplier": "Made-in-China", "keywords": ["home", "kitchen", "garden", "furniture", "appliance", "decor"], "base_domain": "made-in-china.com"},
    {"supplier": "Global Sources", "keywords": ["beauty", "health", "cosmetic", "skincare", "supplement"], "base_domain": "globalsources.com"},
    {"supplier": "LightInTheBox", "keywords": ["party", "wedding", "gift", "seasonal", "toy", "craft"], "base_domain": "lightinthebox.com"},
]


async def find_sources(
    db: AsyncSession, product_id: uuid.UUID
) -> list[SourceMatch]:
    """
    Find potential supplier sources for a competitor product.

    Generates mock source matches with realistic supplier data,
    confidence scores, and margin calculations. Existing matches
    for the product are cleared before generating new ones.

    Args:
        db: Async database session.
        product_id: The CompetitorProduct's UUID.

    Returns:
        List of newly created SourceMatch records.

    Raises:
        ValueError: If the product is not found.
    """
    # Load product
    result = await db.execute(
        select(CompetitorProduct).where(CompetitorProduct.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise ValueError("Product not found")

    # Clear existing matches
    existing = await db.execute(
        select(SourceMatch).where(
            SourceMatch.competitor_product_id == product_id
        )
    )
    for match in existing.scalars().all():
        await db.delete(match)

    # Generate 1-4 mock matches
    num_matches = random.randint(1, 4)
    selected_suppliers = random.sample(
        _SUPPLIERS, min(num_matches, len(_SUPPLIERS))
    )

    matches: list[SourceMatch] = []
    competitor_price = product.price or 0.0

    for supplier in selected_suppliers:
        # Generate a cost that's 20-70% of the competitor price
        if competitor_price > 0:
            cost_ratio = random.uniform(0.20, 0.70)
            cost = round(competitor_price * cost_ratio, 2)
            margin = round(
                ((competitor_price - cost) / competitor_price) * 100, 1
            )
        else:
            cost = round(random.uniform(2.0, 50.0), 2)
            margin = None

        # Generate confidence score (higher for well-known suppliers)
        base_confidence = random.uniform(0.55, 0.95)
        confidence = round(base_confidence, 2)

        # Generate a plausible product URL slug
        slug = product.title.lower().replace(" ", "-")[:50]
        product_id_str = random.randint(10000, 99999)

        match = SourceMatch(
            competitor_product_id=product.id,
            supplier=supplier["name"],
            supplier_url=(
                f"https://{supplier['domain']}/item/{slug}-{product_id_str}.html"
            ),
            cost=cost,
            currency=product.currency,
            confidence_score=confidence,
            margin_percent=margin,
        )
        db.add(match)
        matches.append(match)

    await db.flush()
    return matches


async def find_supplier_matches(
    db: AsyncSession,
    user_id: uuid.UUID,
    product_title: str,
    product_description: str = "",
) -> list[dict]:
    """
    Find supplier matches using LLM-powered keyword extraction.

    Uses the LLM Gateway to extract product keywords from the title and
    description, then matches those keywords against the simulated
    supplier catalog to produce ranked results with similarity scores.

    Args:
        db: Async database session (reserved for future DB-backed catalog).
        user_id: The requesting user's UUID (for LLM usage tracking).
        product_title: The product's title text.
        product_description: The product's description text (optional).

    Returns:
        List of supplier match dicts, ranked by similarity score, each containing:
            - supplier (str): Supplier name.
            - supplier_url (str): Estimated supplier listing URL.
            - similarity_score (float): Match confidence (0.0-1.0).
            - matched_keywords (list[str]): Keywords that matched.
            - estimated_cost_range (str): Estimated cost range string.
    """
    from app.services.llm_client import call_llm

    # Step 1: Extract keywords via LLM
    keywords = await _extract_keywords_via_llm(
        user_id=str(user_id),
        product_title=product_title,
        product_description=product_description,
    )

    # Step 2: Match keywords against supplier catalog
    matches = _match_against_catalog(keywords, product_title)

    # Step 3: Sort by similarity score (highest first)
    matches.sort(key=lambda m: m["similarity_score"], reverse=True)

    return matches


async def _extract_keywords_via_llm(
    user_id: str,
    product_title: str,
    product_description: str,
) -> list[str]:
    """
    Use the LLM Gateway to extract searchable keywords from a product.

    Asks the LLM to identify the core product category, material, and
    key features that would be useful for supplier database searching.

    Args:
        user_id: User ID for LLM usage tracking.
        product_title: Product title text.
        product_description: Product description text.

    Returns:
        List of extracted keyword strings. Falls back to basic word
        splitting if the LLM call fails.
    """
    from app.services.llm_client import call_llm

    system_prompt = (
        "You are a product sourcing expert. Extract the most important "
        "search keywords from the product information provided. Return "
        "a JSON array of 3-8 lowercase keywords that would help find "
        "this product on wholesale supplier platforms like AliExpress, "
        "Alibaba, or DHgate. Focus on: product type, material, key "
        "features, and category. Return ONLY the JSON array."
    )

    prompt = f"Product title: {product_title}"
    if product_description:
        prompt += f"\nProduct description: {product_description[:500]}"

    result = await call_llm(
        prompt=prompt,
        system=system_prompt,
        user_id=user_id,
        task_type="source_finding",
        max_tokens=200,
        temperature=0.3,
        json_mode=True,
    )

    if result.get("error"):
        logger.warning(
            "LLM keyword extraction failed, using fallback: %s", result["error"]
        )
        return _fallback_keyword_extraction(product_title, product_description)

    # Parse the LLM response
    content = result.get("content", "")
    try:
        keywords = json.loads(content)
        if isinstance(keywords, list):
            return [str(k).lower().strip() for k in keywords if k]
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse LLM keywords response: %s", content[:200])

    return _fallback_keyword_extraction(product_title, product_description)


def _fallback_keyword_extraction(title: str, description: str = "") -> list[str]:
    """
    Extract keywords using simple word splitting as a fallback.

    Removes common stop words and returns unique lowercase words.

    Args:
        title: Product title text.
        description: Product description text.

    Returns:
        List of keyword strings.
    """
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "can", "shall",
        "for", "and", "nor", "but", "or", "yet", "so", "at", "by",
        "from", "in", "of", "on", "to", "with", "up", "out", "off",
        "over", "under", "again", "further", "then", "once", "all",
        "each", "every", "both", "few", "more", "most", "other",
        "some", "such", "no", "not", "only", "own", "same", "than",
        "too", "very", "just",
    }

    text = f"{title} {description}".lower()
    words = [w.strip(".,;:!?\"'()[]{}") for w in text.split()]
    keywords = [w for w in words if w and len(w) > 2 and w not in stop_words]
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique[:8]


def _match_against_catalog(
    keywords: list[str], product_title: str
) -> list[dict]:
    """
    Match extracted keywords against the simulated supplier catalog.

    Calculates a similarity score based on keyword overlap between the
    product keywords and each supplier's specialty keywords.

    Args:
        keywords: Extracted product keywords.
        product_title: Original product title for URL generation.

    Returns:
        List of supplier match dicts with similarity scores.
    """
    matches: list[dict] = []
    keyword_set = set(keywords)

    for catalog_entry in _SUPPLIER_CATALOG:
        supplier_keywords = set(catalog_entry["keywords"])
        overlap = keyword_set & supplier_keywords

        if not overlap:
            # Check for partial matches (keyword contained in supplier keyword or vice versa)
            partial_matches = []
            for kw in keywords:
                for skw in supplier_keywords:
                    if kw in skw or skw in kw:
                        partial_matches.append(kw)
                        break
            if not partial_matches:
                continue
            overlap_count = len(partial_matches) * 0.5  # partial matches count half
        else:
            overlap_count = len(overlap)

        # Calculate similarity score (0.0 to 1.0)
        max_possible = max(len(keyword_set), len(supplier_keywords), 1)
        similarity = round(min(overlap_count / max_possible + 0.3, 1.0), 2)

        slug = product_title.lower().replace(" ", "-")[:50]
        item_id = random.randint(10000, 99999)

        matches.append({
            "supplier": catalog_entry["supplier"],
            "supplier_url": f"https://{catalog_entry['base_domain']}/item/{slug}-{item_id}.html",
            "similarity_score": similarity,
            "matched_keywords": list(overlap) if isinstance(overlap, set) else keywords[:3],
            "estimated_cost_range": _estimate_cost_range(product_title),
        })

    # If no matches found, return top 2 generic matches
    if not matches:
        for entry in _SUPPLIER_CATALOG[:2]:
            slug = product_title.lower().replace(" ", "-")[:50]
            item_id = random.randint(10000, 99999)
            matches.append({
                "supplier": entry["supplier"],
                "supplier_url": f"https://{entry['base_domain']}/item/{slug}-{item_id}.html",
                "similarity_score": 0.3,
                "matched_keywords": keywords[:2] if keywords else [],
                "estimated_cost_range": _estimate_cost_range(product_title),
            })

    return matches


def _estimate_cost_range(product_title: str) -> str:
    """
    Estimate a plausible cost range based on the product type.

    Uses keyword heuristics to guess the product category and
    assign a reasonable wholesale price range.

    Args:
        product_title: The product title for category guessing.

    Returns:
        String like '$5-15' or '$20-50'.
    """
    title_lower = product_title.lower()
    if any(kw in title_lower for kw in ["phone", "tablet", "laptop", "computer"]):
        return "$50-200"
    if any(kw in title_lower for kw in ["jewelry", "watch", "ring", "necklace"]):
        return "$2-30"
    if any(kw in title_lower for kw in ["clothing", "shirt", "dress", "pants"]):
        return "$5-25"
    if any(kw in title_lower for kw in ["tool", "hardware", "equipment"]):
        return "$10-50"
    return "$5-30"


async def list_source_matches(
    db: AsyncSession,
    product_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[SourceMatch], int]:
    """
    List source matches for a product with pagination.

    Ordered by confidence score (highest first).

    Args:
        db: Async database session.
        product_id: The CompetitorProduct's UUID.
        page: Page number (1-based).
        per_page: Items per page.

    Returns:
        Tuple of (list of SourceMatch records, total count).
    """
    from sqlalchemy import func as sqlfunc

    count_result = await db.execute(
        select(sqlfunc.count(SourceMatch.id)).where(
            SourceMatch.competitor_product_id == product_id
        )
    )
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(SourceMatch)
        .where(SourceMatch.competitor_product_id == product_id)
        .order_by(SourceMatch.confidence_score.desc())
        .offset(offset)
        .limit(per_page)
    )
    matches = list(result.scalars().all())

    return matches, total
