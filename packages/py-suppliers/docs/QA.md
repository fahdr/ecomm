# py-suppliers QA Engineer Documentation

## Overview

This document provides comprehensive test plans, edge cases, and acceptance criteria for the `ecomm-suppliers` package (`ecomm_suppliers`). The package provides supplier integrations (AliExpress, CJDropship), product data models, pricing normalization, and image processing utilities.

**Test framework:** pytest + pytest-asyncio (asyncio_mode = "auto")
**Install dev dependencies:** `pip install -e "packages/py-suppliers[dev]"`

---

## Test Plan

### 1. Pydantic Models (`models.py`)

#### SupplierVariant

| ID | Test Case | Input | Expected Result |
|----|-----------|-------|-----------------|
| M-01 | Create variant with all fields | `SupplierVariant(name="Color: Red", sku="SKU-1", price=Decimal("9.99"), stock=100, image_url="https://img.png", attributes={"color": "Red"})` | Model validates, all fields accessible |
| M-02 | Create variant with required fields only | `SupplierVariant(name="Size: M", price=Decimal("5.00"))` | Valid; `sku=None`, `stock=None`, `image_url=None`, `attributes={}` |
| M-03 | Decimal price precision | `SupplierVariant(name="X", price=Decimal("18.74"))` | `variant.price == Decimal("18.74")` exactly |
| M-04 | Missing required field `name` | `SupplierVariant(price=Decimal("5"))` | `ValidationError` raised |
| M-05 | Missing required field `price` | `SupplierVariant(name="X")` | `ValidationError` raised |
| M-06 | Frozen model mutation | `variant.name = "new"` | `ValidationError` or `TypeError` raised |
| M-07 | Empty attributes dict | `SupplierVariant(name="X", price=Decimal("1"))` | `variant.attributes == {}` |

#### ShippingInfo

| ID | Test Case | Input | Expected Result |
|----|-----------|-------|-----------------|
| M-08 | Create with all fields | min=12, max=20, cost=Decimal("0.00"), method="ePacket", from="CN" | Valid model |
| M-09 | Free shipping (zero cost) | `shipping_cost=Decimal("0.00")` | Valid, no errors |
| M-10 | Missing required field | Omit `ships_from` | `ValidationError` raised |
| M-11 | Frozen mutation | Attempt to set `shipping_cost` | `TypeError` raised |

#### SupplierRating

| ID | Test Case | Input | Expected Result |
|----|-----------|-------|-----------------|
| M-12 | Create with all fields | average=4.6, count=12847, positive_percent=94.2 | Valid model |
| M-13 | Omit optional `positive_percent` | average=4.0, count=100 | Valid; `positive_percent=None` |
| M-14 | Frozen mutation | Attempt to set `average` | `TypeError` raised |

#### SupplierProduct

| ID | Test Case | Input | Expected Result |
|----|-----------|-------|-----------------|
| M-15 | Create with all required fields | source, source_id, source_url, title, description, price | Valid model |
| M-16 | Default values populated | Create with required fields only | `currency="USD"`, `images=[]`, `variants=[]`, `shipping_info=None`, `ratings=None`, `raw_data={}`, `fetched_at` is near `now(UTC)` |
| M-17 | Missing `source` | Omit source | `ValidationError` |
| M-18 | Missing `title` | Omit title | `ValidationError` |
| M-19 | Missing `price` | Omit price | `ValidationError` |
| M-20 | Frozen mutation | Attempt to set `title` | `TypeError` raised |
| M-21 | `fetched_at` auto-populated | Create product, check `fetched_at` | Datetime within last 2 seconds of UTC now |
| M-22 | Nested frozen models | Product with variants; attempt to mutate a variant | `TypeError` raised |

#### ProductSearchResult

| ID | Test Case | Input | Expected Result |
|----|-----------|-------|-----------------|
| M-23 | Default empty result | `ProductSearchResult()` | `products=[]`, `total_count=0`, `page=1`, `page_size=20` |
| M-24 | Custom pagination | `ProductSearchResult(page=3, page_size=10, total_count=50)` | Fields match input |
| M-25 | Not frozen | Mutate `page` field | Mutation succeeds (no error) |

---

### 2. AliExpress Client (`aliexpress.py`)

All tests should use demo mode (no API key).

#### Demo Mode Detection

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| AE-01 | `AliExpressClient()` with no key | `client.is_demo_mode == True` |
| AE-02 | `AliExpressClient(api_key="test")` | `client.is_demo_mode == False` |

#### Search Products (Demo)

| ID | Test Case | Query | Expected Result |
|----|-----------|-------|-----------------|
| AE-03 | Search "electronics" | `"electronics"` | Returns 6 products, all from electronics category |
| AE-04 | Search "fashion" | `"fashion"` | Returns 6 products |
| AE-05 | Search "home" | `"home"` | Returns products containing "home" in title/description/category |
| AE-06 | Search "beauty" | `"beauty"` | Returns 6 products |
| AE-07 | Search with empty string | `""` | Returns all 24 demo products (empty string matches everything) |
| AE-08 | Search nonexistent | `"xyznonexistent123"` | Returns `ProductSearchResult` with `products=[]`, `total_count=0` |
| AE-09 | Pagination page 1 | `query="electronics", page=1, page_size=3` | Returns 3 products, `total_count=6` |
| AE-10 | Pagination page 2 | `query="electronics", page=2, page_size=3` | Returns 3 products, `total_count=6` |
| AE-11 | Pagination beyond results | `query="electronics", page=5, page_size=3` | Returns `products=[]`, `total_count=6` |
| AE-12 | Case-insensitive search | `"WIRELESS"` | Returns products with "wireless" in title/description |
| AE-13 | All products have `source="aliexpress"` | Search any query | Every product has `source == "aliexpress"` |
| AE-14 | All prices are Decimal | Search any query | Every `product.price` is `isinstance(Decimal)` |
| AE-15 | Products have variants | Search "electronics" | Each product has `len(variants) >= 1` |
| AE-16 | Products have shipping info | Search "electronics" | Each product has `shipping_info is not None` |
| AE-17 | Products have ratings | Search "electronics" | Each product has `ratings is not None` |
| AE-18 | Products have images | Search any query | Each product has `len(images) >= 1` |

#### Get Product by ID (Demo)

| ID | Test Case | Product ID | Expected Result |
|----|-----------|------------|-----------------|
| AE-19 | Valid ID - TWS Earbuds | `"1005006841237901"` | Returns product with matching title containing "TWS" or "Earbuds" |
| AE-20 | Valid ID - Jade Roller | `"1005006432918719"` | Returns product with title containing "Jade" |
| AE-21 | Invalid ID | `"invalid-id-000"` | `SupplierError` with `status_code=404` |
| AE-22 | Product has source_url | `"1005006841237901"` | `source_url` contains `"aliexpress.com/item/1005006841237901.html"` |

#### Get Product by URL (Demo)

| ID | Test Case | URL | Expected Result |
|----|-----------|-----|-----------------|
| AE-23 | Standard URL format | `"https://www.aliexpress.com/item/1005006841237901.html"` | Returns correct product |
| AE-24 | Short URL format | `"https://aliexpress.com/i/1005006841237901.html"` | Returns correct product |
| AE-25 | Product URL format | `"https://aliexpress.com/product/1005006841237901"` | Returns correct product |
| AE-26 | Invalid URL | `"https://example.com/not-aliexpress"` | `SupplierError` raised |
| AE-27 | URL without product ID | `"https://aliexpress.com/category/electronics"` | `SupplierError` raised |

#### Resource Management

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| AE-28 | Async context manager | `async with AliExpressClient() as client: ...` -- no exceptions on enter/exit |
| AE-29 | Close without use | `client = AliExpressClient(); await client.close()` -- no exceptions |
| AE-30 | Double close | Call `close()` twice -- no exceptions |

---

### 3. CJDropship Client (`cjdropship.py`)

All tests should use demo mode (no API key).

#### Demo Mode Detection

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| CJ-01 | `CJDropshipClient()` with no key | `client.is_demo_mode == True` |
| CJ-02 | `CJDropshipClient(api_key="test")` | `client.is_demo_mode == False` |

#### Search Products (Demo)

| ID | Test Case | Query | Expected Result |
|----|-----------|-------|-----------------|
| CJ-03 | Search "electronics" | `"electronics"` | Returns 4 products |
| CJ-04 | Search "fashion" | `"fashion"` | Returns 4 products |
| CJ-05 | Search "home" | `"home"` | Returns 5 products |
| CJ-06 | Search "beauty" | `"beauty"` | Returns 5 products |
| CJ-07 | Search empty string | `""` | Returns all 18 demo products |
| CJ-08 | Search nonexistent | `"xyznonexistent123"` | Returns empty results |
| CJ-09 | Pagination | `query="beauty", page=1, page_size=2` | Returns 2 products, `total_count=5` |
| CJ-10 | All products have `source="cjdropship"` | Any query | Every product has `source == "cjdropship"` |
| CJ-11 | CJ ships from US | Any query | Most/all products have `shipping_info.ships_from == "US"` |
| CJ-12 | CJ shipping faster | Compare shipping days | CJ `estimated_days_max` typically <= 12 (vs. AE up to 25) |

#### Get Product by ID (Demo)

| ID | Test Case | Product ID | Expected Result |
|----|-----------|------------|-----------------|
| CJ-13 | Valid ID | `"CJ-ELEC-2891734"` | Returns Wireless Charging Pad product |
| CJ-14 | Valid beauty ID | `"CJ-BEAU-1038274"` | Returns Hair Scalp Massager product |
| CJ-15 | Invalid ID | `"CJ-INVALID-000"` | `SupplierError` with `status_code=404` |
| CJ-16 | Product source_url format | `"CJ-ELEC-2891734"` | `source_url` contains `"cjdropshipping.com/product/CJ-ELEC-2891734"` |

#### Get Product by URL (Demo)

| ID | Test Case | URL | Expected Result |
|----|-----------|-----|-----------------|
| CJ-17 | Standard URL | `"https://cjdropshipping.com/product/CJ-ELEC-2891734"` | Returns correct product |
| CJ-18 | Product detail URL | `"https://cjdropshipping.com/product_detail/p-CJ-ELEC-2891734"` | Returns correct product |
| CJ-19 | Invalid URL | `"https://example.com/not-cj"` | `SupplierError` raised |

#### Resource Management

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| CJ-20 | Async context manager | Opens and closes cleanly |
| CJ-21 | Close without use | No exceptions |

---

### 4. ProductNormalizer (`normalizer.py`)

#### calculate_markup

| ID | Test Case | Cost | Markup % | Expected Result |
|----|-----------|------|----------|-----------------|
| N-01 | 100% markup | `Decimal("10.00")` | 100.0 | `Decimal("20.00")` |
| N-02 | 150% markup | `Decimal("18.74")` | 150.0 | `Decimal("46.85")` |
| N-03 | 0% markup | `Decimal("25.00")` | 0.0 | `Decimal("25.00")` |
| N-04 | Small markup | `Decimal("1.00")` | 10.0 | `Decimal("1.10")` |
| N-05 | Zero cost | `Decimal("0.00")` | 100.0 | `Decimal("0.00")` |
| N-06 | Large price | `Decimal("999.99")` | 200.0 | `Decimal("2999.97")` |
| N-07 | Negative cost | `Decimal("-1.00")` | 50.0 | `ValueError` raised |
| N-08 | Negative markup | `Decimal("10.00")` | -10.0 | `ValueError` raised |
| N-09 | Fractional cent rounding | `Decimal("10.00")` | 33.33 | Result has exactly 2 decimal places |

#### apply_psychological_pricing

| ID | Test Case | Input Price | Expected Result |
|----|-----------|-------------|-----------------|
| N-10 | Under $10 | `Decimal("8.42")` | `Decimal("7.99")` |
| N-11 | Under $10 boundary | `Decimal("9.99")` | `Decimal("8.99")` |
| N-12 | Under $10 low | `Decimal("1.50")` | `Decimal("0.99")` |
| N-13 | Very low price | `Decimal("0.50")` | `Decimal("0.99")` (minimum) |
| N-14 | $10-$99 range | `Decimal("30.12")` | `Decimal("29.97")` |
| N-15 | $10-$99 exact | `Decimal("50.00")` | `Decimal("49.97")` |
| N-16 | $100+ range | `Decimal("149.50")` | Result ends in `.99` and is <= input |
| N-17 | $100+ exact | `Decimal("200.00")` | `Decimal("199.99")` |
| N-18 | Zero price | `Decimal("0")` | `Decimal("0")` (unchanged) |
| N-19 | Negative price | `Decimal("-5.00")` | `Decimal("-5.00")` (unchanged) |

#### calculate_compare_at_price

| ID | Test Case | Retail | Discount % | Expected Result |
|----|-----------|--------|------------|-----------------|
| N-20 | 30% discount | `Decimal("29.99")` | 30.0 | `Decimal("42.84")` |
| N-21 | 50% discount | `Decimal("20.00")` | 50.0 | `Decimal("40.00")` |
| N-22 | Small discount | `Decimal("10.00")` | 5.0 | `Decimal("10.53")` |
| N-23 | 0% discount | `Decimal("10.00")` | 0.0 | `ValueError` raised |
| N-24 | 100% discount | `Decimal("10.00")` | 100.0 | `ValueError` raised |
| N-25 | Negative discount | `Decimal("10.00")` | -10.0 | `ValueError` raised |

#### generate_slug

| ID | Test Case | Input Title | Expected Result |
|----|-----------|-------------|-----------------|
| N-26 | Simple title | `"TWS Wireless Bluetooth 5.3 Earbuds"` | `"tws-wireless-bluetooth-5-3-earbuds"` |
| N-27 | Unicode accents | `"Creme Brulee Maker -- Pro Edition!"` | `"creme-brulee-maker-pro-edition"` |
| N-28 | Extra whitespace | `"  Hello   World  "` | `"hello-world"` |
| N-29 | Special characters | `"Product!@#$%^&*()Name"` | `"product-name"` |
| N-30 | Already clean | `"simple-slug"` | `"simple-slug"` |
| N-31 | Empty string | `""` | `""` |
| N-32 | Very long title (200+ chars) | 200-character string | Result <= 120 chars, truncated at hyphen boundary |
| N-33 | CJK characters | Title with Chinese/Japanese chars | Non-ASCII stripped, remaining ASCII slugified |
| N-34 | Numbers preserved | `"USB-C 3.0 Hub"` | `"usb-c-3-0-hub"` |
| N-35 | Leading/trailing special chars | `"---Product---"` | `"product"` |

---

### 5. ImageService (`image_service.py`)

Use small in-memory test images created with Pillow. Mock HTTP calls for `download_image`.

#### download_image

| ID | Test Case | Setup | Expected Result |
|----|-----------|-------|-----------------|
| I-01 | Successful download | Mock 200 response with `content-type: image/jpeg` | Returns image bytes |
| I-02 | HTTP 404 | Mock 404 response | `SupplierError` with `status_code=404` |
| I-03 | HTTP 500 | Mock 500 response | `SupplierError` with `status_code=500` |
| I-04 | Non-image content type | Mock 200 with `content-type: text/html` | `SupplierError` raised |
| I-05 | Connection timeout | Mock `httpx.TimeoutException` | `SupplierError` raised |
| I-06 | Connection error | Mock `httpx.ConnectError` | `SupplierError` raised |
| I-07 | No content-type header | Mock 200 with no content-type | Returns bytes (no error -- empty content-type passes the check) |

#### optimize_image

| ID | Test Case | Input | Expected Result |
|----|-----------|-------|-----------------|
| I-08 | Wide image resize | 2000x1000 JPEG | Output width = 1200, height proportional (600) |
| I-09 | Small image no resize | 800x600 JPEG | Output dimensions <= 800x600 (no upscaling) |
| I-10 | RGBA to RGB conversion | RGBA PNG bytes | Output is valid JPEG (RGB mode) |
| I-11 | Palette (P) mode | P-mode PNG bytes | Output is valid JPEG (RGB mode) |
| I-12 | LA (Luminance + Alpha) mode | LA PNG bytes | Output is valid JPEG (RGB mode) |
| I-13 | Grayscale (L) mode | L-mode image | Output is valid JPEG (converted to RGB) |
| I-14 | Custom max_width | 2000px image, `max_width=500` | Output width = 500 |
| I-15 | Custom quality | Same image, quality=50 vs quality=95 | quality=50 produces smaller file |
| I-16 | Custom output format | `output_format="PNG"` | Output is valid PNG |
| I-17 | Invalid image data | Random bytes `b"notanimage"` | `SupplierError` raised |

#### create_thumbnail

| ID | Test Case | Input | Expected Result |
|----|-----------|-------|-----------------|
| I-18 | Default 300x300 | 1000x800 image | Output fits within 300x300, aspect ratio preserved |
| I-19 | Landscape aspect ratio | 1000x500 image, size=(300,300) | Output is 300x150 (width limited) |
| I-20 | Portrait aspect ratio | 500x1000 image, size=(300,300) | Output is 150x300 (height limited) |
| I-21 | Small image no upscale | 100x100 image, size=(300,300) | Output is 100x100 (no upscaling) |
| I-22 | Custom size | 1000x1000, size=(150,150) | Output fits within 150x150 |
| I-23 | RGBA input | RGBA image | Valid JPEG thumbnail (composited on white) |
| I-24 | Invalid data | Random bytes | `SupplierError` raised |

#### get_image_dimensions

| ID | Test Case | Input | Expected Result |
|----|-----------|-------|-----------------|
| I-25 | Valid JPEG | 800x600 JPEG bytes | `(800, 600)` |
| I-26 | Valid PNG | 1024x768 PNG bytes | `(1024, 768)` |
| I-27 | Invalid data | Random bytes | `SupplierError` raised |

#### get_image_format

| ID | Test Case | Input | Expected Result |
|----|-----------|-------|-----------------|
| I-28 | JPEG image | JPEG bytes | `"JPEG"` |
| I-29 | PNG image | PNG bytes | `"PNG"` |
| I-30 | Invalid data | Random bytes | `None` |

---

### 6. SupplierFactory (`factory.py`)

| ID | Test Case | Input | Expected Result |
|----|-----------|-------|-----------------|
| F-01 | Create AliExpress client | `SupplierFactory.create("aliexpress")` | Returns `AliExpressClient` instance |
| F-02 | Create CJDropship client | `SupplierFactory.create("cjdropship")` | Returns `CJDropshipClient` instance |
| F-03 | Create with API key | `SupplierFactory.create("aliexpress", api_key="key")` | Returns client with `is_demo_mode == False` |
| F-04 | Case insensitive | `SupplierFactory.create("AliExpress")` | Returns `AliExpressClient` |
| F-05 | Whitespace trimmed | `SupplierFactory.create("  cjdropship  ")` | Returns `CJDropshipClient` |
| F-06 | Unknown supplier | `SupplierFactory.create("unknown")` | `SupplierError` raised, message lists supported types |
| F-07 | Supported suppliers list | `SupplierFactory.supported_suppliers()` | `["aliexpress", "cjdropship"]` (sorted) |
| F-08 | Register new supplier | Register mock class, then create | Returns instance of registered class |
| F-09 | Register non-subclass | `SupplierFactory.register("bad", str)` | `TypeError` raised |
| F-10 | Register non-class | `SupplierFactory.register("bad", "string")` | `TypeError` raised |

---

### 7. Integration Tests

| ID | Test Case | Description | Expected Result |
|----|-----------|-------------|-----------------|
| INT-01 | Full import workflow | Search -> get_product -> normalize pricing -> process image | Data flows correctly through all stages |
| INT-02 | Cross-supplier search | Search same query on both suppliers | Both return results with consistent model structure |
| INT-03 | Factory to context manager | `SupplierFactory.create()` used with `async with` | No resource leaks |
| INT-04 | Normalizer on supplier data | Apply `calculate_markup` + `apply_psychological_pricing` to a supplier product's price | Result is a valid Decimal with charm pricing |
| INT-05 | Slug from supplier title | `generate_slug(product.title)` for each demo product | All slugs are non-empty, lowercase, hyphen-separated, <= 120 chars |

---

## Edge Cases

### Pricing Edge Cases
- Zero-cost product with markup: `calculate_markup(Decimal("0"), 100)` should return `Decimal("0.00")`
- Very small price with psychological pricing: `apply_psychological_pricing(Decimal("0.50"))` should return `Decimal("0.99")` (minimum threshold)
- Large markup percent: `calculate_markup(Decimal("1"), 10000)` should not overflow
- Price exactly at boundary: `apply_psychological_pricing(Decimal("10.00"))` -- behavior at the $10 threshold
- Price exactly at $100: `apply_psychological_pricing(Decimal("100.00"))` -- behavior at the $100 threshold

### Slug Edge Cases
- All non-ASCII characters: `generate_slug("...")` (Chinese only) should return empty string
- Emoji in title: `generate_slug("Cool Product ")` should strip emojis
- Only special characters: `generate_slug("!@#$%^&*()")` should return empty string
- 120+ character title: Slug truncated at hyphen boundary, no trailing hyphen
- Title with multiple consecutive spaces/hyphens: Should collapse to single hyphen

### Image Edge Cases
- 1x1 pixel image: Should process without errors
- Very large image (10000x10000): Should resize successfully (may be slow)
- Animated GIF: `optimize_image` should handle first frame
- Zero-byte input: Should raise `SupplierError`
- CMYK mode image: Should convert to RGB for JPEG output

### Supplier Client Edge Cases
- Search with only whitespace: Should return results (whitespace matches in substring search)
- Product ID with leading/trailing whitespace in demo mode: Should not match (IDs are exact-match)
- Multiple concurrent searches on same client: Should work in async context (no shared mutable state in search path)

---

## Acceptance Criteria

1. **All supplier clients in demo mode return realistic product data** without requiring API keys or network access.
2. **AliExpress demo data includes exactly 24 products** across 4 categories (6 per category: electronics, fashion, home, beauty).
3. **CJDropship demo data includes exactly 18 products** across 4 categories (4 electronics, 4 fashion, 5 home, 5 beauty).
4. **All money values use `Decimal`** -- no `float` anywhere in price fields (`SupplierProduct.price`, `SupplierVariant.price`, `ShippingInfo.shipping_cost`, normalizer return values).
5. **All data models with `frozen=True` reject mutation** -- assigning to any field raises an error.
6. **`SupplierError` is the only exception type** raised by supplier client operations (search, get, get_by_url, close, download_image).
7. **Factory creates correct client types** and raises `SupplierError` for unknown supplier names.
8. **URL extraction works for all documented URL patterns** for both AliExpress and CJDropship.
9. **Image processing handles RGBA, P, LA, L, and RGB modes** without errors.
10. **Slug generation produces valid URL-safe strings** -- lowercase, hyphens only, no leading/trailing hyphens, max 120 characters.
11. **Package installs cleanly** via `pip install -e .` with no dependency conflicts.
12. **All public classes, methods, and functions have docstrings** covering purpose, parameters, and return values.

---

## Test Data Reference

### Stable AliExpress Product IDs for Assertions

| ID | Category | Use In Test |
|----|----------|-------------|
| `1005006841237901` | electronics | First product, TWS earbuds -- good for basic get_product tests |
| `1005007321847924` | beauty | Last product, silk pillowcases -- good for boundary tests |
| `1005006432918719` | beauty | Jade roller, cheapest at $4.87 -- good for pricing tests |
| `1005006503928103` | electronics | Projector, most expensive at $67.43 -- good for pricing tests |

### Stable CJDropship Product IDs for Assertions

| ID | Category | Use In Test |
|----|----------|-------------|
| `CJ-ELEC-2891734` | electronics | First product, wireless charger -- good for basic tests |
| `CJ-BEAU-1038274` | beauty | Last product, scalp brush at $1.89 -- cheapest CJ product |
| `CJ-BEAU-7192834` | beauty | LED face mask at $15.67 -- most expensive CJ product |

### Test Image Generation (Pillow)

```python
from io import BytesIO
from PIL import Image

def make_test_image(width=800, height=600, mode="RGB", fmt="JPEG") -> bytes:
    """Create a minimal test image for ImageService tests."""
    img = Image.new(mode, (width, height), color=(128, 128, 128) if mode == "RGB" else 128)
    buf = BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()

def make_rgba_image(width=100, height=100) -> bytes:
    """Create an RGBA PNG for mode conversion tests."""
    img = Image.new("RGBA", (width, height), (255, 0, 0, 128))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
```
