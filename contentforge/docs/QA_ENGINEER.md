# QA Engineer Guide

> Part of [ContentForge](README.md) documentation

**For QA Engineers:** This guide covers acceptance criteria, verification checklists, and edge cases for manual testing of ContentForge.

**For test infrastructure and automated testing:** See [Testing Guide](TESTING.md)

**For API endpoint documentation:** See [API Reference](API_REFERENCE.md)

---

## Acceptance Criteria

### Content Generation

**AC1:** User can generate content from a product URL
- Given a valid product URL
- When user submits to `/content/generate`
- Then job completes with 5 content types (title, description, meta_description, keywords, bullet_points)

**AC2:** User can generate content from manual data entry
- Given product name, price, category, features
- When user submits to `/content/generate` with `source_type: "manual"`
- Then job completes with requested content types

**AC3:** Plan limits are enforced
- Given a Free tier user with 10 generations in the current month
- When user attempts an 11th generation
- Then request returns 403 with "limit" in the error message

**AC4:** Image optimization respects limits
- Given a Free tier user with 5 images in the current month
- When user attempts to generate with additional `image_urls`
- Then request returns 403 with image limit message

**AC5:** Bulk generation works for Pro/Enterprise users
- Given a Pro tier user
- When user submits multiple URLs via `/content/generate/bulk`
- Then all jobs complete successfully

### Template Management

**AC6:** Users can create custom templates
- Given authenticated user
- When user submits template with name, tone, style
- Then template is created with `is_system: false`

**AC7:** System templates are read-only
- Given a system template (Professional, Casual, Luxury, SEO-Focused)
- When user attempts to PATCH or DELETE
- Then request returns 403

**AC8:** Custom templates can be updated
- Given a custom template owned by the user
- When user submits PATCH with updated fields
- Then only specified fields are updated

### Image Management

**AC9:** Images are listed across all jobs
- Given user has images from multiple generation jobs
- When user requests `/images/`
- Then all images are returned in paginated list

**AC10:** Deleting an image does not delete the parent job
- Given a job with images
- When user deletes an image via `/images/{id}`
- Then image is deleted but job remains accessible

### Billing

**AC11:** Users can upgrade to Pro or Enterprise
- Given a Free tier user
- When user submits `/billing/checkout` with tier "pro"
- Then checkout session is created (or subscription in mock mode)

**AC12:** Users cannot create duplicate subscriptions
- Given a user with an active subscription
- When user attempts another checkout
- Then request returns 400

**AC13:** Billing overview reflects current usage
- Given a user with N generations and M images in the current period
- When user requests `/billing/overview`
- Then `usage.generations_used` equals N and `usage.images_used` equals M

### API Keys

**AC14:** API keys are created with secure hashing
- Given an authenticated user
- When user creates an API key
- Then raw key is returned once, SHA-256 hash stored in DB

**AC15:** API keys can authenticate requests
- Given a valid API key
- When request includes `X-API-Key: <key>` header
- Then user is authenticated (e.g., on `/usage` endpoint)

---

## Verification Checklist

### Pre-Release Checklist

Before releasing a new version, verify the following:

- [ ] All 116 backend tests pass (`make test-backend`)
- [ ] Health endpoint returns 200 (`GET /health`)
- [ ] Swagger docs are accessible (`http://localhost:8102/docs`)
- [ ] Dashboard loads without console errors
- [ ] Landing page renders correctly

### Authentication Flow

### Authentication Flow

- [ ] Register with valid email/password -- returns 201 with access and refresh tokens
- [ ] Register with duplicate email -- returns 409
- [ ] Register with short password (< 8 chars) -- returns 422
- [ ] Login with correct credentials -- returns 200 with tokens
- [ ] Login with wrong password -- returns 401
- [ ] Login with nonexistent email -- returns 401
- [ ] Refresh with valid refresh token -- returns 200 with new tokens
- [ ] Refresh with access token (not refresh) -- returns 401
- [ ] GET /auth/me with valid token -- returns 200 with user profile
- [ ] GET /auth/me without token -- returns 401

### Content Generation Flow

- [ ] Create generation from URL -- job completed with 5 content types
- [ ] Create generation from manual data -- job completed with requested content types
- [ ] Free tier: 11th generation -- returns 403 with "limit" in message
- [ ] List jobs with pagination -- correct total, page, per_page
- [ ] Get job by ID -- includes content_items and image_items
- [ ] Delete job -- returns 204, subsequent GET returns 404
- [ ] Edit content text -- returns updated content with recalculated word_count
- [ ] Bulk generation from URLs -- creates multiple completed jobs
- [ ] Generation with image_urls -- creates image_items with completed status
- [ ] User A cannot access User B's jobs -- returns 404

### Template Management

- [ ] Create custom template -- returns 201 with all fields
- [ ] Create with minimal fields -- defaults applied (professional tone, detailed style)
- [ ] List templates -- includes both system and custom templates
- [ ] Get template by ID -- returns correct template
- [ ] Partial update (PATCH) -- only updates provided fields
- [ ] Full update (PATCH) -- all fields updated including prompt_override
- [ ] Delete custom template -- returns 204, subsequent GET returns 404
- [ ] System template visible to all users
- [ ] System template PATCH -- returns 403
- [ ] System template DELETE -- returns 403
- [ ] User A cannot access User B's custom templates

### Image Management

- [ ] List images -- paginated, includes format/width/height/size_bytes
- [ ] List images pagination -- correct page sizes
- [ ] Empty image list -- returns `{ items: [], total: 0 }`
- [ ] Get image by ID -- correct fields
- [ ] Delete image -- returns 204, does NOT delete parent job
- [ ] User A cannot access User B's images
- [ ] Images from multiple jobs appear in same list

### Billing

- [ ] GET /billing/plans -- returns 3 plans (free, pro, enterprise) with pricing
- [ ] Checkout pro plan -- returns 201 with checkout_url and session_id
- [ ] Checkout free plan -- returns 400
- [ ] Duplicate subscription -- returns 400
- [ ] Billing overview -- includes current_plan, plan_name, usage metrics
- [ ] Current subscription (no subscription) -- returns null
- [ ] Current subscription (after checkout) -- returns active subscription

### API Keys

- [ ] Create key -- returns 201 with raw key (shown once)
- [ ] List keys -- returns keys without raw key values
- [ ] Revoke key -- returns 204, key marked as inactive
- [ ] Auth via X-API-Key header -- returns 200 on /usage endpoint
- [ ] Auth via invalid API key -- returns 401

---

## Edge Cases

### Authentication Edge Cases

- **Expired access token:** Refresh token should still work
- **Expired refresh token:** User must log in again
- **Concurrent logins:** Multiple active sessions supported
- **Password with special characters:** Should be accepted
- **Email with + notation:** Should be accepted (e.g., `user+test@example.com`)

### Content Generation Edge Cases

- **Empty product URL:** Should return 400
- **Malformed URL:** Should return 400
- **Product URL with no product data:** Job may fail gracefully with error message
- **Generation at exactly midnight UTC (billing period boundary):** Should count toward correct period
- **Bulk generation with one failed URL:** Other URLs should still complete

### Template Edge Cases

- **Template with no content types:** Should use default (all 5 types)
- **Template with empty prompt_override:** Should use tone/style defaults
- **Template name with special characters:** Should be accepted
- **Deleting a template in use by a job:** Job should still reference template ID (soft reference)

### Image Edge Cases

- **Image URL returns 404:** Image job should fail gracefully
- **Image URL with no file extension:** Should infer format from content-type header
- **Very large image (>10MB):** Should process but may take longer
- **Image URL with redirect:** Should follow redirect

### Billing Edge Cases

- **Checkout on last day of month:** Next billing period should start 1st of next month
- **Downgrade from Pro to Free:** Should take effect at end of current period
- **Stripe webhook arrives late:** Idempotent handler should process correctly
- **Subscription canceled but still in grace period:** User should retain Pro features until `current_period_end`

---

## Feature Verification

| Feature | Expected Behavior | Endpoint(s) |
|---------|------------------|-------------|
| Plan limit enforcement | Free: 10 gens/month, Pro: 200, Enterprise: unlimited | POST `/content/generate` |
| Image limit enforcement | Free: 5/month, Pro: 100, Enterprise: unlimited | POST `/content/generate` with `image_urls` |
| Content types | title, description, meta_description, keywords, bullet_points | POST `/content/generate` |
| Source types | "url", "manual", "csv" | POST `/content/generate` |
| Job status transitions | pending -> processing -> completed OR failed | GET `/content/jobs/{id}` |
| System template protection | Cannot PATCH or DELETE system templates (403) | PATCH/DELETE `/templates/{id}` |
| User isolation | Users cannot read, update, or delete other users' resources | All authenticated endpoints |
| API key hashing | Keys are SHA-256 hashed; raw key only returned at creation | POST `/api-keys` |
| Mock Stripe mode | Checkout creates subscription directly in DB without Stripe | POST `/billing/checkout` |
| Webhook handling | Processes `customer.subscription.created/updated/deleted` | POST `/webhooks/stripe` |
| Psychological pricing | round_99 ($X.99), round_95 ($X.95), round_00 ($X.00), none | Pricing service (unit tested) |

---

*See also: [README](README.md) · [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
