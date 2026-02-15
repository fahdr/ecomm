# QA Engineer Guide

> Part of [AdScale](README.md) documentation

**For QA Engineers:** This guide covers acceptance criteria, verification checklists, and edge case testing for the AdScale AI Ad Campaign Manager service. AdScale manages advertising campaigns across Google Ads and Meta Ads with AI-generated ad copy, automated optimization rules, and ROAS-based performance tracking.

For test infrastructure details, see **[Testing Guide](TESTING.md)**.
For API endpoint specifications, see **[API Reference](API_REFERENCE.md)**.

---

## Verification Checklist

### Authentication Flow

- [ ] Register new user returns `201` with `access_token` and `refresh_token`
- [ ] Duplicate email registration returns `409`
- [ ] Short password (< 8 chars) returns `422`
- [ ] Login with correct credentials returns `200` with tokens
- [ ] Login with wrong password returns `401`
- [ ] Token refresh with valid refresh_token returns new token pair
- [ ] Token refresh with access_token (wrong type) returns `401`
- [ ] `/auth/me` with valid token returns user profile with `plan: "free"`
- [ ] All protected endpoints return `401` without authentication

### Ad Account Management

- [ ] Connect Google Ads account returns `201` with `platform: "google"`, `is_connected: true`, `status: "active"`
- [ ] Connect Meta Ads account returns `201` with `platform: "meta"`
- [ ] Duplicate connection (same external ID + platform) returns `409`
- [ ] Same external ID on different platforms does NOT conflict
- [ ] List accounts with pagination (offset/limit) returns correct `total`, `items`, `offset`, `limit`
- [ ] User A cannot see User B's accounts
- [ ] Disconnect sets `is_connected: false`, `status: "paused"`
- [ ] Disconnect nonexistent account returns `404`
- [ ] Invalid UUID format returns `400`

### Campaign Management

- [ ] Create campaign with all 4 objectives: traffic, conversions, awareness, sales
- [ ] Create campaign with daily budget vs. lifetime budget
- [ ] Campaign platform is auto-set from ad account platform
- [ ] Campaign status defaults to `draft`
- [ ] List campaigns returns paginated results
- [ ] Update campaign name, budget, status, objective via `PATCH`
- [ ] Delete campaign returns `204` and cascades to ad groups
- [ ] User isolation: User B cannot see/modify/delete User A's campaigns
- [ ] Plan limit enforcement: Free user with 2 campaigns gets `403` on 3rd

### Ad Group Management

- [ ] Create ad group with targeting JSON and bid strategy
- [ ] Ad group validates campaign ownership
- [ ] List ad groups with optional `campaign_id` filter
- [ ] Plan limit enforcement: Free user with 5 ad groups gets `403` on 6th
- [ ] Delete ad group cascades to creatives

### Creative Management

- [ ] Create creative with headline, description, destination URL, CTA
- [ ] Creative validates ownership through full chain (ad_group -> campaign -> user)
- [ ] List creatives with optional `ad_group_id` filter
- [ ] AI copy generation returns non-empty `headline`, `description`, `call_to_action`
- [ ] AI copy generation with all optional fields (target_audience, tone)

### Optimization Rules

- [ ] Create rules with all 4 types: `pause_low_roas`, `scale_high_roas`, `adjust_bid`, `increase_budget`
- [ ] Rules accept arbitrary JSON conditions
- [ ] Execute-now with no active campaigns returns `campaigns_affected: 0`
- [ ] Rule execution increments `executions_count` and sets `last_executed`
- [ ] User isolation on all rule operations

### Billing

- [ ] `/billing/plans` returns 3 tiers: free, pro, enterprise (public, no auth)
- [ ] Free plan: `price_monthly_cents: 0`, `trial_days: 0`
- [ ] Checkout for Pro plan returns `checkout_url` and `session_id`
- [ ] Checkout for Free plan returns `400`
- [ ] Duplicate subscription returns `400`
- [ ] Billing overview reflects current plan and usage metrics

### API Keys

- [ ] Create key returns raw key (only time it is shown)
- [ ] List keys does NOT include raw key values
- [ ] Revoked key shows `is_active: false` in list
- [ ] `X-API-Key` header successfully authenticates to `/usage`
- [ ] Invalid API key returns `401`

---

## Feature Verification Matrix

| Feature | Free Tier | Pro Tier | Enterprise Tier |
|---------|-----------|----------|-----------------|
| Campaigns | Up to 2 | Up to 25 | Unlimited |
| Ad Groups | Up to 5 | Up to 100 | Unlimited |
| Platforms | 1 (Google OR Meta) | Google + Meta | All + API |
| AI Copy | 5/month | Unlimited | Priority AI |
| Auto-Optimization | Manual only | Yes + ROAS tracking | Yes + ROAS targets |
| API Key Access | No | Yes | Yes |
| Trial Days | None | 14 days | 14 days |

### Error Response Format

All error responses follow this structure:

```json
{
  "detail": "Human-readable error message"
}
```

Validation errors (422) include field-level details:

```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "error description",
      "type": "error_type"
    }
  ]
}
```

---

## Edge Cases to Test

### Resource Ownership Chain

- Creating a creative with an ad group owned by another user
- Updating a campaign that belongs to another user
- Deleting an ad account while campaigns are active (should cascade properly)

### Plan Limits

- Upgrading from Free to Pro should unlock additional campaign slots immediately
- Downgrading from Pro to Free with 10 active campaigns (should be handled gracefully)
- Creating resources at exact plan limit boundary

### Pagination

- Listing with offset=0, limit=0 (should return empty items, total > 0)
- Listing with offset > total (should return empty items)
- Listing with negative offset or limit (should return 422)

### Metrics Computation

- Campaign with zero spend (ROAS should be null, not division error)
- Campaign with zero conversions (CPA should be null)
- Campaign with zero impressions (CTR should be null)

### AI Copy Generation

- Product name with special characters or emojis
- Very long product description (> 1000 chars)
- Empty target audience or tone (should use defaults)

### Rule Execution

- Executing a rule when user has no campaigns
- Executing a rule when all campaigns are paused (not active)
- Executing a rule with threshold=0 (should handle edge case)

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
