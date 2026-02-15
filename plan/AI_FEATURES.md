# Feature 5: AI-Driven Marketing Features

Cross-cutting AI capabilities spanning all 10 platform services (9 SaaS + dropshipping core), powered by the centralized LLM Gateway.

---

## Table of Contents

- [1. Developer Documentation](#1-developer-documentation)
- [2. Project Manager Documentation](#2-project-manager-documentation)
- [3. QA Engineer Documentation](#3-qa-engineer-documentation)
- [4. End User Documentation](#4-end-user-documentation)

---

## 1. Developer Documentation

### 1.1 Architecture Overview

All AI features follow a three-layer architecture:

```
Dashboard UI  -->  API Route (FastAPI)  -->  Service Layer  -->  call_llm()  -->  LLM Gateway (port 8200)
                                                                                       |
                                                                          Claude / OpenAI / Gemini
```

- **LLM Gateway** (`llm-gateway/`, port 8200) is the single point of contact for all LLM providers. It handles provider selection, rate limiting, caching, and per-customer cost tracking.
- **`call_llm()`** from `packages/py-core/ecomm_core/llm_client.py` is the unified async client that every service imports. No service imports LLM SDKs directly.
- **`call_llm_mock()`** from the same module provides a deterministic test double with the identical response shape.

### 1.2 Shared Client: `call_llm()`

**Location:** `packages/py-core/ecomm_core/llm_client.py`

```python
async def call_llm(
    prompt: str,
    *,
    system: str = "",
    user_id: str = "",
    service_name: str = "",
    task_type: str = "general",
    max_tokens: int = 1000,
    temperature: float = 0.7,
    json_mode: bool = False,
    gateway_url: str = "http://localhost:8200",
    gateway_key: str = "",
    timeout: float = 60.0,
) -> dict:
```

**Gateway HTTP call:**
```
POST {gateway_url}/api/v1/generate
Headers: X-Service-Key: {gateway_key}
Body: { user_id, service, task_type, prompt, system, max_tokens, temperature, json_mode }
```

**Response shape (returned as dict):**

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str` | Raw LLM output (typically JSON string when `json_mode=True`) |
| `provider` | `str` | Provider used (e.g., `"anthropic"`, `"openai"`, `"google"`) |
| `model` | `str` | Specific model ID (e.g., `"claude-3-sonnet"`) |
| `input_tokens` | `int` | Prompt tokens consumed |
| `output_tokens` | `int` | Completion tokens consumed |
| `cost_usd` | `float` | Cost of this call in USD |
| `cached` | `bool` | Whether the response was served from cache |
| `latency_ms` | `int` | Round-trip latency in milliseconds |

### 1.3 Common Service Pattern

Every service follows the same file structure:

| File | Purpose |
|------|---------|
| `{service}/backend/app/services/ai_suggestions_service.py` | Business logic: builds prompts, calls `call_llm()`, parses responses |
| `{service}/backend/app/api/suggestions.py` | FastAPI router: auth, request validation, delegates to service |
| `{service}/backend/tests/test_ai_suggestions.py` | Pytest: mocks `call_llm()`, tests auth + success + malformed JSON |

**Dropshipping exception:** The dropshipping platform uses `app/api/ai_features.py` and `tests/test_ai_features.py` instead of `suggestions.py` because its AI endpoints are nested under store/product paths.

#### Service layer pattern (common to all):

```python
import json
from datetime import datetime, timezone
from ecomm_core.llm_client import call_llm
from app.config import settings

async def get_ai_suggestions(db: AsyncSession, user_id: str) -> dict:
    result = await call_llm(
        prompt="...",
        system="...",
        user_id=user_id,
        service_name=settings.service_name,
        task_type="...",
        max_tokens=1000,
        temperature=0.7,
        json_mode=True,
        gateway_url=settings.llm_gateway_url,
        gateway_key=settings.llm_gateway_key,
    )
    try:
        parsed = json.loads(result["content"])
    except (json.JSONDecodeError, KeyError):
        parsed = {"suggestions": [result.get("content", "No suggestions available.")]}

    return {
        "suggestions": parsed.get("suggestions", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": result.get("provider", "unknown"),
        "cost_usd": result.get("cost_usd", 0),
    }
```

Key design decisions:
- Every AI function requests `json_mode=True` from the gateway.
- JSON parsing is wrapped in a try/except; malformed LLM output falls back to a raw-string wrapper rather than raising an error.
- Every response includes `generated_at` (ISO 8601), `provider`, and `cost_usd` for audit/billing.
- `settings.llm_gateway_url` and `settings.llm_gateway_key` are read from each service's config.

#### API router pattern (9 SaaS services):

```python
router = APIRouter(prefix="/ai", tags=["ai"])

@router.get("/suggestions")
async def ai_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return await get_ai_suggestions(db, str(current_user.id))
```

All 9 SaaS services mount the suggestions router at `/api/v1/ai/...`. Authentication is handled via JWT dependency injection (`get_current_user`).

#### Dropshipping API pattern (different):

Dropshipping AI endpoints are scoped under stores and require ownership validation:

```python
router = APIRouter(prefix="/stores", tags=["ai-features"])

@router.post("/{store_id}/products/{product_id}/ai-description")
async def ai_description_endpoint(
    store_id: uuid.UUID,
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await _validate_store_ownership(db, store_id, current_user)
    return await generate_product_description(db, str(store_id), str(product_id))
```

### 1.4 Complete API Reference

#### Universal endpoint (all 10 services)

| Method | Path | Auth | Request Body | Description |
|--------|------|------|-------------|-------------|
| `GET` | `/api/v1/ai/suggestions` | JWT | None | Domain-specific AI suggestions |

#### Dropshipping (port 8000)

| Method | Path | Auth | Request Body | Description |
|--------|------|------|-------------|-------------|
| `POST` | `/api/v1/stores/{store_id}/products/{product_id}/ai-description` | JWT + store owner | None | Generate AI product descriptions |
| `POST` | `/api/v1/stores/{store_id}/products/{product_id}/ai-pricing` | JWT + store owner | None | AI pricing recommendations |

Note: Dropshipping does not have a `GET /ai/suggestions` endpoint; its AI features are product-scoped.

#### TrendScout (port 8101)

| Method | Path | Auth | Request Body | Description |
|--------|------|------|-------------|-------------|
| `POST` | `/api/v1/ai/predict-trends` | JWT | None | Predict upcoming product trends |

#### ContentForge (port 8102)

| Method | Path | Auth | Request Body | Description |
|--------|------|------|-------------|-------------|
| `POST` | `/api/v1/ai/enhance-content` | JWT | `{ "content_id": "uuid-string" }` | Enhance a content piece with AI |

#### RankPilot (port 8103)

| Method | Path | Auth | Request Body | Description |
|--------|------|------|-------------|-------------|
| `POST` | `/api/v1/ai/seo-suggest` | JWT | None | Detailed SEO recommendations |

#### FlowSend (port 8104)

| Method | Path | Auth | Request Body | Description |
|--------|------|------|-------------|-------------|
| `POST` | `/api/v1/ai/generate-copy` | JWT | `{ "campaign_name": "str", "audience": "str" }` | Generate email/SMS campaign copy |
| `POST` | `/api/v1/ai/segment-contacts` | JWT | None | AI customer segmentation |

#### SpyDrop (port 8105)

| Method | Path | Auth | Request Body | Description |
|--------|------|------|-------------|-------------|
| `POST` | `/api/v1/ai/competitor-analysis` | JWT | `{ "competitor_id": "uuid-string" }` | Detailed competitor insights |

#### PostPilot (port 8106)

| Method | Path | Auth | Request Body | Description |
|--------|------|------|-------------|-------------|
| `POST` | `/api/v1/ai/generate-caption` | JWT | `{ "topic": "str", "platform": "str", "tone": "str" }` | Social media caption generation |

#### AdScale (port 8107)

| Method | Path | Auth | Request Body | Description |
|--------|------|------|-------------|-------------|
| `POST` | `/api/v1/ai/optimize-ad` | JWT | `{ "ad_id": "uuid-string" }` | Optimize ad copy and targeting |

#### ShopChat (port 8108)

| Method | Path | Auth | Request Body | Description |
|--------|------|------|-------------|-------------|
| `POST` | `/api/v1/ai/train-assistant` | JWT | `{ "knowledge_base": "str" }` | Enhance chatbot knowledge base |

#### SourcePilot (port 8109)

| Method | Path | Auth | Request Body | Description |
|--------|------|------|-------------|-------------|
| `POST` | `/api/v1/ai/score-supplier` | JWT | `{ "supplier_url": "str" }` | AI supplier reliability scoring |

### 1.5 Response Shapes by Service

Every response includes the common fields `generated_at`, `provider`, and `cost_usd`. The domain-specific payload varies:

| Service | Primary Key | Payload Type |
|---------|-------------|-------------|
| Dropshipping (description) | `description` | Object with `title_variants`, `short_description`, `long_description`, `bullet_points`, `seo_title`, `meta_description`, `suggested_tags` |
| Dropshipping (pricing) | `pricing` | Object with `recommended_price_range`, `pricing_strategy`, `psychological_tips`, `bundle_suggestions`, `discount_strategy`, `margin_analysis` |
| TrendScout (predictions) | `predictions` | Array of `{ name, description, confidence, estimated_market_size, recommended_action }` |
| TrendScout (suggestions) | `suggestions` | Array of `{ title, description, priority }` |
| ContentForge (enhance) | `enhancements` | Array of `{ category, current_issue, suggestion, impact }` |
| RankPilot (seo) | `recommendations` | Array of `{ category, action, expected_impact, difficulty }` |
| FlowSend (copy) | `copy_variants` | Array of `{ subject_line, preview_text, body_html, sms_version }` |
| FlowSend (segments) | `segments` | Array of `{ name, description, criteria, campaign_type, expected_engagement }` |
| SpyDrop (analysis) | `analysis` | Array of `{ category, finding, opportunity, urgency }` |
| PostPilot (captions) | `captions` | Array of `{ caption, hashtags, call_to_action, best_posting_time }` |
| AdScale (optimize) | `optimizations` | Array of `{ element, current_assessment, improvement, expected_lift }` |
| ShopChat (train) | `training_data` | Object with `faqs[]`, `templates[]`, `recommendations[]`, `escalation_rules[]` |
| SourcePilot (score) | `scoring` + `overall_score` | Object with dimension scores (0-100) + integer overall score + `recommendation` string |

### 1.6 LLM Parameters by Endpoint

| Service / Endpoint | `task_type` | `max_tokens` | `temperature` |
|---|---|---|---|
| Dropshipping / product-description | `product_description` | 2000 | 0.7 |
| Dropshipping / price-optimization | `pricing_suggestion` | 1500 | 0.5 |
| TrendScout / predict-trends | `trend_prediction` | 1500 | 0.7 |
| ContentForge / enhance-content | `content_enhancement` | 1500 | 0.7 |
| RankPilot / seo-suggest | `seo_recommendations` | 1500 | 0.7 |
| FlowSend / generate-copy | `campaign_copy` | 2000 | 0.8 |
| FlowSend / segment-contacts | `contact_segmentation` | 1500 | 0.7 |
| SpyDrop / competitor-analysis | `competitor_analysis` | 2000 | 0.7 |
| PostPilot / generate-caption | `caption_generation` | 1500 | 0.8 |
| AdScale / optimize-ad | `ad_optimization` | 2000 | 0.7 |
| ShopChat / train-assistant | `chatbot_training` | 2000 | 0.5 |
| SourcePilot / score-supplier | `supplier_scoring` | 1500 | 0.5 |
| All services / suggestions | varies by service | 1000 | 0.7 |

Note: Lower temperatures (0.5) are used for analytical/scoring tasks (pricing, chatbot training, supplier scoring). Higher temperatures (0.8) are used for creative tasks (campaign copy, social captions).

### 1.7 Error Handling Strategy

1. **LLM Gateway unreachable:** `call_llm()` raises `httpx.HTTPStatusError` or `httpx.ConnectError`. These propagate as HTTP 500 to the caller (unhandled intentionally -- gateway availability is an infrastructure concern).
2. **Malformed JSON from LLM:** Each service function wraps `json.loads(result["content"])` in a try/except. On failure, the raw content string is returned inside a fallback structure (e.g., `{"suggestions": ["raw string"]}`). The endpoint still returns 200.
3. **Missing `content` key:** The `KeyError` is caught by the same except block. Fallback uses `result.get("content", "No ... available.")`.
4. **Authentication failure:** FastAPI `Depends(get_current_user)` returns 401 before the service layer is reached.
5. **Store ownership (Dropshipping only):** `_validate_store_ownership()` raises HTTP 404 if the store does not exist or is not owned by the current user.

### 1.8 File Inventory

```
packages/py-core/ecomm_core/llm_client.py           # call_llm() + call_llm_mock()

dropshipping/backend/app/services/ai_suggestions_service.py
dropshipping/backend/app/api/ai_features.py
dropshipping/backend/tests/test_ai_features.py

trendscout/backend/app/services/ai_suggestions_service.py
trendscout/backend/app/api/suggestions.py
trendscout/backend/tests/test_ai_suggestions.py

contentforge/backend/app/services/ai_suggestions_service.py
contentforge/backend/app/api/suggestions.py
contentforge/backend/tests/test_ai_suggestions.py

rankpilot/backend/app/services/ai_suggestions_service.py
rankpilot/backend/app/api/suggestions.py
rankpilot/backend/tests/test_ai_suggestions.py

flowsend/backend/app/services/ai_suggestions_service.py
flowsend/backend/app/api/suggestions.py
flowsend/backend/tests/test_ai_suggestions.py

spydrop/backend/app/services/ai_suggestions_service.py
spydrop/backend/app/api/suggestions.py
spydrop/backend/tests/test_ai_suggestions.py

postpilot/backend/app/services/ai_suggestions_service.py
postpilot/backend/app/api/suggestions.py
postpilot/backend/tests/test_ai_suggestions.py

adscale/backend/app/services/ai_suggestions_service.py
adscale/backend/app/api/suggestions.py
adscale/backend/tests/test_ai_suggestions.py

shopchat/backend/app/services/ai_suggestions_service.py
shopchat/backend/app/api/suggestions.py
shopchat/backend/tests/test_ai_suggestions.py

sourcepilot/backend/app/services/ai_suggestions_service.py
sourcepilot/backend/app/api/suggestions.py
sourcepilot/backend/tests/test_ai_suggestions.py
```

---

## 2. Project Manager Documentation

### 2.1 Feature Scope

Feature 5 adds AI-powered capabilities to every service in the platform, giving merchants intelligent automation across their entire e-commerce workflow. AI features span product copywriting, pricing strategy, trend forecasting, SEO optimization, email marketing, competitor analysis, social media content, ad optimization, chatbot training, and supplier evaluation.

### 2.2 Service-by-Service Capability Map

| Service | AI Capability | Business Value |
|---------|--------------|----------------|
| **Dropshipping** | Product description generation, price optimization | Faster product listings, data-driven pricing |
| **TrendScout** | Trend prediction, research suggestions | Early identification of winning products |
| **ContentForge** | Content enhancement, strategy suggestions | Higher-quality product content, better SEO |
| **RankPilot** | SEO recommendations, optimization suggestions | Improved organic search rankings |
| **FlowSend** | Campaign copy generation, customer segmentation | Higher email/SMS conversion rates |
| **SpyDrop** | Competitor analysis, competitive intelligence | Strategic market positioning |
| **PostPilot** | Caption generation, social strategy | Faster social media content creation |
| **AdScale** | Ad copy optimization, campaign suggestions | Better ROAS on paid campaigns |
| **ShopChat** | Knowledge base enhancement, chatbot improvement | Smarter customer support chatbot |
| **SourcePilot** | Supplier scoring, sourcing suggestions | Data-driven supplier selection |

### 2.3 Delivery Milestones

| Milestone | Deliverables | Status |
|-----------|-------------|--------|
| M1: Infrastructure | LLM Gateway integration, `call_llm()` shared client | Complete |
| M2: Common pattern | `get_ai_suggestions()` endpoint across all 10 services | Complete |
| M3: Service-specific endpoints | 12 specialized AI endpoints (see API reference) | Complete |
| M4: Test coverage | 54 automated tests across 10 services | Complete |
| M5: Dashboard integration | AI features accessible from each service's dashboard UI | Pending |
| M6: Usage tracking & billing | Per-customer AI usage metering via LLM Gateway | Pending |

### 2.4 Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| LLM Gateway (`llm-gateway/`) | Infrastructure | Deployed (port 8200) |
| `ecomm_core` package (`packages/py-core/`) | Shared library | Published with `llm_client` module |
| LLM provider API keys (Claude, OpenAI, Gemini) | External | Configured in gateway |
| PostgreSQL database | Infrastructure | Deployed (shared across services) |
| JWT authentication | Platform feature | Deployed across all services |

### 2.5 Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| LLM provider outage | AI features unavailable | Gateway supports multiple providers with fallback routing |
| Malformed LLM output | Broken UI | All services have JSON fallback parsing; endpoints always return 200 |
| High LLM costs | Budget overrun | Per-customer cost tracking via gateway; `cost_usd` in every response |
| Slow LLM responses | Poor UX | 60-second timeout configured; caching layer in gateway |
| Token limit exceeded | Truncated output | `max_tokens` tuned per endpoint (1000-2000 based on task complexity) |

### 2.6 Metrics to Track

- **AI call volume:** Requests per service per day (available via gateway logs)
- **Cost per call:** Average `cost_usd` by `task_type`
- **Cache hit rate:** Percentage of requests served from gateway cache
- **Latency:** P50/P95 `latency_ms` by provider and task type
- **Error rate:** Malformed JSON fallback percentage per service
- **Feature adoption:** Percentage of active merchants using AI features per service

---

## 3. QA Engineer Documentation

### 3.1 Test Coverage Summary

**Total AI tests: 54** across 10 services.

| Service | Test File | Test Count |
|---------|-----------|-----------|
| TrendScout | `trendscout/backend/tests/test_ai_suggestions.py` | 6 |
| ContentForge | `contentforge/backend/tests/test_ai_suggestions.py` | 5 |
| RankPilot | `rankpilot/backend/tests/test_ai_suggestions.py` | 5 |
| FlowSend | `flowsend/backend/tests/test_ai_suggestions.py` | 7 |
| SpyDrop | `spydrop/backend/tests/test_ai_suggestions.py` | 5 |
| PostPilot | `postpilot/backend/tests/test_ai_suggestions.py` | 5 |
| AdScale | `adscale/backend/tests/test_ai_suggestions.py` | 5 |
| ShopChat | `shopchat/backend/tests/test_ai_suggestions.py` | 5 |
| SourcePilot | `sourcepilot/backend/tests/test_ai_suggestions.py` | 5 |
| Dropshipping | `dropshipping/backend/tests/test_ai_features.py` | 6 |

### 3.2 Test Categories (per service)

Every service's test suite covers these categories:

| Category | What It Validates | Expected Behavior |
|----------|-------------------|-------------------|
| **Auth: unauthenticated GET** | `GET /api/v1/ai/suggestions` without JWT | Returns 401 |
| **Auth: unauthenticated POST** | Service-specific POST endpoint without JWT | Returns 401 |
| **Success: suggestions** | `GET /api/v1/ai/suggestions` with valid JWT + mocked LLM | Returns 200 with domain-specific suggestions array |
| **Success: domain action** | Service-specific POST with valid JWT + mocked LLM | Returns 200 with expected response shape |
| **Malformed JSON** | LLM returns non-JSON string | Returns 200 with fallback wrapper |

**Dropshipping additional test:** Store ownership validation returns 404 for non-existent stores.

**FlowSend additional tests:** Has 7 tests because it has 3 endpoints (suggestions, generate-copy, segment-contacts), each with its own auth + success test.

### 3.3 Mocking Strategy

All tests mock `call_llm()` at the service module level using `unittest.mock.patch`:

```python
with patch(
    "app.services.ai_suggestions_service.call_llm",
    new_callable=AsyncMock,
    return_value=mock_response,
):
    resp = await client.get("/api/v1/ai/suggestions", headers=headers)
```

The mock response factory used in every test file:

```python
def _mock_llm_response(content_dict: dict) -> dict:
    return {
        "content": json.dumps(content_dict),
        "provider": "mock",
        "model": "mock-v1",
        "input_tokens": 50,
        "output_tokens": 100,
        "cost_usd": 0.001,
        "cached": False,
        "latency_ms": 10,
    }
```

For malformed JSON tests, the mock returns `{"content": "Not valid JSON", ...}` (a plain string instead of a JSON-serialized object).

### 3.4 Acceptance Criteria

#### AC-1: Authentication enforcement
- [ ] Every AI endpoint returns 401 when called without a JWT token.
- [ ] Every AI endpoint returns 401 when called with an expired or invalid JWT.

#### AC-2: Successful AI generation
- [ ] `GET /api/v1/ai/suggestions` returns 200 with a `suggestions` array for all 9 SaaS services.
- [ ] Each service-specific POST endpoint returns 200 with the correct domain payload.
- [ ] Every response includes `generated_at` (ISO 8601 format), `provider` (string), and `cost_usd` (number).

#### AC-3: Graceful degradation
- [ ] When the LLM returns non-JSON content, the endpoint still returns 200 (not 500).
- [ ] The fallback response wraps the raw content in the expected key (e.g., `{"suggestions": ["raw text"]}`).

#### AC-4: Dropshipping store ownership
- [ ] `POST /stores/{store_id}/products/{product_id}/ai-description` returns 404 when `store_id` does not belong to the authenticated user.
- [ ] `POST /stores/{store_id}/products/{product_id}/ai-pricing` returns 404 when `store_id` does not belong to the authenticated user.

#### AC-5: Request validation
- [ ] FlowSend `POST /ai/generate-copy` requires `campaign_name` and `audience` in request body; returns 422 without them.
- [ ] PostPilot `POST /ai/generate-caption` requires `topic`, `platform`, and `tone`; returns 422 without them.
- [ ] SpyDrop `POST /ai/competitor-analysis` requires `competitor_id`; returns 422 without it.
- [ ] ContentForge `POST /ai/enhance-content` requires `content_id`; returns 422 without it.
- [ ] AdScale `POST /ai/optimize-ad` requires `ad_id`; returns 422 without it.
- [ ] ShopChat `POST /ai/train-assistant` requires `knowledge_base`; returns 422 without it.
- [ ] SourcePilot `POST /ai/score-supplier` requires `supplier_url`; returns 422 without it.

### 3.5 Edge Cases to Verify

| Edge Case | Expected Behavior |
|-----------|-------------------|
| LLM returns empty string for `content` | Fallback message like "No suggestions available." |
| LLM returns valid JSON but missing expected key | `parsed.get("suggestions", [])` returns empty list; 200 response |
| LLM returns very large response (exceeds max_tokens) | Truncated but still valid; JSON may be cut off and trigger fallback |
| Concurrent AI requests from same user | Each request gets independent LLM call; no session conflicts |
| `call_llm()` raises `httpx.ConnectError` | Unhandled; returns 500 (expected -- infrastructure issue) |
| `call_llm()` raises `httpx.HTTPStatusError` (e.g., 429) | Unhandled; returns 500 (expected -- rate limit) |
| ShopChat `knowledge_base` exceeds 3000 chars | Truncated to 3000 chars before sending to LLM (by service code) |
| SourcePilot `supplier_url` is not a valid URL | LLM receives it as-is; scoring may be unreliable but no crash |

### 3.6 Running Tests

```bash
# Single service
cd trendscout/backend && python -m pytest tests/test_ai_suggestions.py -v

# All AI tests across the platform
for svc in trendscout contentforge rankpilot flowsend spydrop postpilot adscale shopchat sourcepilot; do
    (cd $svc/backend && python -m pytest tests/test_ai_suggestions.py -v)
done
(cd dropshipping/backend && python -m pytest tests/test_ai_features.py -v)
```

---

## 4. End User Documentation

### 4.1 Overview

Every service in the platform includes AI-powered features that help you work smarter and faster. The AI analyzes your data and provides actionable recommendations, generates content, and automates analysis tasks -- all accessible from your service dashboards.

### 4.2 Feature Guide by Service

#### Dropshipping: AI Product Descriptions and Pricing

**What it does:** Generates compelling, SEO-optimized product descriptions and recommends optimal pricing strategies for your products.

**How to use it:**
1. Navigate to a product in your store dashboard.
2. Click "Generate AI Description" to create product copy including title variations, short and long descriptions, bullet points, and SEO meta tags.
3. Click "AI Pricing" to receive pricing strategy recommendations including price range suggestions, psychological pricing tips, and bundle ideas.

**What you get:**
- 3 title variations to choose from
- Short description (50-100 words) and long description (200-300 words, HTML-formatted)
- 5-7 feature bullet points
- SEO title and meta description
- 5-8 suggested tags
- Recommended price range with strategy analysis

#### TrendScout: AI Trend Predictions

**What it does:** Predicts upcoming product trends before they go mainstream, helping you find winning products early.

**How to use it:**
1. Open your TrendScout dashboard.
2. Click "AI Suggestions" for general product research advice.
3. Click "Predict Trends" for detailed trend forecasts.

**What you get:**
- Top 5 predicted trends with confidence scores (0-100)
- Estimated market size per trend
- Recommended actions for each trend
- General research strategy suggestions prioritized by importance

#### ContentForge: AI Content Enhancement

**What it does:** Reviews your product content for SEO, readability, and engagement, then provides specific improvements.

**How to use it:**
1. Open your ContentForge dashboard.
2. Click "AI Suggestions" for general content strategy advice.
3. Select a specific content piece and click "Enhance with AI" for targeted improvements.

**What you get:**
- Improvement suggestions organized by category (SEO, readability, engagement, CTA)
- Each suggestion includes the current issue, the recommended fix, and its expected impact

#### RankPilot: AI SEO Recommendations

**What it does:** Analyzes your store's SEO performance and provides prioritized recommendations to improve search rankings.

**How to use it:**
1. Open your RankPilot dashboard.
2. Click "AI Suggestions" for high-level SEO strategy advice.
3. Click "SEO Analysis" for detailed, prioritized SEO action items.

**What you get:**
- 5 prioritized SEO recommendations covering keywords, technical SEO, content, backlinks, and local SEO
- Each recommendation includes category, specific action, expected impact, and difficulty level

#### FlowSend: AI Campaign Copy and Segmentation

**What it does:** Generates email and SMS campaign copy and recommends intelligent customer segments for targeted marketing.

**How to use it:**
1. Open your FlowSend dashboard.
2. Click "AI Suggestions" for general campaign improvement advice.
3. To generate campaign copy: enter your campaign name and target audience, then click "Generate Copy." You receive 3 variants, each with email subject line, preview text, body content, and an SMS version.
4. Click "AI Segments" to get recommended customer segments with behavioral criteria.

**What you get:**
- 3 campaign copy variants per generation, each with email and SMS versions
- 5 intelligent customer segment recommendations with targeting criteria
- Campaign strategy suggestions prioritized by impact

#### SpyDrop: AI Competitor Analysis

**What it does:** Analyzes competitor stores to provide actionable intelligence on their strategy, pricing, and positioning.

**How to use it:**
1. Open your SpyDrop dashboard.
2. Click "AI Suggestions" for general competitive strategy advice.
3. Select a tracked competitor and click "AI Analysis" for a detailed competitive breakdown.

**What you get:**
- Analysis across pricing, product catalog, marketing channels, SEO, social media, and customer experience
- Counter-strategies for each area
- Urgency ratings to help you prioritize

#### PostPilot: AI Social Media Captions

**What it does:** Creates platform-optimized social media captions with hashtags and posting time recommendations.

**How to use it:**
1. Open your PostPilot dashboard.
2. Click "AI Suggestions" for social media strategy advice.
3. To generate captions: enter your topic, select the platform (Instagram, TikTok, Facebook, etc.), choose a tone (professional, casual, humorous), and click "Generate Captions."

**What you get:**
- 3 caption variants per generation, each optimized for your chosen platform
- 5-10 relevant hashtags per caption
- Call-to-action text
- Best posting time recommendation

#### AdScale: AI Ad Optimization

**What it does:** Optimizes your ad copy, headlines, and targeting with data-driven recommendations to improve ROAS.

**How to use it:**
1. Open your AdScale dashboard.
2. Click "AI Suggestions" for general ad strategy advice.
3. Select an ad and click "Optimize with AI" for specific copy and targeting improvements.

**What you get:**
- Optimization suggestions for headlines (3 variations), body copy, CTA text, and audience targeting
- Each suggestion includes a current assessment, the improvement, and an expected performance lift percentage

#### ShopChat: AI Chatbot Training

**What it does:** Processes your product information, policies, and FAQs to generate structured training data that makes your chatbot smarter.

**How to use it:**
1. Open your ShopChat dashboard.
2. Click "AI Suggestions" for chatbot improvement recommendations.
3. Paste your product information, store policies, or FAQ content into the training box and click "Train with AI."

**What you get:**
- Structured FAQ pairs (question + answer)
- Response templates for common scenarios (shipping, returns, sizing)
- Product recommendation logic rules
- Escalation trigger rules for when to hand off to a human

#### SourcePilot: AI Supplier Scoring

**What it does:** Evaluates supplier reliability across multiple quality dimensions to help you choose trustworthy partners.

**How to use it:**
1. Open your SourcePilot dashboard.
2. Click "AI Suggestions" for sourcing strategy advice.
3. Enter a supplier URL and click "Score Supplier" for a detailed reliability assessment.

**What you get:**
- Scores (0-100) for: product quality, shipping speed, communication, pricing competitiveness, return policy, catalog breadth, and platform reputation
- An overall weighted score (0-100)
- A brief recommendation summary

### 4.3 Cost and Usage

Each AI feature call uses LLM tokens that count toward your account usage. The cost of each generation is shown in the response (typically fractions of a cent). You can view your total AI usage and costs in your account billing section.

### 4.4 Tips for Best Results

- **Be specific with inputs:** When generating campaign copy (FlowSend) or captions (PostPilot), detailed inputs produce better output. "Summer Sale for women's yoga pants targeting repeat customers" yields better copy than "Sale for all."
- **Use suggestions as starting points:** AI-generated content is a draft. Review and customize descriptions, captions, and copy to match your brand voice before publishing.
- **Run multiple generations:** If the first output is not ideal, run the AI again. Different generations produce varied results (temperature-based randomness is intentional).
- **Train your chatbot iteratively:** For ShopChat, start with your most common customer questions and gradually add more knowledge base content over time.
- **Score multiple suppliers:** For SourcePilot, compare scores across several suppliers to build a diversified sourcing strategy.
