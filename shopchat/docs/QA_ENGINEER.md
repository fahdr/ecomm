# QA Engineer Guide

> Part of [ShopChat](README.md) documentation

**For QA Engineers:** This guide covers acceptance criteria, verification checklists, and edge cases for the ShopChat AI Shopping Assistant service.

**See also:** [Testing Guide](TESTING.md) for test infrastructure and running tests · [API Reference](API_REFERENCE.md) for endpoint documentation

---

## Verification Checklist

### Authentication

- [ ] Register with valid email + password (201, returns tokens)
- [ ] Register with duplicate email returns 409
- [ ] Register with short password (<8 chars) returns 422
- [ ] Login with valid credentials returns 200 with tokens
- [ ] Login with wrong password returns 401
- [ ] Login with nonexistent email returns 401
- [ ] Refresh with valid refresh token returns new token pair
- [ ] Refresh with access token (wrong type) returns 401
- [ ] GET /auth/me with valid token returns user profile
- [ ] GET /auth/me without token returns 401

### Chatbot CRUD

- [ ] Create chatbot returns 201 with `widget_key`, `id`, `created_at`
- [ ] Create chatbot with custom personality and welcome_message
- [ ] Create chatbot with custom theme_config stores correctly
- [ ] Create chatbot without auth returns 401
- [ ] Create chatbot with empty name returns 422
- [ ] List chatbots returns paginated response (items, total, page, page_size)
- [ ] List chatbots with pagination parameters works correctly
- [ ] List chatbots only shows current user's chatbots (user scoping)
- [ ] Get chatbot by ID returns correct details
- [ ] Get nonexistent chatbot returns 404
- [ ] Get another user's chatbot returns 404 (not 403)
- [ ] Update chatbot name preserves other fields
- [ ] Update chatbot personality, welcome_message, theme_config, is_active
- [ ] Update nonexistent chatbot returns 404
- [ ] Delete chatbot returns 204 and removes it from list
- [ ] Delete another user's chatbot returns 404
- [ ] Each chatbot has a unique widget_key

### Knowledge Base

- [ ] Create entry with chatbot_id, title, content, source_type returns 201
- [ ] Create entry with metadata stores correctly
- [ ] Create entry for nonexistent chatbot returns 404
- [ ] Create entry for another user's chatbot returns 404
- [ ] Create entry without auth returns 401
- [ ] Create entry with empty title or content returns 422
- [ ] List entries returns all entries across user's chatbots
- [ ] List entries with `chatbot_id` filter returns only that chatbot's entries
- [ ] List entries with pagination works correctly
- [ ] List entries with nonexistent chatbot_id returns 404
- [ ] List entries does not return other users' entries
- [ ] Get single entry by ID returns correct data
- [ ] Get nonexistent entry returns 404
- [ ] Get another user's entry returns 404
- [ ] Update entry title, content, source_type, metadata, is_active
- [ ] Update nonexistent entry returns 404
- [ ] Update another user's entry returns 404
- [ ] Delete entry returns 204, reduces list count
- [ ] Delete another user's entry returns 404
- [ ] All source types accepted: `product_catalog`, `policy_page`, `faq`, `custom_text`, `url`

### Conversations

- [ ] List conversations returns paginated response
- [ ] List conversations with chatbot_id filter
- [ ] List conversations with pagination
- [ ] List conversations does not show other users' conversations
- [ ] Get conversation detail includes messages array
- [ ] Messages include user message and assistant response (at least 2)
- [ ] Get nonexistent conversation returns 404
- [ ] Get another user's conversation returns 404
- [ ] End active conversation sets status to "ended" and ended_at
- [ ] End already-ended conversation returns 400
- [ ] End nonexistent conversation returns 404
- [ ] Rate conversation with score 1.0-5.0 stores correctly
- [ ] Rate with score < 1.0 returns 422
- [ ] Rate with score > 5.0 returns 422
- [ ] Rate nonexistent conversation returns 404
- [ ] Rate another user's conversation returns 404
- [ ] Message count increments with each message pair

### Widget (Public API -- no auth)

- [ ] GET `/widget/config/{widget_key}` returns chatbot config without auth
- [ ] Config includes chatbot_name, personality, welcome_message, theme_config, is_active
- [ ] Config with custom theme returns correct theme values
- [ ] Config with invalid widget_key returns 404
- [ ] Config with inactive chatbot returns 404
- [ ] POST `/widget/chat` sends message and receives AI response without auth
- [ ] Chat response includes conversation_id, message, product_suggestions
- [ ] Chat creates new conversation on first message from a visitor
- [ ] Chat continues same conversation for same visitor_id
- [ ] Chat creates separate conversations for different visitor_ids
- [ ] Chat stores visitor_name if provided
- [ ] Chat with invalid widget_key returns 404
- [ ] Chat with inactive chatbot returns 404
- [ ] Chat with empty message returns 422
- [ ] Chat with missing visitor_id returns 422
- [ ] Chat uses knowledge base entries for contextual responses
- [ ] Chat returns product suggestions from catalog entries

### Analytics

- [ ] Overview returns total_conversations, total_messages, avg_satisfaction, active_chatbots, conversations_today
- [ ] Per-chatbot analytics returns breakdown for each chatbot
- [ ] Analytics handles zero data (new account) gracefully
- [ ] Analytics handles null satisfaction scores correctly

### Billing

- [ ] List plans returns 3 tiers (free, pro, enterprise) with pricing
- [ ] Checkout for pro plan returns checkout_url and session_id
- [ ] Checkout for free plan returns 400
- [ ] Duplicate subscription checkout returns 400
- [ ] Billing overview shows current plan, subscription status, and usage
- [ ] Current subscription returns null when no subscription
- [ ] Current subscription returns subscription data after checkout

### API Keys

- [ ] Create API key returns raw key (shown only once)
- [ ] List API keys returns key_prefix but NOT the raw key
- [ ] Revoke API key sets is_active to false
- [ ] Auth via X-API-Key header works for usage endpoint
- [ ] Invalid API key returns 401

---

## Feature Verification

### Plan Limit Enforcement

| Resource | Free | Pro | Enterprise |
|----------|------|-----|-----------|
| Conversations/month | 50 | 1,000 | Unlimited |
| Knowledge base pages | 10 | 500 | Unlimited |
| Trial days | 0 | 14 | 14 |
| API access | No | Yes | Yes |

- [ ] Free user creating 11th knowledge entry gets 403
- [ ] Pro user creating 501st knowledge entry gets 403
- [ ] Enterprise user can create unlimited entries
- [ ] Free user with 51st conversation gets 429 on widget chat
- [ ] Enterprise user can have unlimited conversations

### Cross-User Security

Every endpoint that retrieves, updates, or deletes a resource must return 404 (not 403) when a different user's resource is accessed. This prevents information leakage about resource existence.

- [ ] Chatbot: GET, PATCH, DELETE of another user's chatbot returns 404
- [ ] Knowledge: GET, PATCH, DELETE of another user's entry returns 404
- [ ] Conversation: GET, end, rate of another user's conversation returns 404

---

*See also: [Testing](TESTING.md) · [API Reference](API_REFERENCE.md) · [Setup](SETUP.md) · [README](README.md)*
