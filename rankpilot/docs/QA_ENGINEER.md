# RankPilot QA Engineer Guide

> Part of [RankPilot](README.md) documentation

**For testing infrastructure and running tests**, see [TESTING.md](TESTING.md).
**For API endpoint documentation**, see [API_REFERENCE.md](API_REFERENCE.md).

This guide provides acceptance criteria, manual verification checklists, and edge case testing guidance for RankPilot features.

---

## Manual Verification Checklist

### Authentication Flow

- [ ] Register new user returns 201 with `access_token` and `refresh_token`
- [ ] Register with duplicate email returns 409
- [ ] Register with short password (< 8 chars) returns 422
- [ ] Login with valid credentials returns 200 with tokens
- [ ] Login with wrong password returns 401
- [ ] Login with non-existent email returns 401
- [ ] Refresh with valid refresh token returns new token pair
- [ ] Refresh with access token (wrong type) returns 401
- [ ] GET /auth/me returns user profile with email, plan, is_active
- [ ] GET /auth/me without token returns 401

### Site Management

- [ ] Create site returns 201 with `domain`, `is_verified=false`, `status="pending"`
- [ ] Create site with sitemap_url stores the URL
- [ ] Create duplicate domain for same user returns 400
- [ ] Create site with domain < 3 chars returns 422
- [ ] Create site without auth returns 401
- [ ] List sites returns paginated response scoped to authenticated user
- [ ] List sites with pagination respects `page` and `per_page` params
- [ ] Get site by ID returns 200
- [ ] Get non-existent site returns 404
- [ ] Get another user's site returns 404
- [ ] Update site domain, sitemap_url, and status via PATCH
- [ ] Delete site returns 204, subsequent GET returns 404
- [ ] Delete another user's site returns 404
- [ ] Verify site sets `is_verified=true` and `status="active"`
- [ ] Verify non-existent site returns 404
- [ ] Verify another user's site returns 404

### Blog Posts

- [ ] Create post returns 201 with title, slug, status="draft", word_count
- [ ] Create post with content calculates word_count > 0
- [ ] Create post with keywords stores the keyword list
- [ ] Create post with meta_description stores it
- [ ] Create post for non-existent site returns 404
- [ ] Create post without auth returns 401
- [ ] Create post with empty title returns 422
- [ ] List posts returns paginated response
- [ ] List posts with site_id filter returns only matching posts
- [ ] Get post by ID returns correct post
- [ ] Get non-existent post returns 404
- [ ] Get another user's post returns 404
- [ ] Update post title, content, keywords, status via PATCH
- [ ] Updating content recalculates word_count
- [ ] Setting status to "published" populates published_at timestamp
- [ ] Delete post returns 204
- [ ] AI generate fills in content and meta_description
- [ ] AI generate for non-existent post returns 404
- [ ] AI generate for another user's post returns 404

### Keyword Tracking

- [ ] Add keyword returns 201 with keyword, site_id, tracked_since
- [ ] Add duplicate keyword for same site returns 400
- [ ] Add keyword for non-existent site returns 404
- [ ] Add keyword without auth returns 401
- [ ] Add keyword for another user's site returns 404
- [ ] List keywords by site_id returns paginated response
- [ ] List keywords with pagination works correctly
- [ ] List keywords for non-existent site returns 404
- [ ] Delete keyword returns 204, removed from list
- [ ] Delete non-existent keyword returns 404
- [ ] Delete keyword with wrong site_id returns 404
- [ ] Refresh ranks returns updated count and message
- [ ] Refresh ranks for non-existent site returns 404

### SEO Audits

- [ ] Run audit returns 201 with overall_score (0-100), issues list, recommendations list
- [ ] Audit issues have severity, category, and message fields
- [ ] Run audit for non-existent site returns 404
- [ ] Run audit without auth returns 401
- [ ] Run audit for another user's site returns 404
- [ ] Running multiple audits creates separate records
- [ ] List audits by site_id returns paginated response
- [ ] List audits with pagination works correctly
- [ ] List audits for non-existent site returns 404
- [ ] Get audit by ID returns correct audit with matching score
- [ ] Get non-existent audit returns 404
- [ ] Get another user's audit returns 404

### Schema Markup

- [ ] Create schema config returns 201 with page_type and schema_json
- [ ] Creating without custom schema_json generates default template
- [ ] Supported page types: product, article, faq, breadcrumb, organization
- [ ] Get schema config by ID returns correct config
- [ ] List schema configs by site_id returns paginated response
- [ ] Update schema_json and is_active via PATCH
- [ ] Delete schema config returns 204
- [ ] Preview returns rendered `<script type="application/ld+json">` tag
- [ ] Cross-user access to schema configs returns 404

### Billing

- [ ] List plans returns 3 tiers (free, pro, enterprise) -- no auth required
- [ ] Free plan has price_monthly_cents=0 and trial_days=0
- [ ] Checkout for pro plan returns 201 with checkout_url and session_id
- [ ] Checkout for free plan returns 400
- [ ] Duplicate checkout (already subscribed) returns 400
- [ ] Billing overview returns current_plan, plan_name, usage metrics
- [ ] Billing overview reflects plan upgrade after checkout
- [ ] Get current subscription returns null when unsubscribed
- [ ] Get current subscription returns subscription data after checkout

### API Keys

- [ ] Create API key returns 201 with raw key (shown once)
- [ ] Raw key is 20+ characters long
- [ ] List API keys returns key metadata without raw key values
- [ ] Revoke key sets is_active=false (returns 204)
- [ ] API key authentication works via X-API-Key header on /usage endpoint
- [ ] Invalid API key returns 401

---

## Feature Verification Tips

### Mock Implementations

Several features use mock implementations that return realistic but deterministic data:

1. **Domain Verification** (`POST /sites/{id}/verify`): Always succeeds. Sets `verification_method="mock_verification"`.
2. **AI Blog Generation** (`POST /blog-posts/generate`): Generates placeholder content based on the post title and keywords. Content includes headings, bullet points, and SEO-friendly structure.
3. **Keyword Rank Refresh** (`POST /keywords/refresh`): Assigns random ranks (1-100), search volumes (100-50000), and difficulty scores (10.0-90.0). Preserves `previous_rank` for trend tracking.
4. **SEO Audits** (`POST /audits/run`): Randomly selects from 12 issue templates and 12 recommendation templates. Score is calculated based on issue severity (critical: -15, warning: -5).

### Plan Limit Enforcement

Test plan limits by creating a free-tier user and attempting to exceed:
- **Blog posts**: Free tier allows 2 posts/month. The 3rd creation should return 403.
- **Keywords**: Free tier allows 20 total keywords. The 21st should return 403.

### Cross-User Isolation

Every resource (sites, posts, keywords, audits, schema configs) is scoped to the owning user. Accessing another user's resource always returns 404 (not 403) to avoid leaking existence information.

### Stripe Mock Mode

When `STRIPE_SECRET_KEY` is empty, the billing system operates in mock mode:
- Checkout creates a mock subscription directly in the database.
- No real Stripe API calls are made.
- Webhooks accept raw JSON without signature verification.

---

*See also: [Testing Guide](TESTING.md) · [API Reference](API_REFERENCE.md) · [Setup](SETUP.md)*
