# QA Engineer Guide

> Part of [TrendScout](README.md) documentation

**For QA Engineers:** This guide covers acceptance criteria, verification checklists, and edge cases for the TrendScout service. For detailed testing procedures, see the [Testing Guide](TESTING.md). For API documentation, see the [API Reference](API_REFERENCE.md).

TrendScout is an AI-powered product research SaaS that discovers trending products using multi-source data aggregation and weighted scoring. All tests run in mock mode -- no real Stripe, AI, or external API calls are made during testing.

---

## Pre-Release Verification Checklist

Before marking a release as ready:

- [ ] All backend tests pass: `pytest` (158 tests) -- see [Testing Guide](TESTING.md)
- [ ] Dashboard builds successfully: `cd dashboard && npm run build`
- [ ] Landing page builds successfully: `cd landing && npm run build`
- [ ] Backend starts without errors: `uvicorn app.main:app --port 8101`
- [ ] Swagger docs load at http://localhost:8101/docs -- see [API Reference](API_REFERENCE.md)
- [ ] Health endpoint returns `{"status": "ok"}` at `/api/v1/health`
- [ ] All critical user flows complete end-to-end (registration, research run, watchlist)
- [ ] Plan limits properly enforced (Free: 5 runs, 25 watchlist items)
- [ ] Credential redaction verified (source configs never expose raw credentials)
- [ ] User isolation verified (users cannot access other users' resources)

---

## Feature Verification Table

| Feature | What to Test | Expected Behavior |
|---------|-------------|-------------------|
| **Registration** | POST `/auth/register` with valid email/password | 201 + JWT tokens returned |
| **Duplicate Email** | Register same email twice | Second attempt returns 409 |
| **Login** | POST `/auth/login` with correct credentials | 200 + JWT tokens |
| **Invalid Login** | POST `/auth/login` with wrong password | 401 |
| **Token Refresh** | POST `/auth/refresh` with refresh token | 200 + new token pair |
| **Profile** | GET `/auth/me` with Bearer token | 200 + user profile with plan=free |
| **Plan Listing** | GET `/billing/plans` | 200 + 3 plans (free, pro, enterprise) |
| **Checkout** | POST `/billing/checkout` for "pro" plan | 201 + checkout_url and session_id |
| **Free Plan Checkout** | POST `/billing/checkout` for "free" plan | 400 error |
| **Create Research Run** | POST `/research/runs` with keywords and sources | 201 + run with status=pending |
| **Plan Limit Enforcement** | Create 6 runs on free plan (limit=5) | 6th run returns 403 |
| **List Runs** | GET `/research/runs` after creating runs | Paginated list, newest first |
| **Run Detail** | GET `/research/runs/{id}` | 200 + run with results array |
| **Delete Run** | DELETE `/research/runs/{id}` | 204 + run no longer retrievable |
| **Add to Watchlist** | POST `/watchlist` with valid result_id | 201 + item with status=watching |
| **Duplicate Watchlist** | Add same result twice | Second attempt returns 409 |
| **Watchlist Capacity** | Add 26 items on free plan (limit=25) | 26th item returns 403 |
| **Filter Watchlist** | GET `/watchlist?status=imported` | Only imported items returned |
| **Update Watchlist** | PATCH `/watchlist/{id}` with status=imported | 200 + status updated |
| **Create Source** | POST `/sources` with aliexpress type | 201 + config with has_credentials flag |
| **Invalid Source Type** | POST `/sources` with type=amazon | 400 error |
| **Credential Redaction** | Any source response | No raw credentials, only has_credentials boolean |
| **Create API Key** | POST `/api-keys` | 201 + raw key returned (shown once) |
| **API Key Auth** | GET `/usage` with X-API-Key header | 200 + usage data |
| **Revoke API Key** | DELETE `/api-keys/{id}` | 204 + key marked inactive |
| **User Isolation** | Access another user's run/watchlist/source | Always returns 404 |
| **Unauthenticated Access** | Any protected endpoint without token | Always returns 401 |

---

## Edge Cases and Known Issues

### Research Runs

- **Empty Keywords Array**: POST `/research/runs` with empty `keywords` array returns 422
- **Invalid Source Type**: Requesting sources not in `{aliexpress, tiktok, google_trends, reddit}` silently filters them out
- **Celery Worker Offline**: Runs stay in `pending` status indefinitely if worker is not running
- **Score Config Weights**: If custom weights don't sum to 1.0, they are automatically normalized

### Watchlist

- **Duplicate Add**: Adding same result twice returns 409 Conflict
- **Nonexistent Result**: Adding a result_id that doesn't exist returns 404
- **Plan Limit Boundary**: Exactly at limit (e.g., 25th item on Free) succeeds; 26th fails with 403
- **Re-add After Delete**: Same result can be re-added after deletion with a new watchlist_item_id

### Source Configuration

- **Invalid Source Type**: POST with `source_type` not in valid set returns 400
- **Credential Redaction**: All responses replace raw `credentials` with `has_credentials` boolean
- **Multiple Configs Same Type**: Users can create multiple configs for the same source_type (e.g., multiple AliExpress accounts)

### Billing

- **Free Plan Checkout**: Attempting to checkout for "free" plan returns 400
- **No Stripe Keys**: Mock mode provides placeholder URLs without real Stripe API calls
- **Duplicate Subscription**: Creating second subscription for same plan returns 400

### API Keys

- **Raw Key Display**: Key is only shown once at creation time (201 response)
- **Revoked Key Auth**: Attempting auth with revoked key returns 401
- **Free Plan Restriction**: API key creation works on Free plan in tests but may be restricted in production

---

## Acceptance Criteria by Feature

### Research Run Creation (F1)

**Must**:
- Validate keywords array is non-empty
- Enforce plan limit (Free: 5/month, Pro: 50/month, Enterprise: unlimited)
- Dispatch Celery task for background processing
- Return 201 with run in `pending` status
- Support custom `score_config` override

**Must Not**:
- Block API response waiting for research completion
- Allow creation beyond plan limit (must return 403)
- Accept invalid source types

---

### Watchlist Management (F2)

**Must**:
- Prevent duplicate additions (same user + result_id)
- Enforce plan limit (Free: 25, Pro: 500, Enterprise: unlimited)
- Support status filtering (`watching`, `imported`, `dismissed`)
- Include result snapshot in response (product_title, source, price, score)
- Allow re-adding after deletion

**Must Not**:
- Delete underlying research result when removing from watchlist
- Allow adding nonexistent result_id
- Expose other users' watchlist items

---

### Source Configuration (F3)

**Must**:
- Validate source_type against `{aliexpress, tiktok, google_trends, reddit}`
- Redact credentials in all responses (use `has_credentials` flag)
- Support partial updates (credentials, settings, is_active)
- Order list by source_type

**Must Not**:
- Return raw credentials in any response
- Allow invalid source_type (must return 400)
- Expose other users' source configs

---

### AI Scoring (F4)

**Must**:
- Score products 0-100 across 5 dimensions (Social 40%, Market 30%, Competition 15%, SEO 10%, Fundamentals 5%)
- Support custom weight overrides via `score_config`
- Normalize custom weights to sum to 1.0
- Round final score to 1 decimal place

**Must Not**:
- Return scores outside [0, 100] range
- Fail if some metrics are missing (use defaults)

---

### AI Analysis (F5)

**Must**:
- Provide summary, opportunity_score, risk_factors, recommended_price_range, target_audience, marketing_angles
- Fall back to mock analysis if Anthropic API key missing or API fails
- Store analysis as JSON in `research_results.ai_analysis` column

**Must Not**:
- Block research run on AI analysis failure (fallback to mock)
- Expose Anthropic API key in responses

---

*See also: [Testing Guide](TESTING.md) · [API Reference](API_REFERENCE.md) · [Setup](SETUP.md)*
