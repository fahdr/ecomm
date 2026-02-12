# RankPilot Implementation Steps

This document records the implementation history of the RankPilot service, from initial template scaffolding through all domain models, services, API routes, tests, and frontend pages. Each step describes what was built, the specific steps completed, and how to verify the work.

---

## Step 1: Template Scaffolding

### What Was Built

The RankPilot service was scaffolded from the shared service template, providing the foundational project structure, standard auth/billing/API key infrastructure, and Docker configuration.

### Steps Completed

1. Ran `scripts/create-service.sh` with service name `rankpilot`, slug `rankpilot`, port base `103`.
2. Template placeholders were replaced with RankPilot-specific values across all files.
3. `docker-compose.yml` configured with ports: backend 8103, dashboard 3103, landing 3203, PostgreSQL 5503, Redis 6403.
4. `backend/app/config.py` configured with service-specific settings.
5. `backend/app/main.py` created as FastAPI application entry point.
6. `backend/app/database.py` configured with async SQLAlchemy engine and session factory.
7. Standard route files scaffolded: `auth.py`, `deps.py`, `health.py`, `billing.py`, `api_keys.py`, `usage.py`, `webhooks.py`.
8. Standard models scaffolded: `base.py`, `user.py` (with `PlanTier` enum), `subscription.py`, `api_key.py`.
9. Standard services scaffolded: `auth_service.py`, `billing_service.py`.
10. Standard schemas scaffolded: `auth.py`, `billing.py`.
11. Celery app configured in `tasks/celery_app.py`.
12. Alembic configured with `env.py` for async migrations.
13. `Makefile` created with install, migrate, start, test targets.
14. Dashboard scaffolded with Next.js 16 App Router, Tailwind CSS, and shared UI components.
15. `service.config.ts` populated with RankPilot branding (Emerald Green, General Sans/Inter fonts).
16. Standard dashboard pages scaffolded: `login`, `register`, `billing`, `api-keys`, `settings`.
17. Landing page scaffolded with static Next.js export on port 3203.

### Verification

- `make install` completes without errors.
- `make migrate` applies initial migration.
- `make start` starts backend on port 8103 and dashboard on port 3103.
- `GET /api/v1/health` returns `{"status": "ok", "service": "rankpilot", ...}`.
- Standard auth flow works: register, login, refresh, profile.
- Standard billing flow works: list plans (3 tiers), mock checkout.

---

## Step 2: Sites Model and Service

### What Was Built

The `sites` table and full CRUD + domain verification for site (domain) management. Sites are the top-level resource that all other features depend on.

### Steps Completed

1. Created `backend/app/models/site.py` with the `Site` model:
   - Fields: `id` (UUID PK), `user_id` (FK to users), `domain` (String 255, indexed), `sitemap_url` (optional), `verification_method` (optional), `is_verified` (Boolean, default False), `last_crawled` (optional DateTime), `status` (String, default "pending"), `created_at`, `updated_at`.
   - Relationships: `owner` (to User), `blog_posts`, `keyword_trackings`, `seo_audits`, `schema_configs` (all with cascade delete-orphan).
2. Registered `Site` in `models/__init__.py` for Alembic detection.
3. Created `backend/app/services/site_service.py` with functions:
   - `create_site(db, user, domain, sitemap_url)` -- checks duplicate domain per user.
   - `get_site(db, site_id, user_id)` -- scoped to user.
   - `list_sites(db, user_id, page, per_page)` -- paginated.
   - `update_site(db, site, domain, sitemap_url, status)` -- sentinel pattern for sitemap_url.
   - `delete_site(db, site)` -- cascades to all related data.
   - `verify_site(db, site)` -- mock verification (always succeeds).
   - `count_user_sites(db, user_id)` -- for future plan limit checks.
4. Created `backend/app/schemas/seo.py` with Pydantic schemas: `SiteCreate`, `SiteUpdate`, `SiteResponse`.
5. Created `backend/app/api/sites.py` with route handlers:
   - `POST /sites` -- create site (201).
   - `GET /sites` -- list sites with pagination.
   - `GET /sites/{site_id}` -- get by ID.
   - `PATCH /sites/{site_id}` -- update fields.
   - `DELETE /sites/{site_id}` -- delete (204).
   - `POST /sites/{site_id}/verify` -- verify ownership.
6. Registered sites router in `main.py`.
7. Generated Alembic migration for the `sites` table.

### Verification

- 20 tests pass in `test_sites.py`.
- Create, list, get, update, delete, and verify all work.
- Cross-user isolation confirmed (other user's site returns 404).
- Duplicate domain per user returns 400.
- Domain shorter than 3 characters returns 422.

---

## Step 3: Blog Posts Model and Service

### What Was Built

The `blog_posts` table and full CRUD with AI content generation, slug generation, word counting, and monthly plan limit enforcement.

### Steps Completed

1. Created `backend/app/models/blog_post.py` with the `BlogPost` model:
   - Fields: `id` (UUID PK), `site_id` (FK to sites), `user_id` (FK to users), `title` (String 500), `slug` (String 500, indexed), `content` (TEXT), `meta_description` (String 320, optional), `keywords` (ARRAY of String), `status` (String, default "draft"), `word_count` (Integer, default 0), `published_at` (optional DateTime), `created_at`, `updated_at`.
   - Relationship: `site` (back_populates to Site.blog_posts).
2. Registered `BlogPost` in `models/__init__.py`.
3. Created `backend/app/services/blog_service.py` with functions:
   - `generate_slug(title)` -- converts title to URL-safe slug.
   - `count_words(content)` -- counts words by whitespace splitting.
   - `count_monthly_posts(db, user_id)` -- counts posts created in current calendar month.
   - `create_blog_post(db, user, site_id, title, content, meta_description, keywords)` -- generates slug and calculates word count.
   - `get_blog_post(db, post_id, user_id)` -- scoped to user.
   - `list_blog_posts(db, user_id, site_id, page, per_page)` -- paginated, optional site filter.
   - `update_blog_post(db, post, title, content, meta_description, keywords, status)` -- recalculates slug/word_count, sets published_at on publish.
   - `delete_blog_post(db, post)`.
   - `generate_blog_content(db, post)` -- mock AI generation producing ~300-word SEO article with headings, bullet points, and conclusion; auto-generates meta_description if not set.
4. Added blog post schemas to `schemas/seo.py`: `BlogPostCreate`, `BlogPostUpdate`, `BlogPostGenerate`, `BlogPostResponse`.
5. Created `backend/app/api/blog_posts.py` with route handlers:
   - `POST /blog-posts` -- create (201), enforces `PLAN_LIMITS[user.plan].max_items` monthly cap.
   - `GET /blog-posts` -- list with optional `site_id` filter and pagination.
   - `GET /blog-posts/{post_id}` -- get by ID.
   - `PATCH /blog-posts/{post_id}` -- update fields.
   - `DELETE /blog-posts/{post_id}` -- delete (204).
   - `POST /blog-posts/generate` -- AI content generation for existing post.
6. Registered blog_posts router in `main.py`.
7. Generated Alembic migration for the `blog_posts` table.

### Verification

- 25 tests pass in `test_blog.py`.
- Create with content calculates word_count.
- Keywords stored as ARRAY.
- AI generation fills content and meta_description.
- Publishing sets published_at timestamp.
- Cross-user post access returns 404.
- Empty title returns 422.
- Non-existent site_id returns 404.

---

## Step 4: Keyword Tracking Model and Service

### What Was Built

The `keyword_tracking` table and CRUD with rank refresh functionality, duplicate detection, and plan limit enforcement on total keyword count.

### Steps Completed

1. Created `backend/app/models/keyword.py` with the `KeywordTracking` model:
   - Fields: `id` (UUID PK), `site_id` (FK to sites), `keyword` (String 255), `current_rank` (Integer, optional), `previous_rank` (Integer, optional), `search_volume` (Integer, optional), `difficulty` (Float, optional), `tracked_since` (DateTime, auto-set), `last_checked` (DateTime, optional).
   - Relationship: `site` (back_populates to Site.keyword_trackings).
2. Registered `KeywordTracking` in `models/__init__.py`.
3. Created `backend/app/services/keyword_service.py` with functions:
   - `add_keyword(db, site_id, keyword)` -- checks for duplicate within same site.
   - `list_keywords(db, site_id, page, per_page)` -- paginated.
   - `get_keyword(db, keyword_id, site_id)` -- scoped to site.
   - `delete_keyword(db, tracking)`.
   - `count_site_keywords(db, site_id)` -- per-site count.
   - `count_user_keywords(db, user_id)` -- total across all user's sites (JOIN on sites table).
   - `update_keyword_ranks_for_site(db, site_id)` -- mock rank update: assigns random rank (1-100), search volume (100-50000), difficulty (10.0-90.0); preserves previous_rank for trend tracking.
4. Added keyword schemas to `schemas/seo.py`: `KeywordTrackingCreate`, `KeywordTrackingResponse`.
5. Created `backend/app/api/keywords.py` with route handlers:
   - `POST /keywords` -- add keyword (201), enforces `PLAN_LIMITS[user.plan].max_secondary` total keyword cap.
   - `GET /keywords` -- list by site_id (required query param) with pagination.
   - `DELETE /keywords/{keyword_id}` -- remove (204), requires site_id query param.
   - `POST /keywords/refresh` -- refresh ranks for all keywords in a site.
6. Registered keywords router in `main.py`.
7. Generated Alembic migration for the `keyword_tracking` table.

### Verification

- 16 tests pass in `test_keywords.py`.
- Duplicate keyword for same site returns 400.
- Keywords scoped to site; non-existent site returns 404.
- Rank refresh returns updated count.
- Cross-user keyword operations return 404.
- Pagination works correctly.

---

## Step 5: SEO Audits Model and Service

### What Was Built

The `seo_audits` table and audit execution with mock scoring, issue generation, and recommendation generation. Audit history with pagination.

### Steps Completed

1. Created `backend/app/models/seo_audit.py` with the `SeoAudit` model:
   - Fields: `id` (UUID PK), `site_id` (FK to sites), `overall_score` (Float, 0-100), `issues` (JSON, list of issue objects), `recommendations` (JSON, list of strings), `pages_crawled` (Integer), `created_at` (DateTime, auto-set).
   - Relationship: `site` (back_populates to Site.seo_audits).
2. Registered `SeoAudit` in `models/__init__.py`.
3. Created `backend/app/services/audit_service.py` with functions:
   - `run_audit(db, site)` -- generates mock audit with:
     - 12 issue templates across 5 categories (meta_tags, performance, content, technical, mobile) and 3 severity levels (critical, warning, info).
     - 12 recommendation templates covering meta descriptions, image optimization, structured data, heading tags, alt text, caching, sitemaps, HTTPS, Core Web Vitals, internal linking, mobile design, server response time.
     - Score calculated: `100 - (critical_count * 15) - (warning_count * 5) +/- random noise`, clamped to 0-100.
     - Updates `site.last_crawled` timestamp.
   - `get_audit(db, audit_id)`.
   - `list_audits(db, site_id, page, per_page)` -- sorted by most recent first.
4. Added audit schemas to `schemas/seo.py`: `SeoAuditRun`, `SeoAuditResponse`.
5. Created `backend/app/api/audits.py` with route handlers:
   - `POST /audits/run` -- run audit (201), verifies site ownership.
   - `GET /audits` -- list audit history by site_id with pagination.
   - `GET /audits/{audit_id}` -- get by ID, verifies site ownership.
6. Registered audits router in `main.py`.
7. Generated Alembic migration for the `seo_audits` table.

### Verification

- 15 tests pass in `test_audits.py`.
- Audit score is between 0 and 100.
- Issues contain severity, category, and message fields.
- Multiple audits for same site create separate records with unique IDs.
- Cross-user audit access returns 404.
- Non-existent site returns 404.
- Pagination works correctly.

---

## Step 6: Schema Markup Model and Service

### What Was Built

The `schema_configs` table and full CRUD for JSON-LD structured data management, with default template generation for 5 page types and a preview endpoint that renders HTML script tags.

### Steps Completed

1. Created `backend/app/models/schema_config.py` with the `SchemaConfig` model:
   - Fields: `id` (UUID PK), `site_id` (FK to sites), `page_type` (String 50), `schema_json` (JSON), `is_active` (Boolean, default True), `created_at`, `updated_at`.
   - Relationship: `site` (back_populates to Site.schema_configs).
2. Registered `SchemaConfig` in `models/__init__.py`.
3. Created `backend/app/services/schema_service.py` with functions:
   - `generate_default_schema(page_type, domain)` -- produces schema.org-compliant JSON-LD templates for 5 types:
     - **product**: Product with Offer, AggregateRating, Brand.
     - **article**: Article with author (Person), publisher (Organization with logo).
     - **faq**: FAQPage with mainEntity list of Question/Answer pairs.
     - **breadcrumb**: BreadcrumbList with ordered ListItem entries.
     - **organization**: Organization with contactPoint, sameAs social links.
   - `create_schema_config(db, site_id, page_type, schema_json, domain)` -- uses default template if no custom JSON provided.
   - `get_schema_config(db, config_id)`.
   - `list_schema_configs(db, site_id, page, per_page)` -- paginated.
   - `update_schema_config(db, config, schema_json, is_active)`.
   - `delete_schema_config(db, config)`.
   - `render_json_ld(schema_json)` -- renders `<script type="application/ld+json">\n{formatted JSON}\n</script>`.
4. Added schema schemas to `schemas/seo.py`: `SchemaConfigCreate`, `SchemaConfigUpdate`, `SchemaConfigResponse`.
5. Created `backend/app/api/schema.py` with route handlers:
   - `POST /schema` -- create (201), verifies site ownership, generates default template if needed.
   - `GET /schema` -- list by site_id with pagination.
   - `GET /schema/{config_id}` -- get by ID.
   - `PATCH /schema/{config_id}` -- update schema_json and/or is_active.
   - `DELETE /schema/{config_id}` -- delete (204).
   - `GET /schema/{config_id}/preview` -- returns rendered JSON-LD script tag as PlainTextResponse.
6. Registered schema router in `main.py`.
7. Generated Alembic migration for the `schema_configs` table.

### Verification

- Schema CRUD works for all 5 page types.
- Default templates contain correct `@context` and `@type` fields.
- Domain is inserted into template URLs correctly.
- Preview endpoint returns properly formatted `<script>` tag.
- Cross-user schema access returns 404.
- Pagination works correctly.

---

## Step 7: Plan Limits and Constants

### What Was Built

The `constants/plans.py` module defining plan tier limits and Stripe Price ID management.

### Steps Completed

1. Created `backend/app/constants/plans.py` with:
   - `PlanLimits` dataclass (frozen=True): `max_items`, `max_secondary`, `price_monthly_cents`, `stripe_price_id`, `trial_days`, `api_access`.
   - `PLAN_LIMITS` dict mapping `PlanTier` to `PlanLimits`:
     - **Free**: max_items=2, max_secondary=20, $0, no API access, 0 trial days.
     - **Pro**: max_items=20, max_secondary=200, $29 (2900 cents), API access, 14 trial days.
     - **Enterprise**: max_items=-1 (unlimited), max_secondary=-1 (unlimited), $99 (9900 cents), API access, 14 trial days.
   - `init_price_ids(pro_price_id, enterprise_price_id)` -- called at startup to set Stripe Price IDs.
   - `resolve_plan_from_price_id(price_id)` -- maps Stripe Price ID back to PlanTier (used in webhook handlers).
2. Integrated plan limits into `blog_posts.py` (checks `max_items` before creating posts).
3. Integrated plan limits into `keywords.py` (checks `max_secondary` before adding keywords).

### Verification

- Free tier users cannot create more than 2 blog posts/month (returns 403).
- Free tier users cannot track more than 20 keywords (returns 403).
- Pro and Enterprise users have higher/unlimited limits.
- `init_price_ids` correctly updates the PLAN_LIMITS dict.

---

## Step 8: Backend Tests

### What Was Built

Comprehensive test suite with 74 tests covering all API endpoints, business logic, and edge cases.

### Steps Completed

1. Created `backend/tests/conftest.py` with:
   - `setup_db` (autouse): Table creation and truncation with connection termination.
   - `client`: httpx.AsyncClient fixture.
   - `db`: Raw AsyncSession fixture.
   - `auth_headers`: Auto-registers test user and returns Bearer headers.
   - `register_and_login`: Helper for creating additional users in tests.
   - Database dependency override using NullPool for isolation.
2. Created `test_health.py` (1 test): Health check returns status "ok".
3. Created `test_auth.py` (11 tests): Registration, login, refresh, profile, duplicate email, short password, wrong password, non-existent user, refresh-with-access-token, unauthenticated profile.
4. Created `test_sites.py` (20 tests): Full CRUD, pagination, domain verification, duplicate domain, invalid domain, cross-user isolation, unauthenticated access.
5. Created `test_blog.py` (25 tests): Full CRUD, content/keywords/meta_description, AI generation, status transitions (publish sets published_at), pagination, site filter, cross-user isolation, empty title validation, non-existent site.
6. Created `test_keywords.py` (16 tests): Add/list/delete, duplicate rejection, pagination, rank refresh, cross-site keyword deletion, non-existent site, cross-user isolation, unauthenticated access.
7. Created `test_audits.py` (15 tests): Run audit, score validation (0-100), issues structure, multiple audits, history listing, pagination, get by ID, non-existent site/audit, cross-user isolation, unauthenticated access.
8. Created `test_billing.py` (10 tests): List plans (3 tiers), plan pricing, pro checkout, free plan checkout fails, duplicate subscription fails, billing overview, overview after subscribe, current subscription (null and after subscribe).
9. Created `test_api_keys.py` (5 tests): Create key (raw key returned), list keys (no raw keys), revoke key, API key authentication on /usage, invalid API key.

### Verification

```bash
make test-backend   # All 74 tests pass
```

---

## Step 9: Dashboard Pages

### What Was Built

9 dashboard pages using Next.js 16 App Router, driven by the config in `service.config.ts`.

### Steps Completed

1. Created `dashboard/src/service.config.ts` as the single source of truth:
   - Service name: "RankPilot", tagline: "Automated SEO Engine", slug: "rankpilot".
   - API URL: `http://localhost:8103`.
   - Colors: Primary `oklch(0.65 0.18 155)` / `#10b981`, Accent `oklch(0.72 0.15 140)` / `#34d399`.
   - Fonts: General Sans (heading), Inter (body).
   - Navigation: 9 items (Dashboard, Sites, Blog Posts, Keywords, Audits, Schema, API Keys, Billing, Settings).
   - Plans: Free ($0), Pro ($29), Enterprise ($99) with feature lists.
2. Created `dashboard/src/app/layout.tsx` with font loading and shell wrapper.
3. Created `dashboard/src/app/page.tsx` -- Dashboard home page.
4. Created `dashboard/src/app/login/page.tsx` -- Login form.
5. Created `dashboard/src/app/register/page.tsx` -- Registration form.
6. Created `dashboard/src/app/sites/page.tsx` -- Site management page.
7. Created `dashboard/src/app/keywords/page.tsx` -- Keyword tracking page.
8. Created `dashboard/src/app/audits/page.tsx` -- SEO audit history page.
9. Created `dashboard/src/app/billing/page.tsx` -- Subscription management page.
10. Created `dashboard/src/app/api-keys/page.tsx` -- API key management page.
11. Created `dashboard/src/app/settings/page.tsx` -- Account settings page.
12. Created shared components: `shell.tsx`, `sidebar.tsx`, `top-bar.tsx`, `motion.tsx`.
13. Created UI components: `badge.tsx`, `button.tsx`, `card.tsx`, `dialog.tsx`, `input.tsx`, `skeleton.tsx`.
14. Created lib utilities: `api.ts` (HTTP client), `auth.ts` (JWT management), `utils.ts`.

### Verification

- Dashboard builds without errors.
- All 9 pages are accessible via sidebar navigation.
- Login and register forms connect to the backend API.
- Sites, keywords, and audits pages fetch and display data.
- Billing page shows 3 plan tiers with correct pricing.
- API keys page supports create, list, and revoke operations.

---

## Step 10: Landing Page

### What Was Built

Static marketing landing page for RankPilot using Next.js 16 static export on port 3203.

### Steps Completed

1. Created `landing/src/app/page.tsx` with marketing content.
2. Configured Next.js for static export in `next.config.ts`.
3. Applied RankPilot branding (Emerald Green, General Sans font).
4. Added feature highlights, pricing section, and call-to-action buttons.

### Verification

- Landing page builds and serves on port 3203.
- Branding matches the dashboard (same colors and fonts).
- Links to dashboard registration page work correctly.

---

## Summary

| Step | Component | Key Files | Tests |
|------|-----------|-----------|-------|
| 1 | Template scaffolding | main.py, config.py, database.py, auth.py, billing.py | -- |
| 2 | Sites model + service | site.py, site_service.py, sites.py (API) | 20 |
| 3 | Blog posts model + service | blog_post.py, blog_service.py, blog_posts.py (API) | 25 |
| 4 | Keyword tracking model + service | keyword.py, keyword_service.py, keywords.py (API) | 16 |
| 5 | SEO audits model + service | seo_audit.py, audit_service.py, audits.py (API) | 15 |
| 6 | Schema markup model + service | schema_config.py, schema_service.py, schema.py (API) | -- |
| 7 | Plan limits + constants | plans.py | -- |
| 8 | Backend test suite | conftest.py + 8 test files | 74 total |
| 9 | Dashboard pages | 9 page.tsx files + components | -- |
| 10 | Landing page | landing/src/app/page.tsx | -- |
