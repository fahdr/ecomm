# MVP Implementation Plan — Path to Production

**Document Version:** 1.1
**Created:** 2026-02-14
**Last Updated:** 2026-02-14
**Status:** Phase 1-2 COMPLETE, Phase 3 mostly complete, Phase 4+ pending real API credentials

---

## Executive Summary

This plan outlines the work required to complete the MVP (Minimum Viable Product) for the dropshipping automation platform. The codebase is **~85% complete** — all services are built, tested, and documented. The remaining work is integrating real supplier APIs and deploying to production.

**Key Gap Resolved:** SourcePilot (A9) service built with full import pipeline (demo mode).
**Remaining Gap:** Real API credentials needed for live supplier/AI/email integrations.

**Estimated Remaining Effort:** 4-6 weeks (real APIs + infrastructure + launch)
**MVP Launch Target:** Q2 2026

---

## Table of Contents

1. [Current State Assessment](#current-state-assessment)
2. [Critical Missing Features](#critical-missing-features)
3. [NEW: SourcePilot Service (A9)](#new-sourcepilot-service-a9)
4. [Implementation Phases](#implementation-phases)
5. [Phase 1: Foundation (Weeks 1-2)](#phase-1-foundation-weeks-1-2)
6. [Phase 2: SourcePilot Service (Weeks 3-4)](#phase-2-sourcepilot-service-weeks-3-4)
7. [Phase 3: Product Import Pipeline (Weeks 5-6)](#phase-3-product-import-pipeline-weeks-5-6)
8. [Phase 4: Automation Workflows (Weeks 7-8)](#phase-4-automation-workflows-weeks-7-8)
9. [Phase 5: Integration & Testing (Weeks 9-10)](#phase-5-integration--testing-weeks-9-10)
10. [Phase 6: Polish & Launch Prep (Weeks 11-12)](#phase-6-polish--launch-prep-weeks-11-12)
11. [Success Criteria](#success-criteria)
12. [Risk Mitigation](#risk-mitigation)
13. [Post-MVP Roadmap](#post-mvp-roadmap)

---

## Current State Assessment

### ✅ What's Complete (90-100%)

| Component | Status | Notes |
|-----------|--------|-------|
| Dropshipping Core | 95% | Store CRUD, products, orders, payments, themes, analytics, ServiceBridge |
| 9 SaaS Services Structure | 100% | All have backends, dashboards, landing pages, tests, docs |
| **SourcePilot (A9)** | **100%** | **Complete service with 130 tests + 54 e2e tests (demo mode)** |
| LLM Gateway | 100% | Multi-provider AI routing operational |
| Admin Dashboard | 100% | Super admin controls functional |
| ServiceBridge | 100% | Event-driven integration framework complete |
| Database Design | 100% | All models implemented with proper constraints |
| Test Infrastructure | 100% | 2,025+ backend tests + 62 e2e spec files, schema isolation |
| Documentation | 100% | 4-audience docs (Dev/PM/QA/User) for all services |
| py-suppliers Package | 100% | AliExpress + CJDropship clients (demo mode), normalizer, image service |

### ⚠️ What Uses Demo Data (needs real API credentials)

| Component | Code Status | Blocker |
|-----------|-------------|---------|
| TrendScout | 100% built | Uses mock data — needs Apify, PRAW, pytrends credentials |
| ContentForge | 100% built | Mock content — needs Claude API via LLM Gateway |
| RankPilot | 100% built | Mock SEO data — needs SerpAPI credentials |
| FlowSend | 100% built | Mock email — needs SendGrid credentials |
| SpyDrop | 100% built | Mock competitor data — needs scraping infra |
| PostPilot | 100% built | Mock social posts — needs Meta/Twitter API |
| AdScale | 100% built | Mock ad campaigns — needs Google/Meta Ads API |
| ShopChat | 100% built | Basic chat — needs Claude API via LLM Gateway |
| SourcePilot | 100% built | Demo products — needs AliExpress/CJDropship API keys |

### ❌ What's Not Started (Infrastructure & Ops)

| Component | Status | Impact |
|-----------|--------|--------|
| Real API integration | 0% | CRITICAL — Demo data only, needs live credentials |
| Monitoring (Sentry/Flower) | 0% | HIGH — Can't operate at scale safely |
| K8s deployment | 0% | HIGH — No production deployment |
| Rate limiting | 0% | HIGH — Security vulnerability |
| Backup/DR system | 0% | HIGH — Operational risk |
| CI/CD pipeline | 0% | MEDIUM — Manual deployments don't scale |
| Beta onboarding | 0% | MEDIUM — Launch prep |

---

## Critical Missing Features

Based on comprehensive gap analysis, here are ALL critical missing features beyond SourcePilot:

### 1. **Supplier Import Service (NEW: A9 SourcePilot)** 🚨 CRITICAL

**Problem:** Platform has no way to:
- Scrape/import products from AliExpress
- Fetch products from CJDropship API
- Import from Spocket, Dsers, Modalyst
- Track supplier inventory & pricing updates

**Current State:**
- ✅ `Supplier` and `ProductSupplier` models exist
- ✅ Manual supplier CRUD works
- ❌ No automated product import
- ❌ No scraping infrastructure
- ❌ No supplier API integrations

**Why Critical:**
Without this, users can't:
1. Auto-import trending products found by TrendScout
2. Keep prices/inventory in sync with suppliers
3. Source products at scale
4. Track supplier reliability

**Solution:** Build **SourcePilot (A9)** — dedicated supplier integration service

---

### Additional Critical Gaps Identified

#### **Store Deployment Automation** 🚨 CRITICAL (Post-MVP)
- ❌ No K8s manifests for automated store deployment
- ❌ No cert-manager integration for SSL
- ❌ No Ingress routing for custom domains
- ❌ No DNS provisioning automation
- **Workaround:** Manual store creation works for MVP

#### **Monitoring & Observability** 🔴 HIGH
- ❌ No Sentry error tracking
- ❌ No Prometheus/Grafana metrics
- ❌ No log aggregation (Loki)
- ❌ No alerting system
- **Impact:** Can't operate at scale safely

#### **Backup & Disaster Recovery** 🔴 HIGH
- ❌ No automated database backups
- ❌ No point-in-time recovery
- ❌ No cross-region replication
- ❌ No user data export (GDPR requirement)
- **Impact:** Operational risk

#### **Rate Limiting** 🔴 HIGH
- ❌ No rate limits on core APIs
- ❌ No per-user throttling
- ❌ No IP-based rate limiting
- **Impact:** Security vulnerability

#### **CI/CD Pipeline** ⚠️ MEDIUM
- ⚠️ Partial GitHub Actions setup
- ❌ No automated K8s deployment
- ❌ No blue-green deployment
- ❌ No automated rollback
- **Impact:** Manual deployments don't scale

---

### 2. **Product Import Pipeline** 🚨 CRITICAL

**Problem:** TrendScout finds products but can't import them into dropshipping stores.

**Missing Components:**
- Celery workflow: TrendScout → SourcePilot → Dropshipping
- Product normalization (different suppliers have different schemas)
- Image download & optimization
- Variant extraction
- Price markup calculation

---

### 3. **Real Data Integration** 🚨 CRITICAL

**Problem:** All automation uses mock data.

**Missing Integrations:**
- AliExpress Dropshipping API
- CJDropship API
- Apify (TikTok scraping)
- PRAW (Reddit API)
- pytrends (Google Trends)
- SerpAPI (keyword research)
- SendGrid (email sending)

---

### 4. **Automation Task Execution** 🔴 HIGH

**Problem:** Celery tasks exist but don't execute automation workflows.

**Missing:**
- Daily product research scheduler (Celery Beat)
- Email flow triggers (cart abandoned, order placed)
- SEO optimization scheduler
- Content generation on product create
- ServiceBridge event handlers in services

---

### 5. **Additional Missing Features (Complete List)**

#### **Infrastructure Gaps:**
- ✅ Health endpoints exist → ❌ Not connected to monitoring
- ✅ Docker files exist → ❌ No K8s manifests
- ✅ Basic CI → ❌ No automated deployment pipeline
- ✅ Flower monitoring → ❌ Not deployed/configured
- ❌ API rate limiting (except LLM Gateway)
- ❌ Backup/DR system
- ❌ Log aggregation

#### **Service-Specific Gaps:**
| Service | Critical Gap |
|---------|-------------|
| **TrendScout** | Mock data only (no Apify/PRAW/pytrends) |
| **ContentForge** | Mock content (Claude not called) |
| **RankPilot** | No Celery tasks, no SerpAPI |
| **FlowSend** | No event triggers, SendGrid stubbed |
| **SpyDrop** | Competitor monitoring not functional |
| **PostPilot** | Social media APIs not integrated |
| **AdScale** | Ad platform APIs not integrated |
| **ShopChat** | Basic chat only, limited context |

#### **Platform Gaps:**
- ⚠️ Team collaboration exists → ❌ Incomplete (no audit log, no granular permissions)
- ⚠️ Webhooks exist → ❌ No retry mechanism fully tested
- ⚠️ Multi-currency exists → ❌ Currency conversion not live
- ❌ White-label capabilities (Pro/Enterprise tier)
- ❌ Referral/affiliate program
- ❌ Advanced analytics (cohort, CLV, churn prediction)
- ❌ Customer support tools (Zendesk/Intercom)
- ❌ Usage-based billing (API overages)
- ❌ Payment retry logic (failed card recovery)

---

## NEW: SourcePilot Service (A9)

### Overview

**Name:** SourcePilot
**Tagline:** Automated Supplier Product Import
**Port:** Backend 8109, Dashboard 3109, Landing 3209
**Purpose:** Bridge between supplier platforms and dropshipping stores

### Architecture

```
sourcepilot/
├── backend/                    # Port 8109
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py         # User authentication
│   │   │   ├── suppliers.py    # Supplier account management
│   │   │   ├── imports.py      # Import job CRUD
│   │   │   ├── products.py     # Product search & preview
│   │   │   ├── connections.py  # Store connections
│   │   │   ├── billing.py      # Subscription & usage
│   │   │   └── webhooks.py     # Platform events
│   │   ├── models/
│   │   │   ├── import_job.py   # ImportJob (pending/running/completed/failed)
│   │   │   ├── supplier_account.py  # SupplierAccount (aliexpress/cj/spocket)
│   │   │   ├── product_cache.py     # ProductCache (scraped data)
│   │   │   ├── import_history.py    # ImportHistory (audit log)
│   │   │   ├── price_watch.py       # PriceWatch (monitor supplier price changes)
│   │   │   ├── store_connection.py  # StoreConnection
│   │   │   └── subscription.py      # Subscription
│   │   ├── services/
│   │   │   ├── aliexpress_service.py   # AliExpress API + scraping
│   │   │   ├── cjdropship_service.py   # CJDropship API integration
│   │   │   ├── spocket_service.py      # Spocket API integration
│   │   │   ├── import_service.py       # Orchestrates imports
│   │   │   ├── product_normalizer.py   # Normalize different schemas
│   │   │   ├── image_service.py        # Download & optimize images
│   │   │   ├── pricing_service.py      # Calculate markups
│   │   │   └── variant_service.py      # Extract variants
│   │   ├── tasks/
│   │   │   ├── celery_app.py
│   │   │   ├── import_tasks.py         # process_import_job()
│   │   │   ├── sync_tasks.py           # sync_supplier_prices()
│   │   │   └── scraping_tasks.py       # scrape_product_details()
│   │   └── scrapers/
│   │       ├── base_scraper.py         # Base scraper interface
│   │       ├── aliexpress_scraper.py   # Playwright-based AliExpress scraper
│   │       └── utils.py                # Proxy rotation, CAPTCHA solving
│   └── tests/                          # Target: 120+ tests
├── dashboard/                          # Port 3109
│   └── src/app/
│       ├── suppliers/                  # Manage supplier accounts
│       ├── imports/                    # Import jobs & history
│       ├── products/                   # Browse supplier catalogs
│       ├── pricing/                    # Configure markup rules
│       └── settings/                   # API keys, connections
└── landing/                            # Port 3209
    └── Marketing page for SourcePilot
```

### Core Features

#### 1. Multi-Supplier Support

**Supported Suppliers (Priority Order):**
1. **AliExpress** (API + scraping fallback)
   - AliExpress Dropshipping API (official)
   - Playwright scraper for non-API products
2. **CJDropship** (API)
   - RESTful API integration
   - Product search, order placement
3. **Spocket** (API)
   - Premium suppliers, faster shipping
4. **Modalyst** (Future)
5. **Dsers** (Future)

#### 2. Product Import Flow

```
User Action: "Import AliExpress Product"
  ↓
1. User pastes AliExpress URL or searches by keyword
  ↓
2. SourcePilot fetches product data (API or scrape)
  ↓
3. Preview shown: images, title, price, variants, shipping
  ↓
4. User configures: markup %, compare_at_price, tags
  ↓
5. Click "Import to Store"
  ↓
6. Celery task: process_import_job.delay(job_id)
  ↓
7. Task execution:
   a. Download images → optimize → upload to S3
   b. Extract variants (color, size, etc.)
   c. Calculate prices with markup
   d. Create Supplier + ProductSupplier records in dropshipping DB
   e. Create Product + ProductVariant records
   f. Generate basic content (or queue ContentForge)
   g. Fire platform event: product.created
  ↓
8. Product appears in dropshipping store
```

#### 3. Bulk Import

- CSV upload: List of AliExpress URLs
- TrendScout integration: Import top-scored products
- Keyword search: Import all matching products

#### 4. Price & Inventory Sync

- Daily Celery Beat task: `sync_supplier_prices.delay()`
- Checks supplier for price changes
- Updates `ProductSupplier.supplier_cost`
- Optionally updates retail price (maintain margin)
- Out-of-stock detection

#### 5. Subscription Plans

| Tier | Price | Imports/Month | Stores | Suppliers | Features |
|------|-------|--------------|--------|-----------|----------|
| Free | $0 | 10 | 1 | AliExpress only | Manual import |
| Starter | $19 | 100 | 3 | AliExpress + CJ | Bulk import |
| Pro | $49 | 500 | 10 | All suppliers | Auto-sync prices |
| Enterprise | $199 | Unlimited | Unlimited | All + custom | API access |

### API Endpoints

**Product Search:**
- `GET /api/v1/products/search?supplier=aliexpress&q=wireless+earbuds`
- `POST /api/v1/products/preview` — Preview product before import

**Import Management:**
- `POST /api/v1/imports` — Create import job
- `GET /api/v1/imports/{id}` — Poll job status
- `GET /api/v1/imports/history` — Import history
- `POST /api/v1/imports/bulk` — Bulk import from CSV

**Supplier Accounts:**
- `POST /api/v1/suppliers/accounts` — Connect supplier account (API keys)
- `GET /api/v1/suppliers/accounts` — List connected accounts

**Sync:**
- `POST /api/v1/sync/prices` — Trigger manual price sync

### Integration Points

**With Dropshipping Platform:**
- Creates `Supplier` records
- Creates `ProductSupplier` links
- Creates `Product` + `ProductVariant` records
- Uploads images to shared S3 bucket
- Fires `product.created` event via ServiceBridge

**With TrendScout:**
- Receives `product.scored` webhook with high-score products
- Auto-imports products with score >= 80
- Sends import status back to TrendScout

**With ContentForge:**
- After import, fires `product.created` event
- ContentForge generates enhanced descriptions

---

## Implementation Phases

### Overview

| Phase | Duration | Focus | Deliverables |
|-------|----------|-------|--------------|
| 1 | 2 weeks | Foundation | API integrations, dev environment |
| 2 | 2 weeks | SourcePilot | Complete A9 service with AliExpress |
| 3 | 2 weeks | Import Pipeline | End-to-end product import workflow |
| 4 | 2 weeks | Automation | Real data, Celery workflows, event triggers |
| 5 | 2 weeks | Integration | Wire all services together |
| 6 | 2 weeks | Polish | UI/UX, error handling, docs, launch prep |

---

## Phase 1: Foundation (Weeks 1-2)

### Goals

1. Set up API accounts and credentials
2. Build core integration libraries
3. Test data fetching from real sources
4. Update devcontainer with new dependencies

### Tasks

#### Week 1: API Setup & Credentials

**Task 1.1: Acquire API Access**
- [ ] Register for AliExpress Dropshipping API
- [ ] Register for CJDropship API
- [ ] Register for Apify account (TikTok scraping)
- [ ] Register for PRAW (Reddit API)
- [ ] Register for SerpAPI (keyword research)
- [ ] Register for SendGrid (email)
- [ ] Store credentials in `.env` files

**Task 1.2: Install Dependencies**
```python
# Add to requirements.txt
playwright==1.41.0         # Web scraping
apify-client==1.6.0        # TikTok scraping via Apify
praw==7.7.1                # Reddit API
pytrends==4.9.2            # Google Trends
sendgrid==6.11.0           # Email
pillow==10.2.0             # Image optimization
requests==2.31.0           # HTTP
beautifulsoup4==4.12.3     # HTML parsing
```

**Task 1.3: Update Devcontainer**
- [ ] Add Playwright browser installation to `postCreateCommand`
- [ ] Add environment variables to `docker-compose.yml`
- [ ] Test that all APIs are reachable

#### Week 2: Core Integration Libraries

**Task 1.4: AliExpress Integration**
- [ ] Create `packages/py-suppliers/` package
- [ ] Build `aliexpress_api.py` (API client)
- [ ] Build `aliexpress_scraper.py` (Playwright fallback)
- [ ] Test: Fetch product by ID
- [ ] Test: Search products by keyword
- [ ] Test: Extract variants, images, pricing

**Task 1.5: Basic Scraping Infrastructure**
- [ ] Create `scrapers/base_scraper.py` (abstract base)
- [ ] Implement proxy rotation (optional for MVP)
- [ ] Implement retry logic with exponential backoff
- [ ] Add CAPTCHA detection (log warning, manual fallback)

**Task 1.6: Test Real Data Fetching**
- [ ] Write pytest that fetches 5 real AliExpress products
- [ ] Verify data structure matches expected schema
- [ ] Confirm images download successfully

**Deliverables:**
- ✅ All API credentials stored securely
- ✅ Dependencies installed
- ✅ `packages/py-suppliers/` package with AliExpress integration
- ✅ Tests demonstrating real data fetch

---

## Phase 2: SourcePilot Service (Weeks 3-4)

### Goals

1. Build A9 SourcePilot service from scratch
2. Implement product import job workflow
3. Create dashboard for import management
4. Test end-to-end import (AliExpress → Dropshipping)

### Tasks

#### Week 3: Backend Structure

**Task 2.1: Scaffold SourcePilot Service**
- [ ] Copy `_template/` to `sourcepilot/`
- [ ] Update ports (8109, 3109, 3209)
- [ ] Create database schema `sourcepilot` for tests
- [ ] Update `Makefile` with sourcepilot targets

**Task 2.2: Database Models**
- [ ] Create `import_job.py` model
  ```python
  class ImportJob(Base):
      id: UUID
      user_id: UUID
      store_id: UUID
      source: Enum(aliexpress, cjdropship, spocket)
      source_url: str
      status: Enum(pending, running, completed, failed)
      product_data: JSON  # Raw supplier data
      config: JSON  # markup, tags, etc.
      error_message: str | None
      created_product_id: UUID | None  # Link to created product
      created_at, updated_at
  ```
- [ ] Create `supplier_account.py` model (API keys)
- [ ] Create `product_cache.py` model (cache scraped data 24h)
- [ ] Create `import_history.py` model (audit log)
- [ ] Run Alembic migration

**Task 2.3: Import Service**
- [ ] Create `import_service.py`
  - `create_import_job(user_id, store_id, source_url, config)`
  - `get_import_job(job_id)`
  - `list_import_jobs(user_id, store_id, filters)`
- [ ] Create `product_normalizer.py`
  - `normalize_aliexpress(raw_data) -> ProductImport`
  - `normalize_cjdropship(raw_data) -> ProductImport`
- [ ] Create `image_service.py`
  - `download_image(url) -> bytes`
  - `optimize_image(bytes) -> bytes` (resize, compress)
  - `upload_to_s3(bytes, key) -> url`

**Task 2.4: API Endpoints**
- [ ] `POST /api/v1/imports` — Create import job
- [ ] `GET /api/v1/imports/{id}` — Get job status
- [ ] `GET /api/v1/imports/history` — List jobs
- [ ] `POST /api/v1/products/preview` — Preview before import

#### Week 4: Celery Tasks & Dashboard

**Task 2.5: Celery Import Task**
- [ ] Create `tasks/import_tasks.py`
  ```python
  @celery_app.task
  def process_import_job(job_id: str):
      # 1. Fetch product data from supplier (use py-suppliers)
      # 2. Normalize data
      # 3. Download & optimize images
      # 4. Calculate pricing with markup
      # 5. Create Supplier record in dropshipping DB
      # 6. Create ProductSupplier link
      # 7. Create Product + ProductVariant records
      # 8. Update import job status
      # 9. Fire platform event: product.created
  ```
- [ ] Test task execution with real AliExpress product

**Task 2.6: Dashboard UI**
- [ ] Create import page: `/imports`
  - Import form (paste URL or search)
  - Job list with status badges
  - Job detail with progress
- [ ] Create supplier accounts page: `/suppliers`
  - Connect AliExpress account
  - Store API keys securely
- [ ] Create product search: `/products/search`
  - Search AliExpress catalog
  - Preview product cards
  - "Import" button on each

**Task 2.7: Integration Test**
- [ ] End-to-end test:
  1. Create import job via API
  2. Celery task processes job
  3. Product appears in dropshipping `products` table
  4. Images uploaded to S3
  5. Supplier linked correctly
- [ ] Verify ServiceBridge fires `product.created` event

**Deliverables:**
- ✅ SourcePilot service operational (backend + dashboard)
- ✅ Single-product import works end-to-end
- ✅ Tests passing (target: 120 tests)

---

## Phase 3: Product Import Pipeline (Weeks 5-6)

### Goals

1. Connect TrendScout → SourcePilot → Dropshipping
2. Implement bulk import
3. Add variant extraction
4. Optimize pricing logic

### Tasks

#### Week 5: TrendScout Integration

**Task 3.1: TrendScout → SourcePilot Webhook**
- [ ] Add webhook endpoint to SourcePilot: `POST /api/v1/webhooks/product-scored`
- [ ] When TrendScout finds high-score product (>= 80):
  - Fire webhook to SourcePilot
  - SourcePilot creates import job
  - Celery task auto-imports product
- [ ] Update TrendScout to call webhook after scoring
- [ ] Add webhook delivery tracking

**Task 3.2: Bulk Import**
- [ ] `POST /api/v1/imports/bulk` endpoint
  - Accept CSV: `source_url,markup_percent,tags`
  - Create batch of import jobs
  - Dispatch Celery group for parallel processing
- [ ] Dashboard: CSV upload UI
- [ ] Test: Import 10 products in parallel

**Task 3.3: Variant Extraction**
- [ ] Enhance `product_normalizer.py`:
  - Parse AliExpress "sku" data (color, size, material)
  - Generate `ProductVariant` records
  - Map variant images correctly
- [ ] Test with multi-variant product
- [ ] Verify variants appear in dropshipping dashboard

#### Week 6: Pricing & Content

**Task 3.4: Advanced Pricing**
- [ ] Create `pricing_service.py`:
  - `calculate_markup(cost, markup_percent) -> retail`
  - `apply_psychological_pricing(price) -> rounded` (e.g., 29.99)
  - `calculate_compare_at_price(retail, discount_pct) -> compare`
- [ ] Support pricing rules: fixed $, percentage, tiered
- [ ] Dashboard: Configure default markup rules per store

**Task 3.5: ContentForge Integration**
- [ ] After import, fire `product.created` event
- [ ] ContentForge webhook receives event
- [ ] ContentForge enhances product description
- [ ] Updates product record with improved content
- [ ] Test: Import product → ContentForge generates content

**Task 3.6: Import History & Analytics**
- [ ] Dashboard page: `/imports/history`
  - Table: product name, supplier, cost, retail, margin, status, date
  - Filters: date range, supplier, store
  - Export CSV
- [ ] Analytics:
  - Total imports this month
  - Average margin
  - Most popular suppliers

**Deliverables:**
- ✅ TrendScout can auto-import products
- ✅ Bulk import via CSV works
- ✅ Variants extracted correctly
- ✅ ContentForge enhances imported products
- ✅ Import history dashboard

---

## Phase 4: Automation Workflows (Weeks 7-8)

### Goals

1. Replace all mock data with real API calls
2. Implement Celery Beat scheduling
3. Add event-based triggers
4. Enable email automation

### Tasks

#### Week 7: Real Data Integration

**Task 4.1: TrendScout — Real Product Research**
- [ ] Replace `_generate_aliexpress_products()` with real API call
- [ ] Integrate Apify for TikTok scraping:
  ```python
  from apify_client import ApifyClient
  def scrape_tiktok_trends(hashtags):
      client = ApifyClient(settings.apify_token)
      run = client.actor("...").call(run_input={...})
      return client.dataset(run["defaultDatasetId"]).iterate_items()
  ```
- [ ] Integrate PRAW for Reddit scanning:
  ```python
  reddit = praw.Reddit(...)
  for post in reddit.subreddit("shutupandtakemymoney").top("week"):
      # Extract product links
  ```
- [ ] Integrate pytrends for Google Trends:
  ```python
  from pytrends.request import TrendReq
  pytrends = TrendReq()
  pytrends.build_payload([keyword], timeframe=...)
  ```
- [ ] Test: Run research with real APIs
- [ ] Verify results are more relevant than mock

**Task 4.2: ContentForge — Real AI Generation**
- [ ] Remove mock content generation
- [ ] Call LLM Gateway for real content:
  ```python
  response = llm_client.generate(
      prompt=f"Generate product description for: {title}",
      model="claude-sonnet-4",
      max_tokens=500
  )
  ```
- [ ] Test: Generate content for 10 products
- [ ] Verify quality and SEO optimization

**Task 4.3: RankPilot — Keyword Research**
- [ ] Integrate SerpAPI for keyword data:
  ```python
  from serpapi import GoogleSearch
  search = GoogleSearch({"q": keyword, "api_key": settings.serpapi_key})
  results = search.get_dict()
  ```
- [ ] Create Celery task: `research_keywords.delay(niche, store_id)`
- [ ] Store results in `Keyword` model
- [ ] Test: Research keywords for "fitness" niche

#### Week 8: Celery Beat & Triggers

**Task 4.4: Celery Beat Schedule**
- [ ] Configure Celery Beat in `celery_app.py`:
  ```python
  beat_schedule = {
      "daily-product-research": {
          "task": "trendscout.tasks.run_all_stores_research",
          "schedule": crontab(hour=8, minute=0),
      },
      "weekly-seo-optimization": {
          "task": "rankpilot.tasks.run_seo_audit",
          "schedule": crontab(day_of_week=1, hour=9, minute=0),
      },
      "daily-price-sync": {
          "task": "sourcepilot.tasks.sync_all_prices",
          "schedule": crontab(hour=3, minute=0),
      },
  }
  ```
- [ ] Test: Celery Beat triggers scheduled tasks

**Task 4.5: Email Flow Triggers**
- [ ] Update FlowSend to listen for platform events:
  - `order.created` → Trigger welcome flow
  - `cart.abandoned` → Trigger abandoned cart flow (TODO: add cart tracking)
  - `order.shipped` → Trigger shipping notification
- [ ] Create Celery tasks for flow execution:
  ```python
  @celery_app.task
  def execute_email_flow(flow_id, contact_id, trigger_data):
      flow = get_flow(flow_id)
      for step in flow.steps:
          if step.delay_hours > 0:
              schedule_email.apply_async(
                  args=[step.email_template_id, contact_id],
                  countdown=step.delay_hours * 3600
              )
  ```
- [ ] Test: Place order → Email sent

**Task 4.6: SendGrid Integration**
- [ ] Remove mock email sending
- [ ] Use SendGrid API:
  ```python
  from sendgrid import SendGridAPIClient
  from sendgrid.helpers.mail import Mail

  message = Mail(
      from_email="noreply@platform.com",
      to_emails=email,
      subject=subject,
      html_content=html
  )
  sg = SendGridAPIClient(settings.sendgrid_api_key)
  response = sg.send(message)
  ```
- [ ] Test: Send 10 real emails

**Deliverables:**
- ✅ All mock data replaced with real APIs
- ✅ Celery Beat running scheduled tasks
- ✅ Email flows triggered by events
- ✅ Real emails sent via SendGrid

---

## Phase 5: Integration & Testing (Weeks 9-10)

### Goals

1. Wire all services together
2. Test complete automation flows
3. Fix integration bugs
4. Add monitoring & error handling

### Tasks

#### Week 9: End-to-End Workflows

**Task 5.1: Complete Automation Flow Test**
- [ ] Scenario: New user creates store
  1. User registers, creates store
  2. TrendScout runs research (real APIs)
  3. High-score products auto-imported via SourcePilot
  4. ContentForge enhances descriptions
  5. RankPilot suggests SEO improvements
  6. Products appear in storefront
  7. User places test order
  8. FlowSend sends order confirmation
- [ ] Document any failures
- [ ] Fix integration bugs

**Task 5.2: ServiceBridge Event Flow**
- [ ] Test all platform events:
  - `product.created` → ContentForge, RankPilot, ShopChat
  - `product.updated` → ContentForge, RankPilot
  - `order.created` → FlowSend, SpyDrop
  - `order.shipped` → FlowSend
  - `customer.created` → FlowSend
- [ ] Verify webhook delivery (check `BridgeDelivery` records)
- [ ] Test webhook failure retry logic
- [ ] Test HMAC signature validation

**Task 5.3: Dashboard Integration**
- [ ] Dropshipping dashboard: Add service status widgets
  - "TrendScout found 12 products this week"
  - "ContentForge enhanced 8 products"
  - "FlowSend sent 156 emails"
- [ ] Add "Import from TrendScout" button on products page
- [ ] Link to SourcePilot from supplier management

#### Week 10: Error Handling & Monitoring

**Task 5.4: Error Handling**
- [ ] Add comprehensive try/catch in all Celery tasks
- [ ] Log errors to Sentry
- [ ] Update task status to 'failed' with error_message
- [ ] Add retry logic for transient failures (network, rate limits)
- [ ] Test: Simulate API failures, verify graceful degradation

**Task 5.5: Monitoring & Alerting**
- [ ] Set up Sentry for error tracking
- [ ] Configure Flower for Celery monitoring
- [ ] Add health check endpoints for all services
- [ ] Set up uptime monitoring (optional: Better Stack)
- [ ] Create Slack/email alerts for critical failures

**Task 5.6: Rate Limiting & Usage Tracking**
- [ ] Enforce plan limits in all services
- [ ] Track API usage per user
- [ ] Add rate limiting to prevent abuse
- [ ] Test: Exceed free plan limits → blocked with upgrade prompt

**Task 5.7: Documentation**
- [ ] Update all service README.md files
- [ ] Document API endpoints (Swagger/OpenAPI)
- [ ] Create user guides for each service
- [ ] Write developer setup guide

**Deliverables:**
- ✅ All services integrated and communicating
- ✅ Complete automation flows tested
- ✅ Error handling and monitoring in place
- ✅ Documentation updated

---

## Phase 6: Infrastructure & Monitoring (Week 11)

### Goals

1. Set up monitoring and alerting
2. Implement rate limiting
3. Configure backup system
4. Add security hardening
5. Deploy health checks

### Tasks

#### Infrastructure Setup

**Task 6.1: Monitoring Stack**
- [ ] Install Sentry for error tracking
  ```bash
  pip install sentry-sdk[fastapi]
  # Add to all services
  ```
- [ ] Configure Sentry DSN in all services
- [ ] Test error capture and alerting
- [ ] Add custom error grouping

**Task 6.2: Metrics & Dashboards**
- [ ] Set up Flower for Celery monitoring
  ```bash
  celery -A app.tasks.celery_app flower --port=5555
  ```
- [ ] Configure Flower authentication
- [ ] Add custom metrics (product imports/day, emails sent, etc.)
- [ ] Create basic dashboards

**Task 6.3: Rate Limiting**
- [ ] Add rate limiting to core API endpoints:
  ```python
  from slowapi import Limiter, _rate_limit_exceeded_handler
  from slowapi.util import get_remote_address

  limiter = Limiter(key_func=get_remote_address)
  app.state.limiter = limiter
  app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

  @app.get("/api/v1/products")
  @limiter.limit("100/minute")
  async def list_products(...):
      ...
  ```
- [ ] Implement per-user rate limits (based on plan)
- [ ] Add 429 responses with retry headers

**Task 6.4: Backup System**
- [ ] Configure automated PostgreSQL backups:
  ```bash
  # Add to K8s CronJob or external backup service
  pg_dump $DATABASE_URL > backup-$(date +%Y%m%d).sql
  aws s3 cp backup-*.sql s3://backups/postgres/
  ```
- [ ] Set up 30-day retention policy
- [ ] Test restore procedure
- [ ] Document backup/restore process

**Task 6.5: Health Checks**
- [ ] Ensure all services have `/health` endpoints
- [ ] Add liveness and readiness probes:
  ```yaml
  livenessProbe:
    httpGet:
      path: /health
      port: 8000
    initialDelaySeconds: 30
    periodSeconds: 10
  ```
- [ ] Test pod restart on failure

**Deliverables:**
- ✅ Sentry capturing errors
- ✅ Flower monitoring Celery
- ✅ Rate limiting active
- ✅ Daily backups configured
- ✅ Health checks operational

---

## Phase 7: Polish & Launch Prep (Week 12)

### Goals

1. UI/UX polish
2. Performance optimization
3. Security audit
4. Beta user onboarding
5. Launch checklist

### Tasks

#### UI/UX & Performance

**Task 7.1: Dashboard Polish**
- [ ] Review all dashboard pages for consistency
- [ ] Add loading states (skeletons)
- [ ] Add empty states with helpful CTAs
- [ ] Fix any UI bugs
- [ ] Test on mobile/tablet

**Task 7.2: Storefront Polish**
- [ ] Test all themes render correctly
- [ ] Optimize page load times
- [ ] Add favicon and og:image for SEO
- [ ] Test checkout flow end-to-end
- [ ] Fix any cart/checkout bugs

**Task 7.3: Performance Optimization**
- [ ] Database query optimization (add indexes)
- [ ] Implement caching (Redis) for frequent queries
- [ ] Optimize image loading (lazy load, WebP)
- [ ] Test with 100 products, 100 orders, 1000 customers
- [ ] Profile slow endpoints, fix bottlenecks

**Task 7.4: Security Audit**
- [ ] Review all API endpoints for auth enforcement
- [ ] Test for SQL injection, XSS vulnerabilities
- [ ] Ensure all secrets are in environment variables (not hardcoded)
- [ ] Enable HTTPS on all services
- [ ] Test JWT expiration and refresh
- [ ] Add rate limiting on auth endpoints

#### Beta Launch Prep

**Task 7.5: Seed Data & Demo**
- [ ] Create comprehensive seed script:
  - 3 demo stores (different niches)
  - 20+ products per store
  - Realistic orders, customers
  - Connected services
- [ ] Create demo video showing automation
- [ ] Prepare pitch deck for beta users

**Task 7.6: Beta User Onboarding**
- [ ] Create welcome email sequence
- [ ] Build onboarding checklist in dashboard:
  - [ ] Create your first store
  - [ ] Connect TrendScout
  - [ ] Import your first product
  - [ ] Customize your theme
  - [ ] View your storefront
- [ ] Set up feedback collection (Typeform or in-app)

**Task 7.7: Launch Checklist**
- [ ] **Infrastructure:**
  - [ ] Production K8s cluster provisioned
  - [ ] Databases backed up daily
  - [ ] Redis cluster configured
  - [ ] S3 buckets created
  - [ ] CDN configured (Cloudflare)
  - [ ] Domain configured (platform.com)
  - [ ] SSL certificates installed
  - [ ] Monitoring dashboards configured
- [ ] **Services:**
  - [ ] All 10 services deployed (dropshipping + 9 SaaS)
  - [ ] Environment variables set
  - [ ] Database migrations run
  - [ ] Celery workers running
  - [ ] Celery Beat scheduled tasks active
- [ ] **Legal & Compliance:**
  - [ ] Terms of Service published
  - [ ] Privacy Policy published
  - [ ] GDPR compliance reviewed
  - [ ] PCI compliance (Stripe handles)
- [ ] **Go-Live:**
  - [ ] Invite 10-20 beta users
  - [ ] Monitor for errors (Sentry)
  - [ ] Respond to feedback quickly
  - [ ] Iterate based on user behavior

**Deliverables:**
- ✅ Polished, production-ready platform
- ✅ Beta users onboarded
- ✅ All systems operational
- ✅ **LAUNCH!** 🚀

---

## Success Criteria

### MVP Definition

The MVP is considered **complete** when:

1. ✅ **Product Sourcing Works**
   - Users can import products from AliExpress via SourcePilot
   - Images download and optimize correctly
   - Variants extract properly
   - Products appear in storefront

2. ✅ **Automation Works**
   - TrendScout finds real products (not mock data)
   - High-score products auto-import to stores
   - ContentForge generates real descriptions
   - Email flows trigger on order events

3. ✅ **Core Commerce Works**
   - Users can create stores
   - Customers can browse, add to cart, checkout
   - Orders process correctly
   - Payments work (Stripe)

4. ✅ **Services Communicate**
   - ServiceBridge dispatches events
   - Services receive and process webhooks
   - Dashboard shows service activity

5. ✅ **Quality Standards**
   - All tests pass (target: 2,000+ tests)
   - No critical bugs
   - Error handling in place
   - Basic monitoring configured

### Launch Metrics

**Week 1 Goals:**
- 10 beta users registered
- 15+ stores created
- 100+ products imported
- 50+ orders placed (test orders)
- < 5% error rate

**Month 1 Goals:**
- 50 active users
- 75+ stores with products
- 500+ products imported
- 200+ real orders
- Positive user feedback (NPS > 40)

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| API rate limits hit | High | Medium | Implement caching, respect rate limits, queue requests |
| Scraping gets blocked | High | Medium | Use Apify (managed proxies), rotate IPs, fallback to API |
| Image optimization slow | Medium | Low | Use async processing, queue with Celery, optimize algorithms |
| Celery tasks fail silently | High | Medium | Add comprehensive error logging, alerts, retry logic |
| Database performance issues | Medium | Low | Index heavily queried columns, use connection pooling |

### Business Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Users don't understand automation | High | Medium | Create tutorial videos, improve onboarding |
| Suppliers change policies | Medium | Medium | Diversify suppliers, monitor policy changes |
| Competition launches similar product | Medium | Medium | Focus on execution, customer support, unique features |
| API costs exceed revenue | High | Low | Monitor usage, enforce plan limits, optimize calls |

### Timeline Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| API integration takes longer | Medium | High | Start with one supplier (AliExpress), add more post-MVP |
| Complex bugs found late | High | Medium | Test continuously, start integration tests early |
| Scope creep | Medium | Medium | Stick to MVP feature list, defer nice-to-haves |

---

## Post-MVP Roadmap

### Phase 7: Additional Suppliers (Weeks 13-14)
- Add CJDropship integration
- Add Spocket integration
- Add inventory sync

### Phase 8: Advanced SEO (Weeks 15-16)
- Automated blog post generation
- Internal linking builder
- Search console integration

### Phase 9: Social Media (Weeks 17-18)
- Meta API integration (Instagram, Facebook)
- Auto-posting on product create
- Analytics dashboard

### Phase 10: Ad Campaigns (Weeks 19-20)
- Google Ads integration
- Meta Ads integration
- Campaign automation

### Phase 11: Analytics & Reporting (Weeks 21-22)
- Advanced analytics dashboard
- Revenue forecasting
- Profit margins tracking
- Supplier performance metrics

### Phase 12: Scale & Optimize (Weeks 23-24)
- Performance optimization
- Database sharding (if needed)
- CDN optimization
- Cost reduction

---

## Appendix A: Service Priority Matrix

| Service | MVP Critical | Post-MVP | Notes |
|---------|--------------|----------|-------|
| Dropshipping Core | ✅ | - | Already 90% complete |
| **SourcePilot (A9)** | **✅** | - | **NEW — CRITICAL** |
| TrendScout (A1) | ✅ | - | Real data integration needed |
| ContentForge (A2) | ✅ | - | Real AI generation needed |
| RankPilot (A3) | ⚠️ | ✅ | Basic SEO for MVP, advanced post-MVP |
| FlowSend (A4) | ✅ | - | Email automation needed |
| SpyDrop (A5) | - | ✅ | Nice to have, not critical |
| PostPilot (A6) | - | ✅ | Social media post-MVP |
| AdScale (A7) | - | ✅ | Ad campaigns post-MVP |
| ShopChat (A8) | ⚠️ | ✅ | Basic chat for MVP, enhance post-MVP |
| LLM Gateway | ✅ | - | Already complete |
| Admin Dashboard | ✅ | - | Already complete |

---

## Appendix B: Estimated Effort Breakdown

| Phase | Backend | Frontend | Testing | Total |
|-------|---------|----------|---------|-------|
| 1: Foundation | 60h | 0h | 10h | 70h |
| 2: SourcePilot | 50h | 20h | 10h | 80h |
| 3: Import Pipeline | 40h | 20h | 10h | 70h |
| 4: Automation | 50h | 10h | 10h | 70h |
| 5: Integration | 30h | 20h | 20h | 70h |
| 6: Polish | 20h | 30h | 10h | 60h |
| **Total** | **250h** | **100h** | **70h** | **420h** |

**At 40h/week:** 10.5 weeks (round to 11-12 weeks with buffer)

---

## Appendix C: Technology Dependencies

```python
# New dependencies for MVP

# Supplier Integrations
playwright==1.41.0          # Web scraping
playwright-python==0.2.0    # Async Playwright
apify-client==1.6.0         # TikTok scraping

# Social Media & Trends
praw==7.7.1                 # Reddit API
pytrends==4.9.2             # Google Trends

# Email & Marketing
sendgrid==6.11.0            # Email delivery
jinja2==3.1.3               # Email templates (already installed)

# SEO & Content
serpapi==2.4.2              # Keyword research
beautifulsoup4==4.12.3      # HTML parsing

# Image Processing
pillow==10.2.0              # Image optimization
boto3==1.34.34              # S3 upload (already installed)

# API Clients
requests==2.31.0            # HTTP requests (already installed)
httpx==0.26.0               # Async HTTP (already installed)

# Utilities
python-dotenv==1.0.0        # Environment variables (already installed)
pydantic-settings==2.1.0    # Settings management (already installed)
```

---

**Document Status:** Ready for Implementation
**Next Step:** Review and approve this plan, then begin Phase 1.

---

*Last Updated: 2026-02-14*
*Version: 1.0*
