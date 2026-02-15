# py-suppliers Developer Documentation

## Package Overview

**Name:** `ecomm-suppliers` (import as `ecomm_suppliers`)
**Version:** 0.1.0
**Location:** `/workspaces/ecomm/packages/py-suppliers/`
**Python:** >= 3.11

`ecomm-suppliers` is a shared library that provides a unified, supplier-agnostic interface for integrating with third-party dropshipping suppliers. It normalizes product data from multiple platforms (AliExpress, CJDropship) into a common Pydantic model layer, and provides utilities for pricing, slug generation, and image processing.

---

## Architecture

```
ecomm_suppliers/
  __init__.py          # Public API exports, __version__, __all__
  models.py            # Pydantic models: SupplierProduct, SupplierVariant, ShippingInfo, SupplierRating, ProductSearchResult
  base.py              # BaseSupplierClient ABC, SupplierError exception
  aliexpress.py        # AliExpress client (demo data: 24 products, real API stubs)
  cjdropship.py        # CJDropship client (demo data: 18 products, real API stubs)
  normalizer.py        # ProductNormalizer: markup, psychological pricing, compare-at, slug generation
  image_service.py     # ImageService: download, optimize, thumbnail, dimensions, format detection
  factory.py           # SupplierFactory: create clients by name, registry pattern
```

### Dependency Graph

```
factory.py ──> aliexpress.py ──> base.py ──> models.py
           ──> cjdropship.py ──> base.py ──> models.py
normalizer.py  (standalone, no internal imports)
image_service.py ──> base.py (for SupplierError only)
```

### External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `httpx` | >= 0.27.0 | Async HTTP client for supplier API calls and image downloads |
| `pydantic` | >= 2.5.0 | Data validation, serialization, frozen immutable models |
| `beautifulsoup4` | >= 4.12.0 | HTML parsing for product descriptions |
| `Pillow` | >= 10.2.0 | Image processing: resize, optimize, thumbnail, format detection |

Dev-only dependencies: `pytest >= 8.0.0`, `pytest-asyncio >= 0.23.0`.

---

## Installation

```bash
# Editable install (from monorepo root)
pip install -e packages/py-suppliers

# With dev/test dependencies
pip install -e "packages/py-suppliers[dev]"
```

---

## Quick Start

```python
from ecomm_suppliers import SupplierFactory

# Demo mode (no API key) -- returns deterministic mock data
async with SupplierFactory.create("aliexpress") as client:
    results = await client.search_products("wireless earbuds")
    for product in results.products:
        print(f"{product.title}: ${product.price}")

# With a real API key
client = SupplierFactory.create("cjdropship", api_key="your-cj-token")
try:
    product = await client.get_product("CJ-ELEC-2891734")
finally:
    await client.close()
```

---

## Core Design Decisions

### 1. Decimal for All Money Values

All prices (`SupplierProduct.price`, `SupplierVariant.price`, `ShippingInfo.shipping_cost`) use `Decimal` from Python's `decimal` module. This avoids floating-point rounding errors that arise with `float` arithmetic when computing markups, discounts, and totals.

The `ProductNormalizer` methods accept and return `Decimal` exclusively. Conversion from string to `Decimal` happens at the boundary (demo data dicts use string prices like `"18.74"` that are passed to `Decimal()`).

### 2. Demo Mode by Default

When a supplier client is instantiated without an `api_key` argument, it operates in **demo mode** (`is_demo_mode == True`). Demo mode returns a fixed, deterministic set of mock products:

- **AliExpress:** 24 products across 4 categories (electronics, fashion, home, beauty), 6 per category.
- **CJDropship:** 18 products across 4 categories (4 electronics, 4 fashion, 5 home, 5 beauty).

Demo data is built by `_build_demo_products()` functions in each client module. Product IDs are stable strings, enabling deterministic assertions in tests.

### 3. Frozen Pydantic Models

All data models (`SupplierProduct`, `SupplierVariant`, `ShippingInfo`, `SupplierRating`) use `ConfigDict(frozen=True)`, making instances immutable after creation. This prevents accidental mutation and makes models safe to pass across async boundaries.

`ProductSearchResult` is **not** frozen, as it is a container returned from search operations.

### 4. Single Exception Type

`SupplierError` is the only exception type raised by supplier operations. It wraps:
- HTTP errors (status codes, timeouts, connection failures)
- Authentication failures
- Rate limiting
- Parse/validation errors
- "Not found" lookups (with `status_code=404`)

This gives consumers a single `except SupplierError` catch for all supplier failure modes.

### 5. Async Context Manager Support

All supplier clients implement `__aenter__` / `__aexit__` via `BaseSupplierClient`. This ensures the internal `httpx.AsyncClient` is properly closed:

```python
async with SupplierFactory.create("aliexpress") as client:
    # client._client is created lazily on first API call
    results = await client.search_products("earbuds")
# client.close() called automatically here
```

### 6. Factory Pattern with Runtime Registration

`SupplierFactory` maintains a `_SUPPLIER_REGISTRY` dict mapping lowercase type strings to client classes. New suppliers can be added either by:
- Editing `_SUPPLIER_REGISTRY` in `factory.py`, or
- Calling `SupplierFactory.register("newsupplier", NewSupplierClient)` at runtime.

The `register()` method validates that the class is a proper `BaseSupplierClient` subclass.

---

## Module Reference

### `models.py` -- Data Models

#### `SupplierVariant`

A single purchasable variant of a supplier product (e.g., a color/size combination).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | required | Human-readable label, e.g. `"Color: Red, Size: L"` |
| `sku` | `str \| None` | `None` | Stock-keeping unit on the supplier platform |
| `price` | `Decimal` | required | Variant price in the product's currency |
| `stock` | `int \| None` | `None` | Units in stock, or None if unknown |
| `image_url` | `str \| None` | `None` | Variant-specific image URL |
| `attributes` | `dict[str, str]` | `{}` | Structured key-value pairs, e.g. `{"color": "Red", "size": "L"}` |

Frozen: Yes.

#### `ShippingInfo`

Estimated shipping details for a product.

| Field | Type | Description |
|-------|------|-------------|
| `estimated_days_min` | `int` | Minimum delivery days |
| `estimated_days_max` | `int` | Maximum delivery days |
| `shipping_cost` | `Decimal` | Cost in USD |
| `shipping_method` | `str` | Method name, e.g. `"ePacket"`, `"CJ Packet"` |
| `ships_from` | `str` | Origin country/warehouse, e.g. `"CN"`, `"US"` |

Frozen: Yes.

#### `SupplierRating`

Aggregated customer rating.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `average` | `float` | required | Average star rating (0.0 -- 5.0) |
| `count` | `int` | required | Total number of ratings |
| `positive_percent` | `float \| None` | `None` | Percentage of positive reviews |

Frozen: Yes.

#### `SupplierProduct`

The canonical normalized product model. All supplier clients must produce instances of this model.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `source` | `str` | required | Supplier identifier (`"aliexpress"`, `"cjdropship"`) |
| `source_id` | `str` | required | Product ID on the supplier platform |
| `source_url` | `str` | required | Direct URL to the product page |
| `title` | `str` | required | Product title |
| `description` | `str` | required | Full description (may contain HTML) |
| `price` | `Decimal` | required | Supplier cost in USD |
| `currency` | `str` | `"USD"` | ISO 4217 currency code |
| `images` | `list[str]` | `[]` | Product image URLs |
| `variants` | `list[SupplierVariant]` | `[]` | Product variants |
| `shipping_info` | `ShippingInfo \| None` | `None` | Shipping details |
| `ratings` | `SupplierRating \| None` | `None` | Customer ratings |
| `raw_data` | `dict[str, Any]` | `{}` | Original supplier API response |
| `fetched_at` | `datetime` | `now(UTC)` | Timestamp of data retrieval |

Frozen: Yes.

#### `ProductSearchResult`

Paginated container for search results.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `products` | `list[SupplierProduct]` | `[]` | Products for the current page |
| `total_count` | `int` | `0` | Total matching products across all pages |
| `page` | `int` | `1` | Current page number (1-indexed) |
| `page_size` | `int` | `20` | Products per page |

Frozen: No.

---

### `base.py` -- Abstract Base Class

#### `SupplierError`

```python
class SupplierError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, supplier: str = ""):
```

- `message` -- Human-readable error description.
- `status_code` -- HTTP status code (if applicable), else `None`.
- `supplier` -- Supplier identifier string (e.g. `"aliexpress"`, `"cjdropship"`, `"image_service"`).

#### `BaseSupplierClient`

Abstract base class. Constructor takes an optional `api_key: str | None`.

| Property/Method | Signature | Description |
|-----------------|-----------|-------------|
| `is_demo_mode` | `-> bool` | `True` if no API key was provided |
| `search_products` | `(query: str, page: int = 1, page_size: int = 20) -> ProductSearchResult` | Search products (abstract) |
| `get_product` | `(product_id: str) -> SupplierProduct` | Fetch single product by ID (abstract) |
| `get_product_by_url` | `(url: str) -> SupplierProduct` | Fetch product by URL (abstract) |
| `close` | `() -> None` | Release resources (default no-op) |
| `__aenter__` | `-> BaseSupplierClient` | Async context manager entry |
| `__aexit__` | `(...)` -> None | Calls `close()` on exit |

---

### `aliexpress.py` -- AliExpress Client

**API Base URL:** `https://api-sg.aliexpress.com/sync`

**URL Extraction Pattern:** `/item/(\d+)\.html`, `/i/(\d+)\.html`, `product/(\d+)`

**Demo Data:** 24 products across 4 categories (electronics, fashion, home, beauty), 6 per category. Product IDs are numeric strings like `"1005006841237901"`.

**Key implementation details:**

- `_extract_product_id(url)` -- Extracts numeric product ID from AliExpress URLs using regex. Raises `SupplierError` if no match.
- `_build_demo_products()` -- Returns a list of 24 product dicts with realistic titles, descriptions, prices (as strings), images, variants, shipping, and ratings.
- `_dict_to_product(data)` -- Converts a demo dict to a `SupplierProduct` model, creating `SupplierVariant`, `ShippingInfo`, and `SupplierRating` sub-models.
- Real API mode sends POST requests to `/aliexpress.affiliate.product.query` (search) and `/aliexpress.affiliate.product.detail` (detail). Response parsing is stubbed with `# TODO: real API` markers.
- HTTP client is lazily created via `_get_client()` with 30-second timeout.
- `close()` calls `httpx.AsyncClient.aclose()`.

**Demo search:** Case-insensitive substring match against `title`, `description`, and `category` fields. Supports pagination via `page` and `page_size` parameters.

---

### `cjdropship.py` -- CJDropship Client

**API Base URL:** `https://developers.cjdropshipping.com/api/2.0`

**URL Extraction Pattern:** `/product(?:_detail)?/(?:p-)?([A-Za-z0-9-]+)`

**Demo Data:** 18 products across 4 categories (4 electronics, 4 fashion, 5 home, 5 beauty). Product IDs use the format `CJ-{CATEGORY}-{NUMBER}` (e.g. `"CJ-ELEC-2891734"`).

**Key differences from AliExpress:**
- CJDropship ships from US warehouses (shipping min 3-7 days vs. 10-25 for AliExpress).
- API auth uses `CJ-Access-Token` header instead of `app_key` in request body.
- Real API search uses GET `/product/list` with query params; detail uses GET `/product/query`.
- Page size max is 200 (vs. 50 for AliExpress).

---

### `normalizer.py` -- ProductNormalizer

All methods are `@staticmethod` -- the class is purely organizational.

#### `calculate_markup(cost: Decimal, markup_percent: float) -> Decimal`

Applies percentage markup: `cost * (1 + markup_percent / 100)`. Result rounded to 2 decimal places with `ROUND_HALF_UP`.

- Raises `ValueError` if `cost < 0` or `markup_percent < 0`.
- Uses `Decimal(str(...))` conversion to avoid float precision issues in the multiplier.

#### `apply_psychological_pricing(price: Decimal) -> Decimal`

Charm pricing rules:
- **Under $10:** Floor to nearest dollar minus $0.01 (e.g. `$8.42 -> $7.99`). Minimum result is `$0.99`.
- **$10 -- $99:** Floor to nearest dollar minus $0.03 (e.g. `$30.12 -> $29.97`). Minimum result is `$0.97`.
- **$100+:** Floor to nearest dollar minus $0.01, never exceeding input (e.g. `$149.50 -> $149.99` is wrong per code, actual: `$149.50 -> $148.99`). If the candidate exceeds the original price, subtracts an additional $1.00.
- Returns `price` unchanged if `price <= 0`.

#### `calculate_compare_at_price(retail: Decimal, discount_pct: float) -> Decimal`

Computes a "was" price: `retail / (1 - discount_pct / 100)`. Raises `ValueError` if `discount_pct` is not strictly between 0 and 100.

#### `generate_slug(title: str) -> str`

1. NFKD unicode normalization, then ASCII encoding (strips accents).
2. Lowercase.
3. Replace non-alphanumeric characters with hyphens.
4. Collapse consecutive hyphens, strip leading/trailing.
5. Truncate to 120 characters at a word (hyphen) boundary.

---

### `image_service.py` -- ImageService

All methods are `@staticmethod`. `download_image` is async; all others are synchronous.

#### `download_image(url: str, timeout: float = 30.0) -> bytes`

- Creates a fresh `httpx.AsyncClient` per call (with `follow_redirects=True`).
- Validates response content-type starts with `image/`.
- Raises `SupplierError` on HTTP errors (status >= 400), non-image content types, or `httpx.HTTPError`.

#### `optimize_image(data: bytes, max_width: int = 1200, quality: int = 85, output_format: str = "JPEG") -> bytes`

- Opens image from bytes via `Pillow`.
- Converts RGBA/P/LA modes to RGB (composites onto white background for transparency).
- Resizes if width exceeds `max_width` (preserving aspect ratio, using `LANCZOS` filter).
- Saves with `optimize=True` flag.

#### `create_thumbnail(data: bytes, size: tuple[int, int] = (300, 300), output_format: str = "JPEG", quality: int = 85) -> bytes`

- Same mode conversion as `optimize_image`.
- Uses `Pillow.thumbnail()` which preserves aspect ratio and does not upscale.

#### `get_image_dimensions(data: bytes) -> tuple[int, int]`

Returns `(width, height)` in pixels. Raises `SupplierError` on invalid data.

#### `get_image_format(data: bytes) -> str | None`

Returns format string (`"JPEG"`, `"PNG"`, `"WEBP"`, etc.) or `None` if undetectable.

---

### `factory.py` -- SupplierFactory

#### Registry

```python
_SUPPLIER_REGISTRY: dict[str, type[BaseSupplierClient]] = {
    "aliexpress": AliExpressClient,
    "cjdropship": CJDropshipClient,
}
```

#### `create(supplier_type: str, **kwargs) -> BaseSupplierClient`

Looks up `supplier_type.lower().strip()` in the registry. Passes `**kwargs` (typically `api_key`) to the client constructor. Raises `SupplierError` listing supported types if not found.

#### `supported_suppliers() -> list[str]`

Returns sorted list of registered supplier type strings.

#### `register(supplier_type: str, client_class: type[BaseSupplierClient]) -> None`

Adds a new supplier to the registry at runtime. Raises `TypeError` if `client_class` is not a proper `BaseSupplierClient` subclass.

---

## Adding a New Supplier Integration

1. **Create the module:** `ecomm_suppliers/newsupplier.py`
2. **Subclass `BaseSupplierClient`:**
   - Implement `search_products()`, `get_product()`, `get_product_by_url()`.
   - Implement `close()` if you hold resources (e.g., `httpx.AsyncClient`).
   - Add `_build_demo_products()` and `_dict_to_product()` for demo mode.
3. **Add URL extraction:** Write a `_extract_product_id(url)` function with an appropriate regex for the supplier's URL format.
4. **Register in factory:** Add an entry to `_SUPPLIER_REGISTRY` in `factory.py`.
5. **Export from `__init__.py`:** Add the client class to imports and `__all__`.
6. **Write tests:** Follow the existing pattern (test demo search, get by ID, get by URL, error cases, pagination).

---

## Demo Product ID Reference

### AliExpress (24 products)

| ID | Category | Title (abbreviated) |
|----|----------|---------------------|
| `1005006841237901` | electronics | TWS Wireless Bluetooth 5.3 Earbuds |
| `1005007192384502` | electronics | USB-C Docking Station 12-in-1 |
| `1005006503928103` | electronics | Portable Mini Projector 1080P |
| `1005007458192604` | electronics | Smart Watch Ultra 2.1 Inch AMOLED |
| `1005006287451305` | electronics | Mechanical Gaming Keyboard 75% |
| `1005007631284506` | electronics | 4K Action Camera WiFi |
| `1005006912847207` | fashion | Vintage Oversized Polarized Sunglasses |
| `1005007381926408` | fashion | Men's Casual Linen Shirt |
| `1005006724183909` | fashion | Women's Crossbody Bag Genuine Leather |
| `1005007543821710` | fashion | Unisex Canvas Sneakers |
| `1005006891274311` | fashion | Titanium Steel Cuban Link Chain |
| `1005007218374212` | fashion | Women's High Waist Wide Leg Pants |
| `1005006543219813` | home | LED Strip Lights 10M RGB |
| `1005007382719414` | home | Electric Milk Frother Handheld |
| `1005006821937615` | home | Minimalist Floating Wall Shelf Set |
| `1005007492837116` | home | Bamboo Desk Organizer with Wireless Charging |
| `1005006917284317` | home | Aromatherapy Essential Oil Diffuser |
| `1005007291847518` | home | Portable Blender Personal Size |
| `1005006432918719` | beauty | Jade Face Roller and Gua Sha Set |
| `1005007183724620` | beauty | Electric Scalp Massager |
| `1005006827194321` | beauty | Vitamin C Serum 30ml |
| `1005007492183722` | beauty | LED Teeth Whitening Kit |
| `1005006738291423` | beauty | Derma Roller Microneedling Set |
| `1005007321847924` | beauty | Silk Satin Pillowcase Set |

### CJDropship (18 products)

| ID | Category | Title (abbreviated) |
|----|----------|---------------------|
| `CJ-ELEC-2891734` | electronics | Wireless Charging Pad 15W MagSafe |
| `CJ-ELEC-3847291` | electronics | Bluetooth Car FM Transmitter |
| `CJ-ELEC-4918273` | electronics | Mini Portable Power Bank 5000mAh |
| `CJ-ELEC-5729184` | electronics | Ring Light 10 Inch with Tripod |
| `CJ-FASH-6381924` | fashion | Men's Magnetic Buckle Leather Belt |
| `CJ-FASH-7492831` | fashion | Women's Compression Leggings |
| `CJ-FASH-8374912` | fashion | Minimalist Watch Men Quartz |
| `CJ-FASH-9281734` | fashion | Travel Toiletry Bag Waterproof |
| `CJ-HOME-1029384` | home | Silicone Kitchen Utensil Set 12-Piece |
| `CJ-HOME-2038471` | home | Magnetic Spice Rack Jars Set |
| `CJ-HOME-3847291` | home | Smart Plant Watering Globes |
| `CJ-HOME-4729183` | home | Collapsible Laundry Basket |
| `CJ-HOME-5918274` | home | Shower Caddy Corner Shelf |
| `CJ-BEAU-6018273` | beauty | Ice Roller for Face and Eyes |
| `CJ-BEAU-7192834` | beauty | LED Face Mask Light Therapy |
| `CJ-BEAU-8374921` | beauty | Teeth Whitening Strips 28-Pack |
| `CJ-BEAU-9281734` | beauty | Electric Nail Drill Machine |
| `CJ-BEAU-1038274` | beauty | Hair Scalp Massager Shampoo Brush |

---

## Error Handling Patterns

```python
from ecomm_suppliers import SupplierError, SupplierFactory

try:
    async with SupplierFactory.create("aliexpress") as client:
        product = await client.get_product("nonexistent-id")
except SupplierError as e:
    print(f"Supplier: {e.supplier}")         # "aliexpress"
    print(f"Status: {e.status_code}")        # 404
    print(f"Message: {e}")                   # "Product not found: nonexistent-id"
```

---

## Thread Safety and Concurrency Notes

- Supplier clients are **not** thread-safe. Each async task should create its own client instance or use the async context manager.
- `ImageService.download_image()` creates a new `httpx.AsyncClient` per call and is safe to call concurrently.
- `ImageService.optimize_image()` and `create_thumbnail()` are synchronous CPU-bound operations. In high-throughput scenarios, run them in a thread pool executor (`asyncio.to_thread()`).
- `ProductNormalizer` methods are all `@staticmethod` with no shared state, making them inherently thread-safe.
