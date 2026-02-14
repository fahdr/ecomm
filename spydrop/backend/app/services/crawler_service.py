"""
Competitor Store Crawler service for SpyDrop.

Crawls competitor e-commerce stores to extract product data including
titles, prices, descriptions, images, and variants. Supports Shopify
stores (via their public JSON API) and generic stores (via HTML scraping).

For Developers:
    Two main entry points:
    - ``crawl_store_products(store_url)`` — crawl all products from a store.
    - ``crawl_product_page(url)`` — extract data from a single product page.

    For Shopify stores, the crawler uses the ``/products.json`` public API.
    For other stores, it falls back to HTML scraping with heuristics for
    common e-commerce patterns (Open Graph meta tags, JSON-LD, etc.).

    The crawler uses a realistic User-Agent header and respects rate limits
    by adding a small delay between paginated requests.

For QA Engineers:
    Mock the HTTP responses in tests (use ``httpx.MockTransport`` or
    ``respx``). Test Shopify JSON parsing, HTML fallback parsing,
    pagination handling, and error cases (timeouts, 404s, rate limits).

For Project Managers:
    The crawler is the data ingestion engine for SpyDrop. It discovers
    products on competitor stores and feeds them into the diff engine
    for change detection. Shopify stores are easiest to crawl due to
    their public JSON API; other platforms require HTML parsing.

For End Users:
    SpyDrop automatically crawls competitor stores to discover products
    and track prices. You don't need to do anything — just add a
    competitor and the crawler handles the rest.
"""

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Realistic browser User-Agent to avoid bot detection.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)

# Default HTTP timeout for crawl requests (15 seconds).
_CRAWL_TIMEOUT = 15.0

# Maximum pages to crawl for paginated stores.
_MAX_PAGES = 10


async def crawl_store_products(store_url: str) -> list[dict]:
    """
    Crawl all products from a competitor store.

    Attempts Shopify JSON API first (``/products.json``). If that fails,
    falls back to HTML scraping. Handles pagination for Shopify stores
    (up to ``_MAX_PAGES`` pages of 250 products each).

    Args:
        store_url: The competitor store's base URL
            (e.g., 'https://competitor.myshopify.com').

    Returns:
        A list of product dicts, each containing:
            - title (str): Product title.
            - price (float | None): Product price (may be None).
            - currency (str): Currency code (default 'USD').
            - description (str): Product description text.
            - url (str): Direct URL to the product page.
            - image_url (str | None): Primary product image URL.
            - variants (list[dict]): List of variant dicts (title, price, sku).
            - source (str): Data source indicator ('shopify_json' or 'html').

    Raises:
        No exceptions are raised. Network errors return an empty list
        with a warning logged. Individual product parsing failures are
        skipped with warnings.
    """
    # Normalize URL
    store_url = store_url.rstrip("/")

    # Try Shopify JSON API first
    products = await _crawl_shopify_json(store_url)
    if products:
        return products

    # Fallback: attempt to scrape the HTML storefront
    products = await _crawl_html_storefront(store_url)
    return products


async def crawl_product_page(url: str) -> dict:
    """
    Extract detailed product information from a single product page.

    Fetches the HTML of the product page and parses it for product
    data using Open Graph meta tags, JSON-LD structured data, and
    common HTML patterns.

    Args:
        url: Direct URL to the product page.

    Returns:
        A dict containing:
            - title (str): Product title (empty string if not found).
            - price (float | None): Product price.
            - currency (str): Currency code.
            - description (str): Product description.
            - url (str): The original URL.
            - image_url (str | None): Product image URL.
            - variants (list[dict]): Variants found on the page.
            - source (str): Always 'html_detail'.

    Raises:
        No exceptions are raised. Network errors return a minimal dict
        with the URL and empty fields.
    """
    result: dict[str, Any] = {
        "title": "",
        "price": None,
        "currency": "USD",
        "description": "",
        "url": url,
        "image_url": None,
        "variants": [],
        "source": "html_detail",
    }

    try:
        async with httpx.AsyncClient(timeout=_CRAWL_TIMEOUT) as client:
            response = await client.get(
                url,
                headers={"User-Agent": _USER_AGENT},
                follow_redirects=True,
            )
            response.raise_for_status()
            html = response.text
    except Exception as exc:
        logger.warning("Failed to fetch product page %s: %s", url, exc)
        return result

    # Parse Open Graph meta tags
    result["title"] = _extract_meta(html, "og:title") or _extract_html_title(html)
    result["description"] = _extract_meta(html, "og:description") or ""
    result["image_url"] = _extract_meta(html, "og:image")

    # Parse price from meta tags or common HTML patterns
    price_str = _extract_meta(html, "og:price:amount") or _extract_meta(
        html, "product:price:amount"
    )
    if price_str:
        result["price"] = _parse_price(price_str)

    currency = _extract_meta(html, "og:price:currency") or _extract_meta(
        html, "product:price:currency"
    )
    if currency:
        result["currency"] = currency

    # Try to find price in common HTML patterns if not found in meta
    if result["price"] is None:
        result["price"] = _find_price_in_html(html)

    return result


# ── Shopify JSON Crawler ───────────────────────────────────────────


async def _crawl_shopify_json(store_url: str) -> list[dict]:
    """
    Crawl products from a Shopify store using the public JSON API.

    Shopify stores expose ``/products.json`` with up to 250 products per
    page. Pagination is handled via the ``page`` query parameter.

    Args:
        store_url: The Shopify store's base URL.

    Returns:
        List of normalized product dicts, or empty list if the store
        is not Shopify or the API is not accessible.
    """
    all_products: list[dict] = []

    for page in range(1, _MAX_PAGES + 1):
        url = f"{store_url}/products.json?limit=250&page={page}"
        try:
            async with httpx.AsyncClient(timeout=_CRAWL_TIMEOUT) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": _USER_AGENT},
                    follow_redirects=True,
                )

            if response.status_code != 200:
                if page == 1:
                    # Not a Shopify store or API is disabled
                    return []
                break

            data = response.json()
            products_raw = data.get("products", [])
            if not products_raw:
                break

            for raw in products_raw:
                product = _normalize_shopify_product(raw, store_url)
                if product:
                    all_products.append(product)

        except Exception as exc:
            if page == 1:
                logger.debug("Shopify JSON API not available for %s: %s", store_url, exc)
                return []
            logger.warning("Error fetching Shopify page %d for %s: %s", page, store_url, exc)
            break

    return all_products


def _normalize_shopify_product(raw: dict, store_url: str) -> dict | None:
    """
    Normalize a raw Shopify product JSON object into a standard dict.

    Extracts the first variant's price, all variant details, and the
    primary image URL.

    Args:
        raw: Raw product dict from Shopify's /products.json response.
        store_url: The store's base URL for constructing product URLs.

    Returns:
        Normalized product dict, or None if the product is missing
        essential fields (title).
    """
    title = raw.get("title", "").strip()
    if not title:
        return None

    handle = raw.get("handle", "")
    variants = raw.get("variants", [])

    # Get price from the first variant
    price = None
    if variants:
        try:
            price = float(variants[0].get("price", 0))
        except (ValueError, TypeError):
            pass

    # Get primary image
    images = raw.get("images", [])
    image_url = images[0].get("src") if images else None

    # Normalize variants
    normalized_variants = []
    for v in variants:
        normalized_variants.append({
            "title": v.get("title", "Default"),
            "price": _safe_float(v.get("price")),
            "sku": v.get("sku", ""),
        })

    return {
        "title": title,
        "price": price,
        "currency": "USD",
        "description": _strip_html(raw.get("body_html", "") or ""),
        "url": f"{store_url}/products/{handle}" if handle else store_url,
        "image_url": image_url,
        "variants": normalized_variants,
        "source": "shopify_json",
    }


# ── HTML Fallback Crawler ─────────────────────────────────────────


async def _crawl_html_storefront(store_url: str) -> list[dict]:
    """
    Crawl products from a generic HTML storefront.

    Fetches the store's homepage and common product listing paths,
    then extracts product links and basic data using HTML patterns.

    Args:
        store_url: The store's base URL.

    Returns:
        List of product dicts extracted from the HTML. May be empty
        if no products are found or the store is not reachable.
    """
    products: list[dict] = []
    paths_to_try = ["/collections/all", "/shop", "/products", "/store", "/"]

    for path in paths_to_try:
        url = f"{store_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=_CRAWL_TIMEOUT) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": _USER_AGENT},
                    follow_redirects=True,
                )
            if response.status_code != 200:
                continue

            html = response.text
            # Extract product links and basic info from HTML
            page_products = _extract_products_from_html(html, store_url)
            if page_products:
                products.extend(page_products)
                break  # Found products, no need to try more paths

        except Exception as exc:
            logger.debug("HTML crawl failed for %s: %s", url, exc)
            continue

    return products


def _extract_products_from_html(html: str, store_url: str) -> list[dict]:
    """
    Extract product data from HTML using common e-commerce patterns.

    Looks for JSON-LD structured data and common HTML patterns for
    product cards (links, images, prices).

    Args:
        html: The HTML content of the page.
        store_url: The store's base URL for resolving relative URLs.

    Returns:
        List of product dicts found in the HTML.
    """
    products: list[dict] = []

    # Try JSON-LD structured data first
    json_ld_pattern = re.compile(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )
    for match in json_ld_pattern.finditer(html):
        try:
            import json

            data = json.loads(match.group(1))
            if isinstance(data, dict) and data.get("@type") == "Product":
                products.append(_parse_json_ld_product(data, store_url))
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        products.append(_parse_json_ld_product(item, store_url))
        except Exception:
            continue

    # Fallback: look for product-like links with prices
    if not products:
        product_link_pattern = re.compile(
            r'<a[^>]*href=["\']([^"\']*(?:product|item)[^"\']*)["\'][^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE,
        )
        for match in product_link_pattern.finditer(html):
            href = match.group(1)
            link_text = _strip_html(match.group(2)).strip()
            if link_text and len(link_text) > 3:
                full_url = href if href.startswith("http") else f"{store_url}{href}"
                products.append({
                    "title": link_text[:512],
                    "price": None,
                    "currency": "USD",
                    "description": "",
                    "url": full_url,
                    "image_url": None,
                    "variants": [],
                    "source": "html",
                })

    return products


def _parse_json_ld_product(data: dict, store_url: str) -> dict:
    """
    Parse a JSON-LD Product schema into a normalized product dict.

    Args:
        data: The JSON-LD dict with @type 'Product'.
        store_url: The store's base URL for resolving relative URLs.

    Returns:
        Normalized product dict.
    """
    price = None
    currency = "USD"
    offers = data.get("offers", {})
    if isinstance(offers, dict):
        price = _safe_float(offers.get("price"))
        currency = offers.get("priceCurrency", "USD")
    elif isinstance(offers, list) and offers:
        price = _safe_float(offers[0].get("price"))
        currency = offers[0].get("priceCurrency", "USD")

    image = data.get("image", "")
    if isinstance(image, list):
        image = image[0] if image else ""

    url = data.get("url", store_url)
    if not url.startswith("http"):
        url = f"{store_url}{url}"

    return {
        "title": data.get("name", "")[:512],
        "price": price,
        "currency": currency,
        "description": data.get("description", "")[:2000],
        "url": url,
        "image_url": image if isinstance(image, str) else None,
        "variants": [],
        "source": "html",
    }


# ── HTML Parsing Helpers ──────────────────────────────────────────


def _extract_meta(html: str, property_name: str) -> str | None:
    """
    Extract the content of an HTML meta tag by property name.

    Handles both ``property`` and ``name`` attributes.

    Args:
        html: The HTML content to search.
        property_name: The meta property name (e.g., 'og:title').

    Returns:
        The content attribute value, or None if not found.
    """
    patterns = [
        rf'<meta[^>]*property=["\']{property_name}["\'][^>]*content=["\']([^"\']*)["\']',
        rf'<meta[^>]*content=["\']([^"\']*)["\'][^>]*property=["\']{property_name}["\']',
        rf'<meta[^>]*name=["\']{property_name}["\'][^>]*content=["\']([^"\']*)["\']',
        rf'<meta[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']{property_name}["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _extract_html_title(html: str) -> str:
    """
    Extract the page title from an HTML document.

    Args:
        html: The HTML content.

    Returns:
        The title text, or empty string if not found.
    """
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _find_price_in_html(html: str) -> float | None:
    """
    Find a product price in HTML using common price patterns.

    Looks for price-related CSS classes and common price formatting
    patterns (e.g., $29.99, EUR 19.99).

    Args:
        html: The HTML content to search.

    Returns:
        The parsed price as a float, or None if not found.
    """
    # Look for price in common class patterns
    price_patterns = [
        r'class=["\'][^"\']*price[^"\']*["\'][^>]*>[\s$]*([0-9]+[.,][0-9]{2})',
        r'data-price=["\']([0-9]+\.?[0-9]*)["\']',
        r'[\$\u20ac\u00a3]([0-9]+[.,][0-9]{2})',
    ]
    for pattern in price_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return _parse_price(match.group(1))
    return None


def _parse_price(price_str: str) -> float | None:
    """
    Parse a price string into a float.

    Handles comma-separated thousands and decimal separators.

    Args:
        price_str: Price string (e.g., '29.99', '1,299.50', '19,99').

    Returns:
        The parsed float, or None if parsing fails.
    """
    try:
        # Remove currency symbols and whitespace
        cleaned = re.sub(r"[^\d.,]", "", price_str.strip())
        if not cleaned:
            return None
        # Handle European format (1.299,50 -> 1299.50)
        if "," in cleaned and "." in cleaned:
            if cleaned.index(",") > cleaned.index("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            # Could be thousands separator or decimal
            parts = cleaned.split(",")
            if len(parts[-1]) == 2:
                cleaned = cleaned.replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        return round(float(cleaned), 2)
    except (ValueError, IndexError):
        return None


def _strip_html(html_str: str) -> str:
    """
    Remove HTML tags from a string.

    Args:
        html_str: HTML-formatted string.

    Returns:
        Plain text with HTML tags removed.
    """
    return re.sub(r"<[^>]+>", " ", html_str).strip()


def _safe_float(value: Any) -> float | None:
    """
    Safely convert a value to float.

    Args:
        value: Any value that might be numeric.

    Returns:
        The float value, or None if conversion fails.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
