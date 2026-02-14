# Implementation Steps

This document records the step-by-step implementation of PostPilot -- from initial scaffolding through models, services, API routes, tests, dashboard pages, and landing page. Each step references the actual files created and explains the rationale.

---

## Step 1: Template Scaffolding

**Goal:** Generate the PostPilot service from the shared service template.

### Actions

1. **Run scaffold script** (`scripts/create-service.sh`) with PostPilot-specific values:
   - Service name: `PostPilot`
   - Slug: `postpilot`
   - Tagline: `Social Media Automation`
   - Backend port: `8106`
   - Dashboard port: `3106`
   - Landing port: `3206`
   - PostgreSQL port: `5506`
   - Redis port: `6406`
   - Primary color: `oklch(0.65 0.22 350)` (Hot Pink)
   - Accent color: `oklch(0.72 0.18 330)` (Soft Pink)
   - Heading font: `Plus Jakarta Sans`
   - Body font: `Inter`

2. **Template generates:**
   - `backend/` -- FastAPI app skeleton with auth, billing, API keys, health, webhooks
   - `dashboard/` -- Next.js 16 app with login, register, billing, API keys, settings, home pages
   - `landing/` -- Next.js 16 static marketing site
   - `Makefile` -- Build, test, and run targets
   - `README.md` -- Service overview
   - `.env.example` -- Environment variables

### Files Created

```
postpilot/
|-- README.md
|-- Makefile
|-- .env.example
|-- backend/app/main.py
|-- backend/app/config.py
|-- backend/app/database.py
|-- backend/app/api/__init__.py
|-- backend/app/api/auth.py
|-- backend/app/api/deps.py
|-- backend/app/api/billing.py
|-- backend/app/api/api_keys.py
|-- backend/app/api/health.py
|-- backend/app/api/usage.py
|-- backend/app/api/webhooks.py
|-- backend/app/models/base.py
|-- backend/app/models/user.py
|-- backend/app/models/subscription.py
|-- backend/app/models/api_key.py
|-- backend/app/schemas/auth.py
|-- backend/app/schemas/billing.py
|-- backend/app/services/auth_service.py
|-- backend/app/services/billing_service.py
|-- backend/app/constants/plans.py
|-- backend/app/tasks/celery_app.py
|-- backend/app/utils/helpers.py
|-- backend/alembic/env.py
|-- backend/tests/conftest.py
|-- backend/tests/test_auth.py
|-- backend/tests/test_billing.py
|-- backend/tests/test_api_keys.py
|-- backend/tests/test_health.py
|-- dashboard/src/service.config.ts
|-- dashboard/src/app/layout.tsx
|-- dashboard/src/app/page.tsx
|-- dashboard/src/app/login/page.tsx
|-- dashboard/src/app/register/page.tsx
|-- dashboard/src/app/billing/page.tsx
|-- dashboard/src/app/api-keys/page.tsx
|-- dashboard/src/app/settings/page.tsx
|-- dashboard/src/components/shell.tsx
|-- dashboard/src/components/sidebar.tsx
|-- dashboard/src/components/top-bar.tsx
|-- dashboard/src/components/motion.tsx
|-- dashboard/src/components/ui/[card, button, badge, input, skeleton, dialog].tsx
|-- dashboard/src/lib/api.ts
|-- dashboard/src/lib/auth.ts
|-- dashboard/src/lib/utils.ts
|-- landing/src/landing.config.ts
|-- landing/src/app/page.tsx
|-- landing/src/app/layout.tsx
|-- landing/src/app/pricing/page.tsx
|-- landing/src/components/[hero, features, how-it-works, pricing-cards, stats-bar, cta, navbar, footer].tsx
```

---

## Step 2: Domain Models

**Goal:** Define the PostPilot-specific database models for social media automation.

### Models Created

#### 2a. SocialAccount Model (`backend/app/models/social_account.py`)

Represents a connected social media profile.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `user_id` | UUID (FK -> users) | Owning user |
| `platform` | Enum(SocialPlatform) | instagram, facebook, tiktok |
| `account_name` | String(255) | Display name (e.g., @mybrand) |
| `account_id_external` | String(255) | Platform-specific ID |
| `access_token_enc` | String(1024), nullable | Encrypted OAuth access token |
| `refresh_token_enc` | String(1024), nullable | Encrypted OAuth refresh token |
| `is_connected` | Boolean, default True | Active connection status |
| `connected_at` | DateTime, nullable | When connected |
| `created_at` | DateTime | Record creation timestamp |

**Enum:** `SocialPlatform` -- `instagram`, `facebook`, `tiktok`

**Relationships:** `owner` (User, backref), `posts` (Post, back_populates)

#### 2b. Post Model (`backend/app/models/post.py`)

Represents a social media post with lifecycle tracking.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `user_id` | UUID (FK -> users) | Owning user |
| `account_id` | UUID (FK -> social_accounts) | Target social account |
| `content` | Text | Post caption text |
| `media_urls` | ARRAY(String) | Attached media URLs |
| `hashtags` | ARRAY(String) | Hashtag list (without # prefix) |
| `platform` | String(50) | Target platform (denormalized) |
| `status` | Enum(PostStatus) | draft, scheduled, posted, failed |
| `scheduled_for` | DateTime, nullable, indexed | Scheduled publish time |
| `posted_at` | DateTime, nullable | Actual publish timestamp |
| `error_message` | Text, nullable | Failure details |
| `created_at` | DateTime | Record creation timestamp |
| `updated_at` | DateTime | Last modification timestamp |

**Enum:** `PostStatus` -- `draft`, `scheduled`, `posted`, `failed`

**Relationships:** `account` (SocialAccount, back_populates), `metrics` (PostMetrics, one-to-one)

#### 2c. PostMetrics Model (`backend/app/models/post_metrics.py`)

Stores engagement metrics for published posts.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `post_id` | UUID (FK -> posts, unique) | One-to-one with Post |
| `impressions` | Integer, default 0 | Display count |
| `reach` | Integer, default 0 | Unique viewer count |
| `likes` | Integer, default 0 | Like/reaction count |
| `comments` | Integer, default 0 | Comment count |
| `shares` | Integer, default 0 | Share/repost count |
| `clicks` | Integer, default 0 | Link click count |
| `fetched_at` | DateTime | Last metrics refresh |

**Relationships:** `post` (Post, back_populates)

#### 2d. ContentQueue Model (`backend/app/models/content_queue.py`)

AI-assisted content generation pipeline.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `user_id` | UUID (FK -> users) | Owning user |
| `product_data` | JSON | Product information for AI input |
| `ai_generated_content` | Text, nullable | AI-generated caption |
| `platforms` | ARRAY(String) | Target platforms |
| `status` | Enum(QueueStatus) | pending, approved, rejected, posted |
| `created_at` | DateTime | Record creation timestamp |
| `updated_at` | DateTime | Last modification timestamp |

**Enum:** `QueueStatus` -- `pending`, `approved`, `rejected`, `posted`

**Relationships:** `owner` (User, backref)

---

## Step 3: Plan Configuration

**Goal:** Define PostPilot-specific plan limits in `backend/app/constants/plans.py`.

### Plan Limits

```python
PLAN_LIMITS = {
    PlanTier.free: PlanLimits(
        max_items=10,          # 10 posts/month
        max_secondary=1,       # 1 platform
        price_monthly_cents=0,
        trial_days=0,
        api_access=False,
    ),
    PlanTier.pro: PlanLimits(
        max_items=200,         # 200 posts/month
        max_secondary=10,      # Multiple accounts
        price_monthly_cents=2900,
        trial_days=14,
        api_access=True,
    ),
    PlanTier.enterprise: PlanLimits(
        max_items=-1,          # Unlimited posts
        max_secondary=-1,      # Unlimited accounts
        price_monthly_cents=9900,
        trial_days=14,
        api_access=True,
    ),
}
```

---

## Step 4: Service Layer

**Goal:** Implement business logic for social accounts, posts, AI captions, and analytics.

### 4a. Account Service (`backend/app/services/account_service.py`)

| Function | Logic |
|----------|-------|
| `connect_account` | Check `max_secondary` limit -> create SocialAccount with mock OAuth tokens -> return |
| `disconnect_account` | Find account by ID + user -> set `is_connected=False`, clear tokens -> return |
| `list_accounts` | Query all accounts for user, ordered by `created_at` descending |
| `get_account` | Query single account by ID + user |

### 4b. Post Service (`backend/app/services/post_service.py`)

| Function | Logic |
|----------|-------|
| `create_post` | Check `max_items` monthly limit (count posts created this month) -> set status based on `scheduled_for` -> create Post -> return |
| `update_post` | Find post -> reject if posted/failed -> apply partial updates (Ellipsis sentinel for `scheduled_for`) -> return |
| `delete_post` | Find post -> reject if posted -> delete -> return |
| `get_post` | Query single post by ID + user |
| `list_posts` | Build conditions (user, status, platform) -> count total -> fetch page -> return (posts, total) |
| `schedule_post` | Find post -> reject if not draft/scheduled -> reject if past time -> set scheduled_for + status -> return |
| `get_calendar_posts` | Query posts with `scheduled_for` in date range -> group by date string -> return dict |

### 4c. Caption Service (`backend/app/services/caption_service.py`)

| Function | Logic |
|----------|-------|
| `generate_caption` | Extract title, description, price from product_data -> build platform-specific caption with tone -> suggest hashtags -> return `{caption, hashtags, platform}` |
| `_build_caption` | Select tone-appropriate opener -> append platform-specific CTA (TikTok: "Link in bio! #fyp", Instagram: "Double-tap", Facebook: "Shop now") |
| `suggest_hashtags` | Extract keywords from title -> combine with platform-specific trending tags -> deduplicate -> limit to 10 |

### 4d. Analytics Service (`backend/app/services/analytics_service.py`)

| Function | Logic |
|----------|-------|
| `get_analytics_overview` | Count published posts -> aggregate SUM of all metrics via JOIN -> calculate avg engagement rate -> return dict |
| `get_post_metrics` | Query PostMetrics joined with Post, filtered by user |
| `get_all_post_metrics` | Paginated query with engagement rate calculation per post |

---

## Step 5: API Routes

**Goal:** Create REST API endpoints for all PostPilot features.

### 5a. Social Accounts Router (`backend/app/api/accounts.py`)

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/accounts` | POST | 201 | Connect social account |
| `/api/v1/accounts` | GET | 200 | List all accounts |
| `/api/v1/accounts/{account_id}` | DELETE | 200 | Disconnect account |

### 5b. Posts Router (`backend/app/api/posts.py`)

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/posts` | POST | 201 | Create post |
| `/api/v1/posts` | GET | 200 | List posts (paginated, filterable) |
| `/api/v1/posts/calendar` | GET | 200 | Calendar view (date range) |
| `/api/v1/posts/{post_id}` | GET | 200 | Get single post |
| `/api/v1/posts/{post_id}` | PATCH | 200 | Update post |
| `/api/v1/posts/{post_id}` | DELETE | 204 | Delete post |
| `/api/v1/posts/{post_id}/schedule` | POST | 200 | Schedule post |

### 5c. Content Queue Router (`backend/app/api/queue.py`)

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/queue` | POST | 201 | Add to queue |
| `/api/v1/queue` | GET | 200 | List queue items (paginated, filterable) |
| `/api/v1/queue/{item_id}` | GET | 200 | Get single item |
| `/api/v1/queue/{item_id}` | DELETE | 204 | Delete item |
| `/api/v1/queue/{item_id}/generate` | POST | 200 | Generate AI caption |
| `/api/v1/queue/{item_id}/approve` | POST | 200 | Approve item |
| `/api/v1/queue/{item_id}/reject` | POST | 200 | Reject item |
| `/api/v1/queue/generate-caption` | POST | 200 | Standalone caption generation |

### 5d. Analytics Router (`backend/app/api/analytics.py`)

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/analytics/overview` | GET | 200 | Aggregated overview |
| `/api/v1/analytics/posts` | GET | 200 | All post metrics (paginated) |
| `/api/v1/analytics/posts/{post_id}` | GET | 200 | Single post metrics |

### Router Registration

All routers registered in `backend/app/api/__init__.py` with prefix `/api/v1`.

---

## Step 6: Pydantic Schemas

**Goal:** Define request/response schemas in `backend/app/schemas/social.py`.

### Schemas Created

| Schema | Type | Fields |
|--------|------|--------|
| `SocialAccountConnect` | Request | platform (SocialPlatform), account_name (min_length=1), account_id_external (optional) |
| `SocialAccountResponse` | Response | id, platform, account_name, account_id_external, is_connected, connected_at, created_at |
| `PostCreate` | Request | account_id (UUID), content (min_length=1), platform, media_urls (optional), hashtags (optional), scheduled_for (optional) |
| `PostUpdate` | Request | content (optional), media_urls (optional), hashtags (optional), scheduled_for (optional) |
| `PostSchedule` | Request | scheduled_for (datetime) |
| `PostResponse` | Response | id, account_id, content, media_urls, hashtags, platform, status, scheduled_for, posted_at, error_message, created_at, updated_at |
| `PostListResponse` | Response | items (list[PostResponse]), total, page, per_page |
| `CalendarDay` | Response | date (str), posts (list[PostResponse]) |
| `CalendarView` | Response | days (list[CalendarDay]), total_posts (int) |
| `ContentQueueCreate` | Request | product_data (dict), platforms (list[str]) |
| `ContentQueueResponse` | Response | id, product_data, ai_generated_content, platforms, status, created_at, updated_at |
| `ContentQueueListResponse` | Response | items (list[ContentQueueResponse]), total, page, per_page |
| `CaptionGenerateRequest` | Request | product_data (dict), platform (optional, default "instagram"), tone (optional, default "engaging") |
| `CaptionGenerateResponse` | Response | caption, hashtags (list[str]), platform |
| `AnalyticsOverview` | Response | total_posts, total_impressions, total_reach, total_likes, total_comments, total_shares, total_clicks, avg_engagement_rate |
| `PostMetricsResponse` | Response | id, post_id, impressions, reach, likes, comments, shares, clicks, engagement_rate, fetched_at |

---

## Step 7: Backend Tests

**Goal:** Write comprehensive tests for all PostPilot-specific endpoints.

### Test Files Created

#### 7a. `test_accounts.py` -- 16 tests

- Connect: Instagram (201), Facebook (201), TikTok (201), auto-generate external ID, invalid platform (422), empty name (422), unauthenticated (401)
- List: empty (200), after connect, multiple platforms, unauthenticated (401), user isolation
- Disconnect: success (200), shows in list, nonexistent (404), other user's account (404), unauthenticated (401)

#### 7b. `test_posts.py` -- 20 tests

- Create: draft (201), scheduled (201), minimal fields, empty content (422), unauthenticated (401)
- List: empty, with data, pagination, filter by status, filter by platform
- Get: by ID (200), not found (404)
- Update: content, hashtags, nonexistent (404)
- Delete: draft (204), nonexistent (404), unauthenticated (401)
- Schedule: future time (200), past time (400), nonexistent (404)
- Calendar: empty range, with scheduled posts, missing params (422)
- Isolation: user A's posts invisible to user B

#### 7c. `test_queue.py` -- 22 tests

- Create: success (201), empty platforms, unauthenticated (401)
- List: empty, with items, pagination, filter by status, unauthenticated (401)
- Get: by ID (200), not found (404), user isolation
- Delete: pending (204), approved rejected (400), nonexistent (404), rejected allowed (204)
- Generate: success (200, ai_generated_content populated), nonexistent (404)
- Standalone: caption returned (200), default platform
- Approve: pending (200), already approved (400), nonexistent (404)
- Reject: pending (200), already rejected (400), nonexistent (404)
- Isolation: user A items invisible to user B

---

## Step 8: Dashboard Pages

**Goal:** Build feature-specific dashboard pages for PostPilot.

### 8a. Accounts Page (`dashboard/src/app/accounts/page.tsx`)

- Fetches from `GET /api/v1/accounts`
- Connect dialog with platform selector (Instagram, Facebook, TikTok) and account name input
- Account cards with platform icon, name, connection status badge, connected date
- Disconnect button with confirmation
- Empty state with CTA to connect first account
- Loading skeletons and error handling

### 8b. Posts Page (`dashboard/src/app/posts/page.tsx`)

- Fetches from `GET /api/v1/posts` with pagination
- Post cards with content preview, platform badge, status badge
- Status and platform filter dropdowns
- Pagination controls

### 8c. Queue Page (`dashboard/src/app/queue/page.tsx`)

- **Left panel (2/3):** Queue item cards with:
  - Product image/placeholder, title, price
  - Platform badges, status badge
  - AI-generated caption preview (collapsible)
  - Action buttons: Generate Caption, Approve, Reject, Delete
  - Status filter dropdown
  - Pagination controls
  - Stats row (In Queue, Pending, Approved, Rejected)
- **Right panel (1/3):** Calendar sidebar with:
  - Upcoming 14 days of scheduled posts
  - Day cards with weekday, date, post count
  - Total scheduled count
  - Fetches from `GET /api/v1/posts/calendar`
- Add to Queue dialog with:
  - Product title (required), description, price, image URL
  - Platform toggle buttons
  - Submit handler

---

## Step 9: Service Configuration

**Goal:** Configure `dashboard/src/service.config.ts` with PostPilot-specific values.

### Configuration Values

```typescript
{
  name: "PostPilot",
  tagline: "Social Media Automation",
  slug: "postpilot",
  apiUrl: "http://localhost:8106",
  colors: {
    primary: "oklch(0.65 0.22 350)",     // Hot Pink
    primaryHex: "#ec4899",
    accent: "oklch(0.72 0.18 330)",      // Soft Pink
    accentHex: "#f472b6",
  },
  fonts: {
    heading: "Plus Jakarta Sans",
    body: "Inter",
  },
  navigation: [
    { label: "Dashboard",  href: "/",           icon: "LayoutDashboard" },
    { label: "Queue",      href: "/queue",      icon: "ListOrdered" },
    { label: "Calendar",   href: "/calendar",   icon: "Calendar" },
    { label: "Accounts",   href: "/accounts",   icon: "Users" },
    { label: "Analytics",  href: "/analytics",  icon: "BarChart3" },
    { label: "Templates",  href: "/templates",  icon: "FileText" },
    { label: "API Keys",   href: "/api-keys",   icon: "Key" },
    { label: "Billing",    href: "/billing",    icon: "CreditCard" },
    { label: "Settings",   href: "/settings",   icon: "Settings" },
  ],
  plans: [
    { tier: "free",       name: "Free",       price: 0,   features: [...] },
    { tier: "pro",        name: "Pro",        price: 29,  features: [...] },
    { tier: "enterprise", name: "Enterprise", price: 99,  features: [...] },
  ],
}
```

---

## Step 10: Landing Page

**Goal:** Build a marketing landing page for PostPilot.

### Components

| Component | Content |
|-----------|---------|
| `hero.tsx` | Headline, tagline, CTA buttons |
| `features.tsx` | Feature cards (multi-platform, AI captions, scheduling, analytics) |
| `how-it-works.tsx` | Step-by-step workflow visualization |
| `stats-bar.tsx` | Key statistics bar |
| `pricing-cards.tsx` | 3-tier pricing cards with feature lists |
| `cta.tsx` | Bottom call-to-action section |
| `navbar.tsx` | Top navigation with logo and links |
| `footer.tsx` | Footer with links and copyright |

### Pages

| Page | Path | Description |
|------|------|-------------|
| Home | `/` | Full landing page with all sections |
| Pricing | `/pricing` | Dedicated pricing page |

---

## Summary: File Count by Category

| Category | Files | Description |
|----------|-------|-------------|
| Models | 4 domain + 3 standard = 7 | SocialAccount, Post, PostMetrics, ContentQueue + User, Subscription, ApiKey |
| Services | 4 domain + 2 standard = 6 | account, post, caption, analytics + auth, billing |
| API Routes | 4 domain + 6 standard = 10 | accounts, posts, queue, analytics + auth, billing, api_keys, health, usage, webhooks |
| Schemas | 1 domain + 2 standard = 3 | social.py + auth.py, billing.py |
| Tests | 3 domain + 4 standard = 7 | test_accounts, test_posts, test_queue + test_auth, test_billing, test_api_keys, test_health |
| Dashboard pages | 3 domain + 6 standard = 9 | accounts, posts, queue + home, billing, api-keys, settings, login, register |
| Landing components | 8 | hero, features, how-it-works, stats-bar, pricing-cards, cta, navbar, footer |
| Config files | 3 | service.config.ts, landing.config.ts, constants/plans.py |
| **Total** | ~50+ source files | Complete PostPilot service scaffold |
