# QA Engineer Guide

> Part of [SpyDrop](README.md) documentation

**For QA Engineers:** This guide covers acceptance criteria, verification checklists, and edge cases for SpyDrop features. For test infrastructure and running tests, see [Testing](TESTING.md). For API documentation, see [API Reference](API_REFERENCE.md).

---

## Verification Checklist

### Authentication Flow
- [ ] Register with valid email/password -> 201 with tokens
- [ ] Register with existing email -> 409
- [ ] Register with password < 8 chars -> 422
- [ ] Login with valid credentials -> 200 with tokens
- [ ] Login with wrong password -> 401
- [ ] Login with nonexistent email -> 401
- [ ] Refresh with valid refresh token -> 200 with new tokens
- [ ] Refresh with access token (not refresh) -> 401
- [ ] GET /me with valid token -> 200 with user profile
- [ ] GET /me without token -> 401

### Competitor Management
- [ ] Create competitor with name + URL -> 201 with status "active", product_count 0
- [ ] Create without name -> 422
- [ ] Create without URL -> 422
- [ ] Create without auth -> 401
- [ ] Create 4th competitor on free plan -> 403 with plan limit message
- [ ] List competitors -> paginated response with correct total
- [ ] List with pagination params -> correct page/per_page in response
- [ ] Get single competitor by UUID -> 200 with all fields
- [ ] Get with invalid UUID -> 400
- [ ] Get nonexistent UUID -> 404
- [ ] Get another user's competitor -> 404 (not 403)
- [ ] PATCH update name only -> name changes, other fields unchanged
- [ ] PATCH update status to "paused" -> status changes
- [ ] PATCH multiple fields at once -> all provided fields change
- [ ] DELETE competitor -> 204, subsequent GET returns 404
- [ ] DELETE cascades products, scans, alerts, source matches

### Product Tracking
- [ ] List products for user with no competitors -> empty list, total 0
- [ ] List products after seeding -> correct total and items
- [ ] Filter by `?status=active` -> only active products returned
- [ ] Filter by `?status=removed` -> only removed products returned
- [ ] Sort by `?sort_by=price` -> ascending price order
- [ ] Sort by `?sort_by=title` -> alphabetical order
- [ ] Product detail includes `price_history` array
- [ ] Product detail includes `competitor_name`
- [ ] Products from user A invisible to user B

### Billing
- [ ] GET /plans -> 3 tiers (free: $0, pro: $29, enterprise: $99)
- [ ] Checkout pro plan -> 201 with checkout_url and session_id
- [ ] Checkout free plan -> 400
- [ ] Checkout with existing subscription -> 400
- [ ] Overview shows current plan and usage metrics
- [ ] Overview reflects upgraded plan after checkout

### API Keys
- [ ] Create key -> raw key in response, key_prefix matches
- [ ] List keys -> no raw key exposed, key_prefix present
- [ ] Revoke key -> key becomes inactive
- [ ] Auth with valid API key via X-API-Key header -> 200
- [ ] Auth with invalid API key -> 401

---

## Feature Verification

### Alert Types to Test
| Alert Type | Trigger Condition |
|-----------|-------------------|
| `price_drop` | Scan detects price decrease on monitored products |
| `price_increase` | Scan detects price increase on monitored products |
| `new_product` | Scan discovers new products on competitor store |
| `out_of_stock` | Scan detects products removed from competitor |
| `back_in_stock` | Scan detects previously removed products re-appearing |

### Plan Limits to Verify
| Resource | Free | Pro | Enterprise |
|----------|------|-----|------------|
| Competitors | 3 | 25 | Unlimited (-1) |
| Products tracked | 50 | 2,500 | Unlimited (-1) |
| Scan frequency | Weekly | Daily | Hourly |
| Price alerts | No | Yes | Yes + API |
| Source finding | No | Yes | Yes + Bulk |
| Trial days | 0 | 14 | 14 |
| API access | No | Yes | Yes |

### Dashboard Pages to Verify
| Page | Route | Key Behaviors |
|------|-------|--------------|
| Dashboard Home | `/` | KPI cards load, animated counters, quick action links work |
| Competitors | `/competitors` | Table displays, add dialog validates fields, delete confirms, pagination |
| Products | `/products` | Grid displays, filters toggle, sort works, price history dialog opens |
| Billing | `/billing` | Plan cards display correct pricing, checkout redirects |
| API Keys | `/api-keys` | Create shows raw key once, list hides raw key, revoke works |
| Settings | `/settings` | User settings display and save |
| Login | `/login` | Form validates, redirects on success |
| Register | `/register` | Form validates, redirects on success |

---

*See also: [Testing](TESTING.md) · [API Reference](API_REFERENCE.md) · [Setup](SETUP.md) · [README](README.md)*
