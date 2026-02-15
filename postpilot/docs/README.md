# PostPilot Documentation

> Social Media Automation service for managing Instagram, Facebook, and TikTok accounts

**PostPilot** is a standalone SaaS product that automates social media workflows for e-commerce businesses. It supports multi-platform posting, AI-powered caption generation, content queue management, post scheduling with calendar views, and engagement analytics.

---

## Quick Links

| Document | Description |
|----------|-------------|
| [Setup Guide](SETUP.md) | Local development, prerequisites, environment setup |
| [Architecture](ARCHITECTURE.md) | Tech stack, project structure, database models, design decisions |
| [API Reference](API_REFERENCE.md) | Complete API documentation with endpoints and response formats |
| [Testing](TESTING.md) | Test infrastructure, running tests, writing new tests |
| [QA Engineer Guide](QA_ENGINEER.md) | Acceptance criteria, verification checklists, edge cases |
| [Project Manager Guide](PROJECT_MANAGER.md) | Feature scope, progress tracking, roadmap |
| [End User Guide](END_USER.md) | User workflows, feature guides, FAQs |
| [Implementation Steps](IMPLEMENTATION_STEPS.md) | Step-by-step implementation history |

---

## What Is PostPilot?

PostPilot enables users to:
- **Connect** social media accounts (Instagram, Facebook, TikTok) via OAuth
- **Create** posts with captions, media, and hashtags
- **Generate** AI-powered captions from product data
- **Schedule** posts for optimal publishing times
- **Track** engagement metrics (impressions, reach, likes, comments, shares, clicks)

---

## Key Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Backend tests | **157 passing** | 7 test files with full isolation |
| API endpoints | **27** | Auth, Accounts, Posts, Queue, Analytics, Billing, System |
| Dashboard pages | **9** | Home, Queue, Accounts, Posts, Billing, API Keys, Settings, Login, Register |
| Database models | **7** | User, SocialAccount, Post, PostMetrics, ContentQueue, Subscription, ApiKey |
| Service functions | **18** | Across 5 service modules |

---

## Service Ports

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8106 | http://localhost:8106 |
| Dashboard | 3106 | http://localhost:3106 |
| Landing Page | 3206 | http://localhost:3206 |
| PostgreSQL | 5506 | localhost:5506 |
| Redis | 6406 | localhost:6406 |

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
