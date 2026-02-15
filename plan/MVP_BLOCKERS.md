# MVP Blockers — Phase 4 & 5 API Keys & Credentials

**Status:** BLOCKING — Cannot proceed to production without these
**Created:** 2026-02-15
**Priority:** CRITICAL

---

## Overview

The platform codebase is **code-complete** — all services built, tested (2,221 backend tests + ~100 e2e tests), and documented. However, **Phases 4 and 5 of the MVP plan are blocked** because every automation service currently runs in **demo/mock mode**. To go live, real API credentials must be acquired and configured.

---

## Phase 4 Blockers: Real API Integration

### 1. AliExpress Dropshipping API

| Field | Value |
|-------|-------|
| **Service** | SourcePilot (A9) |
| **Purpose** | Product import, price sync, order placement |
| **Registration** | [AliExpress Open Platform](https://openservice.aliexpress.com/) |
| **Required Credentials** | `ALIEXPRESS_APP_KEY`, `ALIEXPRESS_APP_SECRET`, `ALIEXPRESS_ACCESS_TOKEN` |
| **Env File** | `sourcepilot/backend/.env` |
| **Cost** | Free (affiliate program) |
| **Approval Time** | 3-7 business days |
| **Notes** | Requires AliExpress business account. Apply for Dropshipping API access. Need to set up affiliate tracking ID for commissions. |

### 2. CJDropship API

| Field | Value |
|-------|-------|
| **Service** | SourcePilot (A9) |
| **Purpose** | Product import, inventory sync, order fulfillment |
| **Registration** | [CJDropshipping API](https://developers.cjdropshipping.com/) |
| **Required Credentials** | `CJDROPSHIP_API_KEY`, `CJDROPSHIP_EMAIL` |
| **Env File** | `sourcepilot/backend/.env` |
| **Cost** | Free |
| **Approval Time** | 1-3 business days |
| **Notes** | Register at cjdropshipping.com first, then apply for API access from developer portal. |

### 3. Apify (TikTok Scraping)

| Field | Value |
|-------|-------|
| **Service** | TrendScout (A1) |
| **Purpose** | Scrape TikTok trending products and hashtags |
| **Registration** | [Apify.com](https://apify.com/) |
| **Required Credentials** | `APIFY_TOKEN` |
| **Env File** | `trendscout/backend/.env` |
| **Cost** | Free tier: 10 Actor runs/day. Paid: $49/mo for 100 runs |
| **Approval Time** | Instant (self-service) |
| **Notes** | Use pre-built TikTok scraper Actor. Free tier sufficient for MVP beta. |

### 4. Reddit API (PRAW)

| Field | Value |
|-------|-------|
| **Service** | TrendScout (A1) |
| **Purpose** | Scan product subreddits for trending products |
| **Registration** | [Reddit App Preferences](https://www.reddit.com/prefs/apps) |
| **Required Credentials** | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` |
| **Env File** | `trendscout/backend/.env` |
| **Cost** | Free (100 requests/minute) |
| **Approval Time** | Instant (self-service) |
| **Notes** | Create a "script" type application. User agent format: `platform:appname:v1.0 (by /u/username)`. |

### 5. Google Trends (pytrends)

| Field | Value |
|-------|-------|
| **Service** | TrendScout (A1) |
| **Purpose** | Detect emerging product search trends |
| **Registration** | None required |
| **Required Credentials** | None (unofficial API) |
| **Env File** | N/A |
| **Cost** | Free |
| **Approval Time** | N/A |
| **Notes** | pytrends is an unofficial Google Trends wrapper. No API key needed. May need proxy rotation for high volume to avoid rate limits. Consider `PYTRENDS_PROXY` env var. |

### 6. SerpAPI (SEO Keywords)

| Field | Value |
|-------|-------|
| **Service** | RankPilot (A3) |
| **Purpose** | Keyword research, SERP analysis, ranking tracking |
| **Registration** | [SerpAPI.com](https://serpapi.com/) |
| **Required Credentials** | `SERPAPI_KEY` |
| **Env File** | `rankpilot/backend/.env` |
| **Cost** | Free: 100 searches/mo. Paid: $50/mo for 5,000 searches |
| **Approval Time** | Instant (self-service) |
| **Notes** | Free tier sufficient for MVP beta testing. Consider caching results aggressively to reduce API calls. |

### 7. SendGrid (Email Delivery)

| Field | Value |
|-------|-------|
| **Service** | FlowSend (A4) + Dropshipping Core (transactional) |
| **Purpose** | Marketing email campaigns, transactional order emails |
| **Registration** | [SendGrid.com](https://sendgrid.com/) |
| **Required Credentials** | `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL` |
| **Env File** | `flowsend/backend/.env`, `dropshipping/backend/.env` |
| **Cost** | Free: 100 emails/day. Essentials: $19.95/mo for 50K emails |
| **Approval Time** | Instant signup, but **domain verification takes 24-48h** |
| **Notes** | Must verify sending domain (SPF, DKIM, DMARC records). Set up dedicated IP for high volume. Configure webhook URL for delivery tracking events. |

### 8. AWS SES (Alternative Email)

| Field | Value |
|-------|-------|
| **Service** | FlowSend (A4) |
| **Purpose** | Alternative email provider (cheaper at scale) |
| **Registration** | [AWS Console](https://console.aws.amazon.com/ses/) |
| **Required Credentials** | `SES_ACCESS_KEY_ID`, `SES_SECRET_ACCESS_KEY`, `SES_REGION` |
| **Env File** | `flowsend/backend/.env` |
| **Cost** | $0.10 per 1,000 emails (very cheap at scale) |
| **Approval Time** | Instant for sandbox. **Production access request takes 24-48h** |
| **Notes** | Starts in sandbox mode (can only send to verified emails). Must request production access and verify domain. |

### 9. Twilio (SMS)

| Field | Value |
|-------|-------|
| **Service** | FlowSend (A4) |
| **Purpose** | SMS marketing campaigns and transactional messages |
| **Registration** | [Twilio.com](https://www.twilio.com/) |
| **Required Credentials** | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` |
| **Env File** | `flowsend/backend/.env` |
| **Cost** | $0.0079/SMS (US). Phone number: $1/mo |
| **Approval Time** | Instant. Phone number registration: 1-3 business days (A2P 10DLC) |
| **Notes** | Must register for A2P 10DLC campaign for business SMS. Trial account gives $15 credit. Need to buy a phone number. |

### 10. AWS SNS (Alternative SMS)

| Field | Value |
|-------|-------|
| **Service** | FlowSend (A4) |
| **Purpose** | Alternative SMS provider (bulk SMS) |
| **Registration** | [AWS Console](https://console.aws.amazon.com/sns/) |
| **Required Credentials** | `SNS_ACCESS_KEY_ID`, `SNS_SECRET_ACCESS_KEY`, `SNS_REGION` |
| **Env File** | `flowsend/backend/.env` |
| **Cost** | $0.00645/SMS (US) |
| **Approval Time** | Instant for sandbox. Production: request move out of SMS sandbox |
| **Notes** | Starts in sandbox (can only send to verified numbers). Must request production access. |

### 11. Anthropic Claude API (via LLM Gateway)

| Field | Value |
|-------|-------|
| **Service** | LLM Gateway (all AI features) |
| **Purpose** | AI content generation, product descriptions, marketing copy, SEO suggestions |
| **Registration** | [Anthropic Console](https://console.anthropic.com/) |
| **Required Credentials** | `ANTHROPIC_API_KEY` |
| **Env File** | `llm-gateway/backend/.env` |
| **Cost** | Claude Sonnet 4.5: $3/M input, $15/M output tokens |
| **Approval Time** | Instant (self-service) |
| **Notes** | This is the primary AI provider routed through the LLM Gateway. All 10 services use this for AI features. Single key manages all AI access. |

### 12. Meta APIs (Social Media)

| Field | Value |
|-------|-------|
| **Service** | PostPilot (A6) |
| **Purpose** | Auto-posting products to Instagram/Facebook |
| **Registration** | [Meta for Developers](https://developers.facebook.com/) |
| **Required Credentials** | `META_APP_ID`, `META_APP_SECRET`, `META_ACCESS_TOKEN` |
| **Env File** | `postpilot/backend/.env` |
| **Cost** | Free |
| **Approval Time** | App review: 5-10 business days |
| **Notes** | Requires Meta app review for `pages_manage_posts`, `instagram_content_publish` permissions. Start with test users during beta. |

### 13. Google Ads API

| Field | Value |
|-------|-------|
| **Service** | AdScale (A7) |
| **Purpose** | Automated ad campaign creation and management |
| **Registration** | [Google Ads API](https://developers.google.com/google-ads/api/docs/first-call/overview) |
| **Required Credentials** | `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`, `GOOGLE_ADS_REFRESH_TOKEN` |
| **Env File** | `adscale/backend/.env` |
| **Cost** | Free (API access). Ad spend is separate. |
| **Approval Time** | Developer token approval: 2-4 weeks |
| **Notes** | Longest lead time of all credentials. Apply for Basic Access developer token immediately. Requires Google Ads MCC account. |

### 14. Meta Ads API

| Field | Value |
|-------|-------|
| **Service** | AdScale (A7) |
| **Purpose** | Facebook/Instagram ad campaign automation |
| **Registration** | [Meta for Developers](https://developers.facebook.com/) |
| **Required Credentials** | `META_ADS_APP_ID`, `META_ADS_APP_SECRET`, `META_ADS_ACCESS_TOKEN` |
| **Env File** | `adscale/backend/.env` |
| **Cost** | Free (API access). Ad spend is separate. |
| **Approval Time** | App review: 5-10 business days |
| **Notes** | Requires `ads_management` and `ads_read` permissions. Can share same Meta app with PostPilot but needs additional permissions. |

### 15. Stripe (Production Keys)

| Field | Value |
|-------|-------|
| **Service** | All services (billing) + Dropshipping Core (checkout) |
| **Purpose** | Payment processing, subscriptions, platform billing |
| **Registration** | [Stripe Dashboard](https://dashboard.stripe.com/) |
| **Required Credentials** | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY` |
| **Env File** | All service `.env` files |
| **Cost** | 2.9% + $0.30 per transaction |
| **Approval Time** | Instant for test mode. Production: account verification 1-3 days |
| **Notes** | Currently using test mode keys. Need to create production price IDs for all subscription tiers across all 10 services. Must set up webhook endpoints for each service. |

---

## Phase 5 Blockers: Infrastructure & Integration

### 16. Sentry (Error Tracking)

| Field | Value |
|-------|-------|
| **Service** | All services |
| **Purpose** | Production error tracking and alerting |
| **Registration** | [Sentry.io](https://sentry.io/) |
| **Required Credentials** | `SENTRY_DSN` (one per service, or shared) |
| **Cost** | Free: 5K errors/mo. Team: $26/mo for 50K errors |
| **Approval Time** | Instant |
| **Notes** | Create one Sentry project per service or a single project with tags. Free tier is sufficient for MVP beta. |

### 17. Cloud Provider (K8s Hosting)

| Field | Value |
|-------|-------|
| **Purpose** | Host Kubernetes cluster for production deployment |
| **Options** | AWS EKS ($0.10/hr/cluster + EC2), GCP GKE (free control plane + nodes), DigitalOcean DOKS ($12/mo + nodes) |
| **Required** | Cluster access credentials, `kubectl` config, container registry access |
| **Notes** | User states K8s cluster already exists. Need: cluster endpoint, credentials, container registry URL, namespace permissions. |

### 18. Container Registry

| Field | Value |
|-------|-------|
| **Purpose** | Store Docker images for K8s deployment |
| **Options** | Docker Hub, AWS ECR, GCP Artifact Registry, GitHub Container Registry (GHCR) |
| **Required Credentials** | Registry URL, auth credentials |
| **Notes** | GHCR is free for public repos. ECR: $0.10/GB/mo. Choose based on where K8s cluster is hosted. |

### 19. S3-Compatible Object Storage

| Field | Value |
|-------|-------|
| **Purpose** | Product images, file uploads, backups |
| **Options** | AWS S3, Cloudflare R2 (no egress fees), MinIO (self-hosted) |
| **Required Credentials** | `S3_BUCKET_NAME`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_REGION`, `S3_ENDPOINT_URL` |
| **Cost** | S3: ~$0.023/GB/mo. R2: $0.015/GB/mo (no egress) |
| **Notes** | R2 recommended for cost savings (no egress fees for serving product images). |

### 20. Domain & DNS

| Field | Value |
|-------|-------|
| **Purpose** | Production domain, SSL certificates, custom domain routing |
| **Required** | Production domain name, DNS provider access (Cloudflare recommended) |
| **Credentials** | `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ZONE_ID` (if using Cloudflare DNS provider) |
| **Notes** | Need wildcard SSL for `*.platform.com` subdomains. Cloudflare provides free SSL + DNS + CDN. |

---

## Priority Order for Credential Acquisition

### Immediate (Week 1) — Longest Lead Times
1. **Google Ads Developer Token** — 2-4 weeks approval (APPLY FIRST)
2. **Meta App Review** — 5-10 business days
3. **AliExpress API Access** — 3-7 business days
4. **SendGrid Domain Verification** — 24-48 hours
5. **Stripe Production Verification** — 1-3 days

### Quick Setup (Days 1-2) — Self-Service
6. **Anthropic Claude API** — Instant
7. **Apify Token** — Instant
8. **Reddit API** — Instant
9. **SerpAPI** — Instant
10. **CJDropship API** — 1-3 days
11. **Twilio** — Instant (phone number: 1-3 days)
12. **Sentry** — Instant

### Infrastructure (Parallel)
13. **Container Registry** — Based on K8s provider
14. **S3/R2 Storage** — Quick setup
15. **Domain + Cloudflare** — DNS propagation: 24-48h

---

## Environment Variable Template

Create `.env.production` at the project root with all required credentials:

```bash
# ============================================
# PRODUCTION ENVIRONMENT VARIABLES
# ============================================

# --- Database ---
DATABASE_URL=postgresql+asyncpg://<user>:<pass>@<host>:5432/dropshipping

# --- Redis ---
REDIS_URL=redis://<host>:6379/0

# --- JWT (CHANGE THESE) ---
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-64>
ADMIN_SECRET_KEY=<generate-with-openssl-rand-hex-64>

# --- Stripe (Production) ---
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_live_...

# --- LLM Gateway ---
LLM_GATEWAY_SERVICE_KEY=<generate-strong-key>
ANTHROPIC_API_KEY=sk-ant-...

# --- SourcePilot ---
ALIEXPRESS_APP_KEY=...
ALIEXPRESS_APP_SECRET=...
ALIEXPRESS_ACCESS_TOKEN=...
CJDROPSHIP_API_KEY=...
CJDROPSHIP_EMAIL=...

# --- TrendScout ---
APIFY_TOKEN=apify_api_...
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=dropshipping-platform:v1.0 (by /u/<username>)

# --- RankPilot ---
SERPAPI_KEY=...

# --- FlowSend ---
SENDGRID_API_KEY=SG....
SENDGRID_FROM_EMAIL=noreply@<your-domain>
SES_ACCESS_KEY_ID=...
SES_SECRET_ACCESS_KEY=...
SES_REGION=us-east-1
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
SNS_ACCESS_KEY_ID=...
SNS_SECRET_ACCESS_KEY=...
SNS_REGION=us-east-1

# --- PostPilot ---
META_APP_ID=...
META_APP_SECRET=...
META_ACCESS_TOKEN=...

# --- AdScale ---
GOOGLE_ADS_DEVELOPER_TOKEN=...
GOOGLE_ADS_CLIENT_ID=...
GOOGLE_ADS_CLIENT_SECRET=...
GOOGLE_ADS_REFRESH_TOKEN=...
META_ADS_APP_ID=...
META_ADS_APP_SECRET=...
META_ADS_ACCESS_TOKEN=...

# --- Monitoring ---
SENTRY_DSN=https://<key>@<org>.ingest.sentry.io/<project>

# --- Infrastructure ---
S3_BUCKET_NAME=...
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
S3_REGION=us-east-1
S3_ENDPOINT_URL=...  # For R2: https://<account>.r2.cloudflarestorage.com

# --- DNS/Domain ---
CLOUDFLARE_API_TOKEN=...
CLOUDFLARE_ZONE_ID=...
```

---

## Cost Estimate (MVP Beta — 20 Users)

| Service | Tier | Monthly Cost |
|---------|------|-------------|
| Anthropic Claude | Pay-as-you-go | ~$50-100 |
| SendGrid | Free/Essentials | $0-20 |
| Twilio | Pay-as-you-go | ~$10-20 |
| SerpAPI | Free | $0 |
| Apify | Free | $0 |
| Reddit/Google Trends | Free | $0 |
| Sentry | Free | $0 |
| Stripe | Transaction fees | ~2.9% + $0.30/txn |
| S3/R2 Storage | Pay-as-you-go | ~$5-10 |
| K8s Cluster | Provider-dependent | $50-200 |
| **Total** | | **~$115-350/mo** |

---

## Action Items

- [ ] Apply for Google Ads Developer Token immediately (longest lead time)
- [ ] Submit Meta App for review (PostPilot + AdScale)
- [ ] Register AliExpress Dropshipping API access
- [ ] Set up SendGrid account and verify sending domain
- [ ] Create Anthropic API key and load credits
- [ ] Set up Apify, Reddit, SerpAPI accounts (instant)
- [ ] Configure Twilio with A2P 10DLC registration
- [ ] Set up Sentry project(s)
- [ ] Activate Stripe production mode and create price IDs
- [ ] Provision S3/R2 bucket for product images
- [ ] Configure production domain and SSL

---

*Once all credentials are acquired, Phase 4 implementation is estimated at 2 weeks — primarily replacing mock data calls with real API calls using the existing provider abstraction pattern.*
