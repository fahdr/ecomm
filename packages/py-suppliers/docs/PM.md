# py-suppliers Project Manager Documentation

## Executive Summary

`ecomm-suppliers` is a shared Python package that serves as the supplier integration layer for the entire ecomm dropshipping platform. It provides a unified interface for connecting to third-party product suppliers (AliExpress, CJDropship), normalizing their product data into a common format, and preparing that data for use in merchant storefronts. The package eliminates the need for each service to implement its own supplier integration logic.

---

## Feature Scope

### Delivered in v0.1.0

| Feature | Description | Status |
|---------|-------------|--------|
| Unified supplier interface | Abstract base class (`BaseSupplierClient`) with standard methods for search, get-by-ID, and get-by-URL | Complete |
| AliExpress client | Full demo mode with 24 realistic products across 4 categories; real API endpoint stubs in place | Demo complete, real API stubbed |
| CJDropship client | Full demo mode with 18 realistic products across 4 categories; real API endpoint stubs in place | Demo complete, real API stubbed |
| Product data models | 5 Pydantic models (`SupplierProduct`, `SupplierVariant`, `ShippingInfo`, `SupplierRating`, `ProductSearchResult`) with validation and immutability | Complete |
| Pricing normalizer | Markup calculation, psychological pricing (charm pricing), compare-at/strikethrough pricing | Complete |
| Slug generator | SEO-friendly URL slug generation from product titles with unicode support | Complete |
| Image processing | Download, optimize (resize + compress), thumbnail creation, dimension/format detection | Complete |
| Factory pattern | `SupplierFactory` for creating supplier clients by name with runtime registration support | Complete |
| Editable installation | Package installs via `pip install -e .` from the monorepo | Complete |

### Pending -- Future Milestones

| Feature | Priority | Blocked By | Estimated Effort |
|---------|----------|------------|------------------|
| Real AliExpress API integration | High | API key provisioning from AliExpress developer program | 2-3 days |
| Real CJDropship API integration | High | API key provisioning from CJDropship developer program | 2-3 days |
| Spocket supplier integration | Medium | Spocket API access, business agreement | 3-4 days |
| Automated product sync scheduling | Medium | Real API integrations complete | 2 days |
| Price history tracking | Low | Database schema design, service integration | 3 days |
| Inventory / stock level monitoring | Medium | Real API integrations with webhook support | 3-4 days |
| Bulk import from CSV/spreadsheet | Low | Import format specification | 2 days |
| Rate limit handling and retry logic | High | Real API integrations | 1-2 days |
| Caching layer for API responses | Medium | Cache infrastructure decision (Redis vs. in-memory) | 2 days |

---

## Dependency Map

### Internal Dependencies (this package depends on)

None. `ecomm-suppliers` is a leaf package with no dependencies on other internal monorepo packages (`ecomm_core`, `ecomm_connectors`, etc.).

### Internal Dependents (packages/services that depend on this)

Any service in the monorepo that needs to import products from suppliers. The package is designed to be consumed by:
- **Dropshipping core** (`dropshipping/`) -- product import workflows
- **SpyDrop** (`spydrop/`) -- competitor product analysis
- **TrendScout** (`trendscout/`) -- trending product discovery
- **ContentForge** (`contentforge/`) -- product content generation from supplier data

### External Dependencies

| Package | Version Requirement | Purpose | License Risk |
|---------|-------------------|---------|--------------|
| `httpx` | >= 0.27.0 | Async HTTP client | BSD-3 (safe) |
| `pydantic` | >= 2.5.0 | Data validation | MIT (safe) |
| `beautifulsoup4` | >= 4.12.0 | HTML parsing | MIT (safe) |
| `Pillow` | >= 10.2.0 | Image processing | HPND (safe) |

---

## Product Category Coverage

Both supplier integrations cover 4 product categories in demo mode:

| Category | AliExpress Products | CJDropship Products | Total |
|----------|-------------------|-------------------|-------|
| Electronics | 6 | 4 | 10 |
| Fashion | 6 | 4 | 10 |
| Home & Garden | 6 | 5 | 11 |
| Beauty & Health | 6 | 5 | 11 |
| **Total** | **24** | **18** | **42** |

Product categories include realistic items such as wireless earbuds, smartwatches, sunglasses, leather bags, LED strip lights, kitchen utensils, skincare tools, and silk pillowcases.

---

## Supplier Comparison

| Dimension | AliExpress | CJDropship |
|-----------|------------|------------|
| Catalog size | Millions of products | Curated catalog (~100K+) |
| Shipping origin | China (CN) | US / EU warehouses |
| Typical shipping time | 12-25 days | 3-10 days |
| Shipping cost | Often free (standard) | Free to $3.99 |
| Branded packaging | Not available | Available |
| Quality inspection | Not available | Available |
| API style | POST-based (affiliate API) | REST GET/POST |
| Auth mechanism | `app_key` in request body | `CJ-Access-Token` header |
| Demo product count | 24 | 18 |
| Product ID format | Numeric strings | `CJ-{CATEGORY}-{NUMBER}` |

---

## Key Milestones

### Phase 1 -- Foundation (v0.1.0) -- COMPLETE

- [x] Abstract base class and exception hierarchy
- [x] Pydantic data models with validation
- [x] AliExpress demo client (24 products)
- [x] CJDropship demo client (18 products)
- [x] Factory pattern with registry
- [x] Product normalizer (markup, psychological pricing, compare-at, slug)
- [x] Image service (download, optimize, thumbnail, dimensions, format)
- [x] Package installable via pip

### Phase 2 -- Real API Integration (planned)

- [ ] Obtain AliExpress Open Platform API key
- [ ] Implement AliExpress response parsing in `search_products()` and `get_product()`
- [ ] Obtain CJDropship developer API key
- [ ] Implement CJDropship response parsing in `search_products()` and `get_product()`
- [ ] Add rate limit detection and backoff
- [ ] Add response caching

### Phase 3 -- Expansion (planned)

- [ ] Spocket supplier integration
- [ ] Automated product sync scheduling
- [ ] Price history tracking
- [ ] Inventory monitoring
- [ ] Bulk CSV import

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **API key provisioning delays** | Blocks real supplier integrations | Medium | Demo mode provides full development capability; real API can be added incrementally |
| **Supplier API rate limits** | Throttled requests in production | High | Stubs exist for rate limit handling; backoff strategy documented |
| **Supplier API changes** | Breaking changes to response formats | Medium | `raw_data` field preserves original responses; normalization layer isolates services from API changes |
| **Image CDN reliability** | Product images fail to load | Medium | Image service includes timeout handling and error wrapping; consider local image proxy for production |
| **Price precision errors** | Incorrect pricing displayed to customers | Low | All money uses `Decimal` arithmetic; psychological pricing is carefully bounded |
| **Dependency security** | Vulnerability in httpx/Pillow/pydantic | Low | Standard, well-maintained libraries; pin minimum versions, monitor CVEs |

---

## Quality Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Public API docstring coverage | 100% | 100% (all classes, methods, functions have docstrings) |
| Type annotation coverage | 100% | 100% (full type hints on all public and private functions) |
| Demo data realism | High | High (realistic product titles, descriptions, prices, SKUs, shipping) |
| Model immutability | All data models frozen | 4/5 models frozen (`ProductSearchResult` intentionally mutable) |
| Exception consistency | Single exception type | Achieved (`SupplierError` only) |

---

## Stakeholder Communication

### For Engineering

The package is ready for integration. Services can import `ecomm_suppliers` and use demo mode immediately. No API keys or external services are required for development.

### For Product

42 realistic demo products are available across 4 categories from 2 supplier platforms. The pricing normalizer supports markup, psychological pricing, and compare-at pricing out of the box. Real supplier API integration is the next deliverable once API keys are provisioned.

### For QA

All demo data is deterministic. Product IDs are stable, making it possible to write assertions against specific products. The package has comprehensive docstrings and a clear test surface (see QA.md).
