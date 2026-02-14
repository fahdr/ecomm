# SourcePilot -- QA Engineer Documentation

## Test Environment

### Prerequisites

- PostgreSQL with `sourcepilot` database accessible
- Redis running on default port
- Python 3.11+ with project dependencies installed

### Running Tests

```bash
cd sourcepilot/backend

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_imports.py

# Run specific test
pytest tests/test_imports.py::test_create_import_success -v

# Stop on first failure
pytest -x

# Show print output
pytest -s
```

### Test Infrastructure

- **Schema isolation**: Tests use a dedicated `sourcepilot_test` PostgreSQL schema, separate from the production `sourcepilot` schema.
- **Per-test truncation**: All tables are truncated before each test via the `truncate_tables` autouse fixture.
- **Session-scoped setup**: Schema creation and table DDL run once per test session.
- **Dependency override**: The FastAPI `get_db` dependency is overridden to use the test database session.
- **Mock Stripe**: All tests run in mock mode (empty `STRIPE_SECRET_KEY`), so no real Stripe calls are made.

### Key Fixtures

| Fixture | Scope | Description |
|---|---|---|
| `create_tables` | session | Creates the `sourcepilot_test` schema and all tables |
| `truncate_tables` | function (autouse) | Truncates all tables before each test |
| `db` | function | Provides an async database session within the test schema |
| `client` | function | Provides an httpx `AsyncClient` for API testing |
| `auth_headers` | function | Registers a test user and returns `{"Authorization": "Bearer <token>"}` |
| `register_and_login` | imported from `ecomm_core.testing` | Helper that POSTs to register + login and returns auth headers |

---

## Test Coverage Summary

**Total: 130 tests across 11 files.**

| File | Test Count | Area |
|---|---|---|
| `test_auth.py` | 12+ | Authentication and user management |
| `test_imports.py` | 20+ | Import job lifecycle |
| `test_products.py` | 12+ | Product search and preview |
| `test_suppliers.py` | 12+ | Supplier account CRUD |
| `test_connections.py` | 15+ | Store connection CRUD |
| `test_price_watch.py` | 12+ | Price monitoring |
| `test_billing.py` | 10+ | Billing and subscriptions |
| `test_webhooks_sp.py` | 8+ | Webhook handling |
| `test_api_keys.py` | 8+ | API key management |
| `test_health.py` | 2+ | Health check |

---

## Test Plans by Feature

### 1. Authentication (`/api/v1/auth`)

#### Registration (`POST /auth/register`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Successful registration | Valid email + password (>= 8 chars) | 201, returns access_token + refresh_token | Pass |
| Duplicate email | Email already registered | 409 Conflict, "A user with this email already exists" | Pass |
| Invalid email format | `"not-an-email"` | 422 Unprocessable Entity | Pass |
| Short password | Password < 8 characters | 422 Unprocessable Entity | Pass |
| Missing email | Omit email field | 422 Unprocessable Entity | Pass |
| Missing password | Omit password field | 422 Unprocessable Entity | Pass |

#### Login (`POST /auth/login`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Successful login | Correct email + password | 200, returns access_token + refresh_token | Pass |
| Wrong password | Correct email, wrong password | 401 Unauthorized | Pass |
| Non-existent email | Email not registered | 401 Unauthorized | Pass |
| Missing credentials | Omit email or password | 422 Unprocessable Entity | Pass |

#### Token Refresh (`POST /auth/refresh`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Valid refresh token | Active refresh token | 200, returns new token pair | Pass |
| Expired refresh token | Expired refresh token | 401 Unauthorized | Pass |
| Invalid refresh token | Random string | 401 Unauthorized | Pass |
| Access token as refresh | Use access token instead | 401 Unauthorized ("type" != "refresh") | Pass |

#### Profile (`GET /auth/me`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Authenticated user | Valid JWT | 200, returns user profile (id, email, plan, is_active) | Pass |
| No auth header | Omit Authorization header | 401 Unauthorized | Pass |
| Invalid token | Expired or malformed JWT | 401 Unauthorized | Pass |

#### User Provisioning (`POST /auth/provision`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Successful provision | Valid email, plan, external IDs | 201, returns user_id + api_key | Pass |
| Unauthenticated | No auth header | 401 Unauthorized | Pass |
| Duplicate email provision | Already provisioned email | Returns existing user_id with new API key | Pass |

### 2. Import Jobs (`/api/v1/imports`)

#### Create Import (`POST /imports`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Successful create | Valid product_url + source | 201, returns job in "pending" status, progress_percent = 0 | Pass |
| Valid sources | "aliexpress", "cjdropship", "spocket", "manual" | 201 for each | Pass |
| Invalid source | source = "ebay" | 400 Bad Request, "Invalid source" | Pass |
| Plan limit reached | Free user with 10 imports this month | 403 Forbidden, "Import limit reached" | Pass |
| Enterprise unlimited | Enterprise user | 201 regardless of count | Pass |
| With store_id | Valid store connection UUID | 201, store_id set in response | Pass |
| With config | `{"markup_percent": 30, "tags": ["trending"]}` | 201, config preserved in response | Pass |
| No auth | Omit Authorization header | 401 Unauthorized | Pass |
| History entry created | After successful create | ImportHistory row with action="created" | Pass |

#### List Imports (`GET /imports`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| List with data | After creating imports | 200, items array with correct total | Pass |
| Empty list | No imports | 200, items=[], total=0 | Pass |
| Pagination (skip/limit) | skip=0, limit=5 | Returns correct page | Pass |
| Filter by status | status=pending | Only pending jobs returned | Pass |
| Filter by store_id | store_id=UUID | Only matching store jobs returned | Pass |
| Ordering | Multiple imports | Newest first (desc by created_at) | Pass |
| Other user's imports not visible | Create imports for user A, query as user B | 200, items=[], total=0 | Pass |

#### Get Import Detail (`GET /imports/{job_id}`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Valid job | Own job's UUID | 200, full job details | Pass |
| Non-existent job | Random UUID | 404 Not Found | Pass |
| Other user's job | Job owned by different user | 404 Not Found | Pass |

#### Cancel Import (`POST /imports/{job_id}/cancel`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Cancel pending job | Job in "pending" status | 200, status changes to "cancelled" | Pass |
| Cancel running job | Job in "running" status | 200, status changes to "cancelled" | Pass |
| Cancel completed job | Job in "completed" status | 400 Bad Request | Pass |
| Cancel failed job | Job in "failed" status | 400 Bad Request | Pass |
| Cancel non-existent | Random UUID | 404 Not Found | Pass |
| Cancel other user's job | Job owned by different user | 404 Not Found | Pass |

#### Retry Import (`POST /imports/{job_id}/retry`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Retry failed job | Job in "failed" status | 200, status resets to "pending", progress = 0 | Pass |
| Retry cancelled job | Job in "cancelled" status | 200, status resets to "pending" | Pass |
| Retry pending job | Job in "pending" status | 400 Bad Request | Pass |
| Retry running job | Job in "running" status | 400 Bad Request | Pass |
| Retry completed job | Job in "completed" status | 400 Bad Request | Pass |
| History entry | After retry | ImportHistory row with action="retried" | Pass |

#### Bulk Import (`POST /imports/bulk`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Successful bulk | 3 valid URLs + source | 201, returns 3 jobs all in "pending" | Pass |
| Max 50 URLs | 50 URLs | 201, returns 50 jobs | Pass |
| Over 50 URLs | 51 URLs | 422 Unprocessable Entity (schema validation) | Pass |
| Empty URL list | product_urls = [] | 422 Unprocessable Entity (min_length=1) | Pass |
| Invalid source | source = "invalid" | 400 Bad Request | Pass |
| Plan limit | Exceeds import limit | 403 Forbidden | Pass |
| Shared config | All jobs get same config | All jobs have matching config field | Pass |

### 3. Products (`/api/v1/products`)

#### Search (`GET /products/search`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Basic search | q="wireless earbuds" | 200, returns products with total, page, page_size | Pass |
| With source filter | q="shoes", source="aliexpress" | 200, all results from aliexpress | Pass |
| Pagination | page=2, page_size=10 | 200, correct offset results | Pass |
| Invalid source | source="invalid" | 400 Bad Request | Pass |
| Empty query | q="" | 422 Unprocessable Entity (min_length=1) | Pass |
| Long query | 500+ chars | 422 Unprocessable Entity (max_length=500) | Pass |
| No auth | Omit Authorization | 401 Unauthorized | Pass |
| Default source | No source param | Defaults to "aliexpress" | Pass |

#### Preview (`POST /products/preview`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Valid AliExpress URL | https://aliexpress.com/item/123.html | 200, returns title, price, images, etc. | Pass |
| Valid CJ URL | https://cjdropshipping.com/... | 200, source = "cjdropship" | Pass |
| Valid Spocket URL | https://spocket.co/... | 200, source = "spocket" | Pass |
| Non-HTTP URL | "ftp://invalid" | 400 Bad Request, "must start with http" | Pass |
| Empty URL | url="" | 422 Unprocessable Entity (min_length=1) | Pass |
| Product caching | Preview same URL twice | Second call uses cached data | Pass |
| Response shape | Any valid URL | Contains: title, price, currency, images, variants, source, shipping_info | Pass |

### 4. Supplier Accounts (`/api/v1/suppliers`)

#### Create (`POST /suppliers/accounts`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Successful create | name, platform, credentials | 201, returns account with id | Pass |
| Duplicate name+platform | Same name and platform for same user | 400 Bad Request | Pass |
| Same name different platform | Same name, different platform | 201 (allowed) | Pass |
| Without credentials | credentials=null | 201, credentials=null in response | Pass |
| No auth | Omit Authorization | 401 Unauthorized | Pass |

#### List (`GET /suppliers/accounts`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| List accounts | After creating accounts | 200, items array | Pass |
| Empty list | No accounts | 200, items=[] | Pass |
| Ordering | Multiple accounts | Ordered by platform, then name | Pass |
| Isolation | Other user's accounts not visible | 200, only own accounts | Pass |

#### Update (`PUT /suppliers/accounts/{id}`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Update name | name="New Name" | 200, name updated | Pass |
| Update credentials | New credentials dict | 200, credentials updated | Pass |
| Toggle active | is_active=false | 200, is_active=false | Pass |
| Partial update | Only name provided | 200, other fields unchanged | Pass |
| Non-existent account | Random UUID | 404 Not Found | Pass |
| Other user's account | Account owned by different user | 404 Not Found | Pass |

#### Delete (`DELETE /suppliers/accounts/{id}`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Successful delete | Own account UUID | 204 No Content | Pass |
| Non-existent account | Random UUID | 404 Not Found | Pass |
| Other user's account | Account owned by different user | 404 Not Found | Pass |
| Verify deleted | GET after delete | Not in list | Pass |

### 5. Store Connections (`/api/v1/connections`)

#### Create (`POST /connections`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| First connection | store_name, platform, store_url | 201, is_default=true (auto-set) | Pass |
| Second connection | Different store_url | 201, is_default=false | Pass |
| Duplicate URL | Same store_url for same user | 409 Conflict | Pass |
| With API key | api_key provided | 201, api_key stored | Pass |
| No auth | Omit Authorization | 401 Unauthorized | Pass |

#### List (`GET /connections`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| List connections | After creating connections | 200, items array | Pass |
| Ordering | Multiple connections | Default first, then by store_name | Pass |
| Isolation | Other user's connections not visible | 200, only own connections | Pass |

#### Update (`PUT /connections/{id}`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Update store_name | New name | 200, store_name updated | Pass |
| Set as default | is_default=true | 200, old default cleared | Pass |
| Non-existent | Random UUID | 404 Not Found | Pass |
| Other user's | Connection not owned | 404 Not Found | Pass |

#### Delete (`DELETE /connections/{id}`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Delete non-default | Non-default connection | 204, default unchanged | Pass |
| Delete default | Default connection | 204, next connection promoted to default | Pass |
| Delete last connection | Only remaining connection | 204, no default to promote | Pass |
| Non-existent | Random UUID | 404 Not Found | Pass |

#### Set Default (`POST /connections/{id}/default`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Set new default | Valid connection UUID | 200, old default cleared, new default set | Pass |
| Already default | Current default connection | 200, no change | Pass |
| Non-existent | Random UUID | 404 Not Found | Pass |

### 6. Price Watches (`/api/v1/price-watches`)

#### Create (`POST /price-watches`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Successful create | product_url, source, threshold_percent | 201, watch created with is_active=true | Pass |
| Default threshold | Omit threshold_percent | 201, threshold_percent=10.0 | Pass |
| With connection_id | Valid connection UUID | 201, connection_id set | Pass |
| No auth | Omit Authorization | 401 Unauthorized | Pass |

#### List (`GET /price-watches`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| List all | No filters | 200, all watches with total count | Pass |
| Filter by connection_id | connection_id=UUID | 200, only matching watches | Pass |
| Ordering | Multiple watches | Newest first | Pass |

#### Delete (`DELETE /price-watches/{id}`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Successful delete | Own watch UUID | 204 No Content | Pass |
| Non-existent | Random UUID | 404 Not Found | Pass |
| Other user's | Watch not owned | 404 Not Found | Pass |

#### Sync (`POST /price-watches/sync`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Sync with active watches | Watches exist | 200, returns total_checked, total_changed, total_errors | Pass |
| Sync with no watches | No watches | 200, all counts = 0 | Pass |
| Price change detection | Watch with different current_price | price_changed=true in watch | Pass |
| Inactive watches skipped | is_active=false | Not included in checked count | Pass |

### 7. Billing (`/api/v1/billing`)

#### List Plans (`GET /billing/plans`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Public access | No auth required | 200, returns 3 plans (free, pro, enterprise) | Pass |
| Plan structure | - | Each plan has: tier, name, price_monthly_cents, max_items, max_secondary, trial_days, api_access | Pass |
| Free plan | - | price=0, max_items=10, max_secondary=25, trial_days=0, api_access=false | Pass |
| Pro plan | - | price=2900, max_items=100, max_secondary=500, trial_days=14, api_access=true | Pass |
| Enterprise plan | - | price=9900, max_items=-1, max_secondary=-1, trial_days=14, api_access=true | Pass |

#### Checkout (`POST /billing/checkout`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Pro checkout (mock) | plan="pro" | 201, returns checkout_url + session_id | Pass |
| Enterprise checkout (mock) | plan="enterprise" | 201, returns checkout_url + session_id | Pass |
| Free plan checkout | plan="free" | 400 Bad Request, "Cannot checkout for free plan" | Pass |
| Already subscribed | User with active subscription | 400 Bad Request, "already has an active subscription" | Pass |
| No auth | Omit Authorization | 401 Unauthorized | Pass |

#### Portal (`POST /billing/portal`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| With Stripe customer | User has stripe_customer_id | 200, returns portal_url | Pass |
| Without Stripe customer | User has no stripe_customer_id | 400 Bad Request, "no billing account" | Pass |

#### Overview (`GET /billing/overview`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Overview response | Authenticated user | 200, returns current_plan, plan_name, subscription, usage | Pass |
| Usage metrics | - | Contains items_used and secondary_used metrics with limits | Pass |

### 8. Webhooks (`/api/v1/webhooks`)

#### Stripe Webhook (`POST /webhooks/stripe`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Subscription created | type="customer.subscription.created" | 200, subscription record created | Pass |
| Subscription updated | type="customer.subscription.updated" | 200, subscription record updated | Pass |
| Subscription deleted | type="customer.subscription.deleted" | 200, user plan downgraded to free | Pass |
| Invalid JSON | Malformed body | 400 Bad Request | Pass |
| Unhandled event type | type="invoice.paid" | 200 (acknowledged, no action) | Pass |

#### Product Scored (`POST /webhooks/product-scored`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| High score (>= 50) | score=75.0 | 200, import_triggered=true, import_job_id returned | Pass |
| Low score (< 50) | score=30.0 | 200, import_triggered=false | Pass |
| Exact threshold | score=50.0 | 200, import_triggered=true | Pass |
| No auth | Omit Authorization | 401 Unauthorized | Pass |
| Import job created | score=75.0 | ImportJob record exists with auto_import config | Pass |

### 9. API Keys (`/api/v1/api-keys`)

#### Create (`POST /api-keys`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Successful create | name="My Key", scopes=["read"] | 201, returns key (raw), key_prefix, name, scopes | Pass |
| Key format | - | Key starts with "so_live_" | Pass |
| Key prefix | - | key_prefix = first 12 chars of raw key | Pass |
| Default scopes | Omit scopes | 201, scopes=["read"] | Pass |

#### List (`GET /api-keys`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| List keys | After creating keys | 200, array of key metadata | Pass |
| No raw keys in list | - | key field NOT present in list response | Pass |
| Key metadata | - | Contains: id, name, key_prefix, scopes, is_active, created_at | Pass |

#### Revoke (`DELETE /api-keys/{id}`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Successful revoke | Own key UUID | 204, key.is_active=false | Pass |
| Non-existent key | Random UUID | 404 Not Found | Pass |
| Revoked key unusable | Use revoked key as X-API-Key | 401 Unauthorized | Pass |

### 10. Health (`/api/v1/health`)

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Health check | GET /health | 200, {"service": "sourcepilot", "status": "ok", "timestamp": "..."} | Pass |
| No auth required | Omit Authorization | 200 | Pass |

---

## Edge Cases and Boundary Conditions

### Import Limits

- **Exactly at limit**: Create imports until reaching the plan limit, verify the next create returns 403.
- **Month boundary**: Imports from previous month should not count against current month's limit.
- **Plan upgrade mid-month**: After upgrading from Free (10) to Pro (100), user should have the Pro limit immediately.

### Default Store Connection

- **Single connection**: First connection auto-defaults. Verify `is_default=true`.
- **Delete default with alternatives**: When the default is deleted, the oldest remaining connection becomes default.
- **Delete default with no alternatives**: When the only connection is deleted, no default exists.
- **Set default twice**: Setting the same connection as default twice is idempotent.

### Price Watch Sync

- **No price change**: Current price equals last price, `price_changed` should remain `false`.
- **Price increase**: Current price > last price, `price_changed` should be `true`.
- **Price decrease**: Current price < last price, `price_changed` should be `true`.
- **Inactive watch**: Deactivated watches should be skipped during sync.

### Authentication Edge Cases

- **Concurrent requests**: Multiple requests with the same token should all succeed.
- **Token just expired**: Request arriving at exact expiration moment.
- **API key + JWT both provided**: Should prefer JWT authentication.
- **Revoked API key**: Should return 401 even if the key format is correct.

### Bulk Import

- **Duplicate URLs in bulk**: Should create separate jobs for each URL (no dedup).
- **Mixed valid/invalid in bulk**: All URLs share the same source; if source is invalid, all fail.

---

## Acceptance Criteria

### Import Workflow

1. User can create an import job with a valid supplier URL.
2. Job starts in "pending" status with `progress_percent = 0`.
3. Job can be listed with pagination and status filters.
4. Pending/running jobs can be cancelled.
5. Failed/cancelled jobs can be retried (resets to pending).
6. Bulk import creates individual jobs for each URL.
7. Plan limits are enforced before job creation.

### Price Monitoring

1. User can add a price watch with a product URL and source.
2. Watches are listed with optional connection_id filtering.
3. Manual sync checks all active watches and updates prices.
4. Price changes are detected and flagged.
5. Watches can be deleted to stop monitoring.

### Store Connection Management

1. First connection is automatically the default.
2. Only one connection per user can be the default.
3. Setting a new default clears the old one.
4. Deleting the default promotes the next connection.
5. Duplicate store URLs per user are rejected (409).

### Billing

1. Plans listing is public (no auth required).
2. Checkout creates a subscription in mock mode.
3. Plan limits are immediately enforced after plan change.
4. Webhook events correctly update subscription state.
5. Cancellation downgrades user to free plan.

---

## Regression Test Checklist

Before each release, verify:

- [ ] All 130 backend tests pass (`pytest -v`)
- [ ] Authentication flow works (register -> login -> access protected endpoint -> refresh)
- [ ] Import creation respects plan limits
- [ ] Bulk import creates correct number of jobs
- [ ] Cancel and retry work for appropriate statuses
- [ ] Store connection default management is correct
- [ ] Price watch sync updates prices and flags changes
- [ ] Billing checkout works in mock mode
- [ ] Stripe webhook updates subscription and user plan
- [ ] API key creation returns raw key, list does not
- [ ] Health check returns 200 with correct payload
- [ ] Dashboard loads all pages without errors
- [ ] KPI cards show correct counts
