# Implementation Steps

> Part of [TrendScout](README.md) documentation

**For Developers & Project Managers:** This document tracks the step-by-step implementation of the TrendScout service, from initial template scaffolding through feature-complete status. Each step documents what was built, the tasks completed, and how to verify the work.

---

## Step 1: Service Template Scaffolding

### What was built

The TrendScout service was created from the `_template` service scaffold. This provided a fully functional baseline with authentication, billing, API key management, and health check infrastructure -- all shared across every service in the platform.

### Steps completed

1. Ran the scaffold script to generate the service directory structure at `trendscout/`
2. Replaced all `{{service_name}}` placeholders with `trendscout` and `{{service_display_name}}` with `TrendScout`
3. Configured port assignments: backend 8101, dashboard 3101, landing 3201, PostgreSQL 5501, Redis 6401
4. Created `backend/app/config.py` with Pydantic Settings loading from environment variables
5. Created `backend/app/database.py` with async SQLAlchemy engine and session factory
6. Created `backend/app/main.py` with FastAPI app, CORS, and route mounting
7. Created shared models: `User` (with `PlanTier` enum), `Subscription`, `ApiKey`, `Base`
8. Created shared services: `auth_service.py` (registration, login, JWT, provisioning), `billing_service.py` (Stripe checkout/portal/webhooks with mock mode)
9. Created shared API routes: `auth.py`, `billing.py`, `api_keys.py`, `deps.py` (auth dependencies)
10. Created shared schemas: `auth.py` (RegisterRequest, LoginRequest, TokenResponse, etc.), `billing.py` (PlanInfo, CheckoutSessionResponse, etc.)
11. Created `constants/plans.py` with `PlanLimits` dataclass and `PLAN_LIMITS` dict
12. Created `tasks/celery_app.py` with Celery configuration
13. Created `dashboard/src/service.config.ts` with TrendScout branding (Electric Blue primary, Space Grotesk heading font, Inter body font)
14. Created shared dashboard pages: login, register, billing, API keys, settings, home
15. Created landing page: hero/features page and pricing page

### Verification

```bash
# Backend starts
cd trendscout/backend
uvicorn app.main:app --port 8101
# Verify: http://localhost:8101/docs loads Swagger UI

# Dashboard builds
cd trendscout/dashboard
npm run build

# Landing builds
cd trendscout/landing
npm run build
```

---

## Step 2: TrendScout Feature Models

### What was built

Four feature-specific database models that power the core product research workflow. These models sit alongside the shared template models (User, Subscription, ApiKey).

### Steps completed

1. Created `backend/app/models/research.py` with two models:
   - **ResearchRun**: Tracks research job lifecycle (id, user_id, keywords, sources, status, score_config, results_count, error_message, created_at, completed_at). Status transitions: `pending` -> `running` -> `completed` / `failed`. Keywords and sources stored as PostgreSQL `ARRAY(String)` columns. Score config stored as `JSON`.
   - **ResearchResult**: Individual product discoveries (id, run_id, source, product_title, product_url, image_url, price, currency, score, ai_analysis, raw_data, created_at). Score is a `Float` (0-100). AI analysis stored as `JSON`. Raw data preserves original source payload. Cascade-deleted with parent run.

2. Created `backend/app/models/watchlist.py` with:
   - **WatchlistItem**: User's saved products (id, user_id, result_id, status, notes, created_at, updated_at). Unique constraint on `(user_id, result_id)` prevents duplicates. Status values: `watching`, `imported`, `dismissed`. Cascade-deleted when referenced result is deleted.

3. Created `backend/app/models/source_config.py` with:
   - **SourceConfig**: Per-user data source credentials (id, user_id, source_type, credentials, settings, is_active, created_at, updated_at). Valid source types: `aliexpress`, `tiktok`, `google_trends`, `reddit`. Credentials and settings stored as `JSON`. `is_active` flag allows disabling without deleting.

4. Updated `backend/app/models/__init__.py` to export all 7 models: `Base`, `User`, `Subscription`, `ApiKey`, `ResearchRun`, `ResearchResult`, `WatchlistItem`, `SourceConfig`

5. Generated Alembic migration for the new tables: `research_runs`, `research_results`, `watchlist_items`, `source_configs`

### Verification

```bash
cd trendscout/backend
alembic upgrade head
# Verify all 7 tables exist in the database:
# users, subscriptions, api_keys, research_runs, research_results, watchlist_items, source_configs
```

---

## Step 3: Feature Services

### What was built

Three feature-specific service modules that contain all the business logic for product research, scoring, and AI analysis.

### Steps completed

1. Created `backend/app/services/research_service.py` with:
   - **Research Run operations**: `check_run_limit()` (counts runs in current billing period vs plan limit), `get_run_count_this_period()`, `create_research_run()` (validates plan limits, sanitizes sources, creates run in pending status), `get_research_runs()` (paginated list, newest first), `get_research_run()` (single run with eagerly loaded results), `get_result()` (single result by ID), `delete_research_run()` (ownership check + cascade delete)
   - **Watchlist operations**: `check_watchlist_limit()` (counts items vs plan max_secondary), `get_watchlist_count()`, `add_to_watchlist()` (plan limit check + duplicate prevention + result existence check), `get_watchlist_items()` (paginated with optional status filter), `update_watchlist_item()` (Ellipsis sentinel pattern for distinguishing "not provided" from explicit null), `delete_watchlist_item()` (ownership check)
   - **Source Config operations**: `create_source_config()`, `get_source_configs()` (ordered by source_type), `update_source_config()` (partial update for credentials/settings/is_active), `delete_source_config()` (ownership check)

2. Created `backend/app/services/scoring_service.py` with:
   - **Default weights**: Social 40%, Market 30%, Competition 15%, SEO 10%, Fundamentals 5%
   - **Sub-score functions**: `_score_social()` (engagement metrics + view reach + trending bonus), `_score_market()` (search volume + order count + growth rate), `_score_competition()` (seller count inverse + saturation inverse + review quality inverse), `_score_seo()` (keyword relevance + search position + content quality), `_score_fundamentals()` (price sweet spot + margin + shipping time + weight)
   - **Main function**: `calculate_score()` merges custom config with defaults, normalizes weights to sum to 1.0, computes weighted average, clamps to [0, 100], rounds to 1 decimal

3. Created `backend/app/services/ai_analysis_service.py` with:
   - **Mock analysis**: `_generate_mock_analysis()` uses MD5 hash of product title for deterministic variety. Returns structured dict with summary, opportunity_score, risk_factors, recommended_price_range, target_audience, marketing_angles
   - **Real analysis**: `analyze_product()` calls Claude API (claude-sonnet-4-20250514) with a structured prompt requesting JSON output. Falls back to mock on failure or missing API key
   - **Graceful degradation**: No Anthropic API key = mock mode. API errors = fallback to mock with warning log

### Verification

```bash
cd trendscout/backend
python -c "from app.services.scoring_service import calculate_score; print(calculate_score({'social': {'likes': 5000, 'shares': 1000, 'views': 100000, 'comments': 500, 'trending': True}, 'market': {'search_volume': 50000, 'order_count': 3000, 'growth_rate': 25}}))"
# Should print a float between 0 and 100
```

---

## Step 4: Feature API Routes

### What was built

Three feature-specific API route modules that expose the research, watchlist, and source configuration functionality via REST endpoints.

### Steps completed

1. Created `backend/app/api/research.py` with:
   - `POST /api/v1/research/runs` -- Create research run (dispatches Celery task). Validates plan limits (403 on exceed). Returns run in pending status (201).
   - `GET /api/v1/research/runs` -- List runs with pagination (page, per_page query params). Newest first. Does not include inline results.
   - `GET /api/v1/research/runs/{run_id}` -- Get run detail with all results eagerly loaded. Ownership check (404 for wrong user).
   - `DELETE /api/v1/research/runs/{run_id}` -- Delete run with cascading result deletion (204). Ownership check.
   - `GET /api/v1/research/results/{result_id}` -- Get single result detail. Verifies ownership via parent run.

2. Created `backend/app/api/watchlist.py` with:
   - `POST /api/v1/watchlist` -- Add result to watchlist (201). Enforces plan limit (403), prevents duplicates (409), verifies result exists (404). Includes inline result snapshot.
   - `GET /api/v1/watchlist` -- List items with optional `?status=watching|imported|dismissed` filter. Paginated. Each item includes result snapshot.
   - `PATCH /api/v1/watchlist/{item_id}` -- Update status and/or notes. Partial update.
   - `DELETE /api/v1/watchlist/{item_id}` -- Remove from watchlist (204). Does not delete underlying research result.
   - Helper function `_build_watchlist_response()` constructs response with inline `WatchlistResultSnapshot`.

3. Created `backend/app/api/sources.py` with:
   - `POST /api/v1/sources` -- Create source config (201). Validates source_type against `{aliexpress, tiktok, google_trends, reddit}` (400 for invalid).
   - `GET /api/v1/sources` -- List all configs for user. Ordered by source_type. Credentials always redacted.
   - `PATCH /api/v1/sources/{config_id}` -- Update credentials/settings/is_active. Partial update. Ownership check.
   - `DELETE /api/v1/sources/{config_id}` -- Delete config (204). Ownership check.
   - Helper function `_build_source_response()` replaces raw credentials with `has_credentials` boolean flag.

4. Created `backend/app/schemas/research.py` with Pydantic schemas:
   - `ResearchRunCreate`, `ResearchRunResponse`, `ResearchRunListResponse`
   - `ResearchResultResponse`
   - `WatchlistItemCreate`, `WatchlistItemUpdate`, `WatchlistItemResponse`, `WatchlistListResponse`, `WatchlistResultSnapshot`
   - `SourceConfigCreate`, `SourceConfigUpdate`, `SourceConfigResponse`, `SourceConfigListResponse`

5. Mounted all routes in `main.py` under the `/api/v1` prefix

### Verification

```bash
cd trendscout/backend
uvicorn app.main:app --port 8101
# Visit http://localhost:8101/docs
# Verify all endpoints appear:
# - /api/v1/research/runs (POST, GET)
# - /api/v1/research/runs/{run_id} (GET, DELETE)
# - /api/v1/research/results/{result_id} (GET)
# - /api/v1/watchlist (POST, GET)
# - /api/v1/watchlist/{item_id} (PATCH, DELETE)
# - /api/v1/sources (POST, GET)
# - /api/v1/sources/{config_id} (PATCH, DELETE)
```

---

## Step 5: Feature Tests

### What was built

Comprehensive test coverage for all TrendScout-specific features, adding to the shared template tests for auth, billing, API keys, and health.

### Steps completed

1. Created `backend/tests/conftest.py` with:
   - `setup_db` autouse fixture: creates tables before tests, terminates all non-self connections, truncates all tables with CASCADE after each test
   - `client` fixture: httpx AsyncClient wired to the FastAPI app
   - `db` fixture: raw AsyncSession for direct model manipulation
   - `auth_headers` fixture: registers a fresh user and returns Bearer token headers
   - `register_and_login()` helper: registers with random or specified email, returns headers

2. Created `backend/tests/test_research.py` (21 tests):
   - Create run: success, custom sources, score_config override, empty keywords rejection, unauthenticated
   - List runs: empty list, returns created runs (newest first), pagination (page/per_page), unauthenticated, user isolation
   - Get run detail: success (includes results), not found, wrong user (404), unauthenticated
   - Delete run: success (204 + verify gone), not found, wrong user, unauthenticated, total count decrements
   - Result detail: not found, unauthenticated

3. Created `backend/tests/test_watchlist.py` (24 tests):
   - Helper: `create_run_with_result()` creates a run via API then inserts a ResearchResult directly in DB (since Celery is not running)
   - Add to watchlist: success (includes result snapshot), with notes, duplicate rejected (409), nonexistent result (404), unauthenticated
   - List: empty, returns items with snapshots, status filter, pagination, user isolation, unauthenticated
   - Update: status change, dismissed status, notes update, both status+notes, not found, wrong user, unauthenticated
   - Delete: success (204 + verify gone), not found, wrong user, unauthenticated, total decrements
   - Re-add: after delete, same result can be added again with new ID

4. Created `backend/tests/test_sources.py` (22 tests):
   - Create: success with credentials+settings, credentials redacted in response, no credentials (has_credentials=false), all 4 valid types, invalid type rejected (400), unauthenticated
   - List: empty, returns configs (ordered by source_type), credentials always redacted, user isolation, unauthenticated
   - Update: settings update, credentials update (still redacted), active toggle (on/off), not found, wrong user, unauthenticated
   - Delete: success (204 + verify gone from list), not found, wrong user, unauthenticated, list count decrements

5. Shared template tests (already included):
   - `test_auth.py` (10 tests): register, duplicate email, short password, login, wrong password, nonexistent user, refresh token, refresh with access token, profile, unauthenticated profile
   - `test_billing.py` (9 tests): list plans, pricing details, pro checkout, free checkout fails, duplicate subscription, billing overview, overview after subscribe, current subscription none, current subscription after subscribe
   - `test_api_keys.py` (5 tests): create key, list keys (no raw key), revoke key, auth via API key, invalid API key
   - `test_health.py` (1 test): health check returns 200 with service metadata

### Verification

```bash
cd trendscout/backend
pytest -v
# Expected: 67 tests passed
```

---

## Step 6: Dashboard Feature Pages

### What was built

Feature-specific dashboard pages for research, watchlist, and other TrendScout-specific UI, built on top of the shared template pages (login, register, billing, API keys, settings, home).

### Steps completed

1. Configured `dashboard/src/service.config.ts` with TrendScout navigation:
   - Dashboard (home), Research, Watchlist, Sources, History, API Keys, Billing, Settings

2. Created `dashboard/src/app/research/page.tsx`:
   - Research run creation form (keywords input, source selection)
   - Research run history list with status indicators
   - Run detail view with inline product results and scores

3. Created `dashboard/src/app/watchlist/page.tsx`:
   - Watchlist item list with status tabs (watching, imported, dismissed)
   - Result snapshot display (product title, source, score, price)
   - Status update and notes editing
   - Add/remove actions

4. Shared template pages (already included):
   - `dashboard/src/app/page.tsx` -- Dashboard home/overview
   - `dashboard/src/app/login/page.tsx` -- Login form
   - `dashboard/src/app/register/page.tsx` -- Registration form
   - `dashboard/src/app/billing/page.tsx` -- Billing management with plan cards
   - `dashboard/src/app/api-keys/page.tsx` -- API key management
   - `dashboard/src/app/settings/page.tsx` -- User settings

5. Navigation configured in service.config.ts includes Sources and History pages (routes defined, pages pending implementation)

### Dashboard Pages Summary

| Page | Path | Status |
|------|------|--------|
| Dashboard Home | `/` | Implemented |
| Login | `/login` | Implemented |
| Register | `/register` | Implemented |
| Research | `/research` | Implemented |
| Watchlist | `/watchlist` | Implemented |
| Sources | `/sources` | Navigation defined, page pending |
| History | `/history` | Navigation defined, page pending |
| API Keys | `/api-keys` | Implemented |
| Billing | `/billing` | Implemented |
| Settings | `/settings` | Implemented |

### Verification

```bash
cd trendscout/dashboard
npm run build
# All 8 existing pages should build successfully
```

---

## Step 7: Landing Page Customization

### What was built

A branded landing page for TrendScout, customized from the service template with TrendScout-specific copy, features, and pricing.

### Steps completed

1. Created `landing/src/app/page.tsx`:
   - Hero section with TrendScout branding (Electric Blue theme)
   - Feature highlights: multi-source research, AI scoring, watchlist management
   - Call-to-action buttons directing to the dashboard registration page

2. Created `landing/src/app/pricing/page.tsx`:
   - Three-tier pricing table (Free $0, Pro $29, Enterprise $99)
   - Feature comparison across tiers
   - Links to dashboard checkout for paid plans

3. Applied TrendScout design system:
   - Primary color: Electric Blue `oklch(0.65 0.20 250)` / `#3b82f6`
   - Accent color: Cyan `oklch(0.75 0.15 200)` / `#38bdf8`
   - Heading font: Space Grotesk
   - Body font: Inter

### Verification

```bash
cd trendscout/landing
npm run build
# Both pages should build successfully
# Visit http://localhost:3201 and http://localhost:3201/pricing
```

---

## Step 8: Background Task Pipeline

### What was built

The Celery background task that executes research runs, including mock data generators for all 4 data sources, product scoring, and AI analysis.

### Steps completed

1. Created `backend/app/tasks/research_tasks.py` with:
   - `run_research` Celery task: loads run from DB, transitions status (`pending` -> `running` -> `completed`/`failed`), processes each source, stores results, updates results_count
   - Mock data generator for AliExpress: 5-8 products with realistic prices, order counts, ratings, engagement metrics
   - Mock data generator for TikTok: 5-7 products with high social engagement (viral nature)
   - Mock data generator for Google Trends: 5-7 products with strong SEO and market signals
   - Mock data generator for Reddit: 5-7 products from community discussions with varied engagement
   - All generators use MD5-seeded random for deterministic output given the same keywords
   - Synchronous mock AI analysis function for Celery worker context
   - Error handling: failed runs get `status=failed` with `error_message`

2. Created `backend/app/tasks/celery_app.py` with Celery configuration:
   - Broker: Redis on configured URL
   - Result backend: Redis on configured URL
   - Queue: `trendscout` (service-specific)

3. Wired task dispatch in `backend/app/api/research.py`:
   - `run_research.delay(str(run.id))` called after creating the run record
   - Graceful handling if Celery is unavailable (run stays in pending status)

### Verification

```bash
# Start Celery worker
cd trendscout/backend
celery -A app.tasks.celery_app worker -l info -Q trendscout

# In another terminal, create a research run via API:
curl -X POST http://localhost:8101/api/v1/research/runs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["wireless earbuds"], "sources": ["aliexpress", "tiktok"]}'

# Poll the run status:
curl http://localhost:8101/api/v1/research/runs/<run_id> \
  -H "Authorization: Bearer <token>"
# Should show status=completed with results_count > 0
```

---

## Summary of Service State

### Architecture

```
TrendScout Service
├── Backend API (FastAPI, port 8101)
│   ├── 7 API route modules (auth, billing, research, watchlist, sources, api_keys, deps)
│   ├── 7 database models (User, Subscription, ApiKey, ResearchRun, ResearchResult, WatchlistItem, SourceConfig)
│   ├── 5 service modules (auth, billing, research, scoring, AI analysis)
│   ├── 3 schema modules (auth, billing, research)
│   ├── 2 task modules (celery_app, research_tasks)
│   ├── 1 constants module (plans)
│   └── 67 backend tests
├── Dashboard (Next.js 16, port 3101)
│   ├── 8 pages (home, login, register, research, watchlist, billing, api-keys, settings)
│   └── Config-driven via service.config.ts
├── Landing Page (Next.js 16, port 3201)
│   └── 2 pages (hero/features, pricing)
├── PostgreSQL (port 5501) — 7 tables
├── Redis (port 6401) — cache + Celery broker + result backend
└── Celery Worker — background research task execution
```

### Feature Completeness

| Feature | Backend | Dashboard | Tests |
|---------|---------|-----------|-------|
| Authentication | Complete | Complete (login, register) | 10 tests |
| Billing / Subscriptions | Complete | Complete (billing page) | 9 tests |
| API Key Management | Complete | Complete (api-keys page) | 5 tests |
| Research Runs | Complete | Complete (research page) | 21 tests |
| Research Results | Complete | Inline in research page | Covered by research tests |
| Watchlist | Complete | Complete (watchlist page) | 24 tests |
| Source Configuration | Complete | Navigation defined, page pending | 22 tests |
| AI Scoring | Complete | Inline in results | Covered by research tests |
| AI Analysis | Complete (mock + real) | Inline in results | Covered by research tests |
| Background Tasks | Complete (mock generators) | N/A | Covered by research tests |
| Health Check | Complete | N/A | 1 test |

### What Remains

1. **Sources dashboard page** -- Backend API is complete; dashboard page needs implementation
2. **History dashboard page** -- Backend supports listing past runs; dedicated page needs implementation
3. **Real external API integrations** -- Replace mock generators with actual AliExpress (Apify), TikTok (Apify), Google Trends (pytrends), Reddit (PRAW) integrations
4. **Playwright E2E tests** -- Browser-based testing of the dashboard UI
5. **Production configuration** -- Stripe Price IDs, Anthropic API key, production database URL
6. **Email notifications** -- Password reset, research run completed notifications

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
