# FlowSend -- QA Engineer Guide

> Part of [FlowSend](README.md) documentation

This guide provides acceptance criteria, verification checklists, and edge cases for QA engineers testing FlowSend.

**Related Documentation:**
- [Testing Guide](TESTING.md) — Test infrastructure, running tests, writing new tests
- [API Reference](API_REFERENCE.md) — Complete API endpoint documentation

---

## CAN-SPAM Compliance Testing

FlowSend includes CAN-SPAM compliance features that must be verified:

1. **Unsubscribe handling**: When a contact's `is_subscribed` is set to `false`, the `unsubscribed_at` timestamp is automatically recorded.
2. **Unsubscribe records table**: A dedicated `unsubscribes` table tracks all unsubscribe events.
3. **Contact subscription status**: Every contact has `is_subscribed` (boolean) and `unsubscribed_at` (datetime) fields.
4. **Campaign send filtering**: The mock send function (`send_campaign_mock`) only creates `EmailEvent` records for subscribed contacts (`is_subscribed=True`).
5. **Import deduplication**: Bulk import respects existing contacts and does not re-subscribe unsubscribed contacts.

### CAN-SPAM Test Scenarios

- Create a contact, unsubscribe them via PATCH (`is_subscribed: false`), verify `unsubscribed_at` is set.
- Send a campaign with both subscribed and unsubscribed contacts, verify only subscribed contacts receive email events.
- Import contacts that already exist -- verify they are skipped, not re-subscribed.

---

## Verification Checklist

### Authentication
- [ ] Registration returns 201 with access + refresh tokens
- [ ] Duplicate email registration returns 409
- [ ] Short password (<8 chars) returns 422
- [ ] Login with valid credentials returns 200 with tokens
- [ ] Login with wrong password returns 401
- [ ] Login with nonexistent email returns 401
- [ ] Token refresh with valid refresh token returns new tokens
- [ ] Token refresh with access token returns 401
- [ ] GET /auth/me returns user profile with plan and active status
- [ ] All protected endpoints return 401 without token

### Contacts
- [ ] Create contact with full payload returns 201
- [ ] Create contact with only email (minimal) returns 201
- [ ] Create contact with invalid email returns 422
- [ ] Create duplicate email returns 400
- [ ] List contacts with pagination works correctly
- [ ] Search by email substring filters correctly
- [ ] Tag filter returns only matching contacts
- [ ] Get contact by UUID returns correct data
- [ ] Get contact with unknown UUID returns 404
- [ ] Update contact partially (only provided fields change)
- [ ] Unsubscribe via PATCH (`is_subscribed: false`) works
- [ ] Delete contact returns 204, subsequent GET returns 404
- [ ] Import email list creates correct number of contacts
- [ ] Import with duplicates reports correct skipped count
- [ ] Import CSV with first_name/last_name columns works
- [ ] Contact count endpoint reflects actual count
- [ ] Contact lists: create static, create dynamic (with rules), list, delete

### Flows
- [ ] Create flow in draft status with all fields
- [ ] Create flow with only required fields (name, trigger_type)
- [ ] All trigger types accepted: signup, purchase, abandoned_cart, custom, scheduled
- [ ] Missing name returns 422
- [ ] Missing trigger_type returns 422
- [ ] List flows with pagination works
- [ ] Status filter (draft, active, paused) works
- [ ] Get flow by UUID returns correct data
- [ ] Update draft flow changes only provided fields
- [ ] Delete flow returns 204
- [ ] Activate flow with steps transitions to "active"
- [ ] Activate flow without steps returns 400
- [ ] Pause active flow transitions to "paused"
- [ ] Pause draft flow returns 400
- [ ] Update active flow returns 400 (must pause first)
- [ ] Update paused flow succeeds
- [ ] Reactivate paused flow transitions back to "active"
- [ ] List flow executions returns paginated results

### Campaigns
- [ ] Create draft campaign (no scheduled_at)
- [ ] Create scheduled campaign (with scheduled_at)
- [ ] Missing name or subject returns 422
- [ ] List campaigns with pagination works
- [ ] Status filter (draft, scheduled, sent) works
- [ ] Get campaign by UUID returns correct data
- [ ] Update draft campaign changes fields
- [ ] Delete draft campaign returns 204
- [ ] Send campaign transitions to "sent" with sent_at timestamp
- [ ] Send already-sent campaign returns 400
- [ ] Delete sent campaign returns 400
- [ ] Campaign analytics returns totals and rates
- [ ] Campaign events returns paginated email events

### Templates
- [ ] Create template with all fields returns 201 with is_system=false
- [ ] Create minimal template uses default category "newsletter"
- [ ] Missing required fields (name, subject, html_content) returns 422
- [ ] Empty name returns 422
- [ ] List templates includes custom and system templates
- [ ] Category filter works correctly
- [ ] Update custom template changes only provided fields
- [ ] Delete custom template returns 204
- [ ] System templates cannot be updated (400)
- [ ] System templates cannot be deleted (400)

### Billing
- [ ] List plans returns all 3 tiers (free, pro, enterprise) -- public endpoint
- [ ] Plan pricing is correct (0, 3900, 14900 cents)
- [ ] Checkout for pro plan returns 201 with checkout URL
- [ ] Checkout for free plan returns 400
- [ ] Duplicate subscription checkout returns 400
- [ ] Billing overview shows correct plan and usage metrics
- [ ] Overview reflects plan change after checkout
- [ ] Current subscription is null for free users
- [ ] Current subscription shows plan and status after checkout

### API Keys
- [ ] Create key returns 201 with raw key (shown once)
- [ ] List keys returns metadata without raw keys
- [ ] Revoke key marks it as inactive (is_active=false)
- [ ] Auth via X-API-Key header works for usage endpoint
- [ ] Invalid API key returns 401

---

## Feature Verification

### Dashboard Pages (9 pages)

| Page | Route | Key Elements to Verify |
|------|-------|----------------------|
| Dashboard Home | `/` | KPI cards (plan, API calls, API keys), quick action buttons, loading skeletons |
| Contacts | `/contacts` | Contact table, search, import dialog, create/edit/delete dialogs, pagination |
| Flows | `/flows` | Flow list with status icons, status filter tabs, create/edit/activate/pause/delete dialogs |
| Campaigns | `/campaigns` | Campaign list, status filter, create/edit/send/delete dialogs, analytics dialog |
| Templates | `/templates` | (verify navigation route exists) |
| Analytics | `/analytics` | (verify navigation route exists) |
| API Keys | `/api-keys` | Key list, create dialog, revoke confirmation |
| Billing | `/billing` | Plan cards, checkout flow, current subscription display |
| Settings | `/settings` | Account settings |
| Login | `/login` | Email/password form, error handling |
| Register | `/register` | Email/password form, validation |

### Cross-Browser Verification

- Verify all dashboard pages render correctly in Chrome, Firefox, and Safari.
- Verify responsive layout collapses grid on mobile viewports.
- Verify OKLCH colors render with hex fallbacks in older browsers.
- Verify Satoshi and Source Sans 3 fonts load correctly.

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
