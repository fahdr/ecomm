# LLM Gateway - End User Guide

> Part of [LLM Gateway](README.md) documentation

Understanding how the LLM Gateway powers AI features across all ecomm services.

## What is the LLM Gateway?

The LLM Gateway is a **backend microservice** that you never interact with directly. It works behind the scenes to power all the AI features you use across TrendScout, ContentForge, RankPilot, FlowSend, SpyDrop, PostPilot, AdScale, and ShopChat.

Think of it as the "AI brain" that all 8 services talk to when they need to:
- Generate product descriptions
- Analyze market trends
- Write email campaigns
- Create social media posts
- Answer customer support questions
- Optimize ad copy
- Suggest SEO keywords
- ...and much more

## How It Works (Simple View)

```
You use ContentForge → "Generate blog post about wireless headphones"
                ↓
ContentForge sends request → LLM Gateway
                ↓
LLM Gateway routes to → Claude (or OpenAI, or Gemini)
                ↓
AI generates content → "Wireless headphones have revolutionized..."
                ↓
ContentForge shows you ← the blog post
```

## Why You Should Care

### 1. Consistent AI Quality

All services use the same high-quality AI models (Claude Sonnet 4, GPT-4o, etc.). You don't get different quality levels depending on which service you're using.

### 2. Cost Efficiency

The gateway caches identical AI requests. If you generate the same product description twice, the second one is instant and free. This keeps your costs down.

### 3. Premium AI Models (For Premium Users)

If you're on a premium plan, the admin can configure your account to use the most advanced AI models (like Claude Opus 4) across all services — automatically.

### 4. Reliable AI Access

If one AI provider has an outage, the gateway can route your requests to a backup provider (future feature). You don't experience downtime.

## What You See (Per Service)

### TrendScout

When you click **"Analyze Product Trends"**:
- TrendScout sends your request to the gateway
- The gateway calls the configured AI (e.g., Claude)
- You see insights like: "This product is trending up 15% this month..."

### ContentForge

When you click **"Generate Blog Post"**:
- ContentForge sends your prompt to the gateway
- The gateway generates content using your preferred AI model
- You see a full blog post in seconds

### RankPilot

When you click **"Generate Meta Description"**:
- RankPilot sends your page content to the gateway
- The gateway optimizes for SEO using AI
- You get SEO-friendly meta tags

### FlowSend

When you click **"Generate Email Subject Lines"**:
- FlowSend sends your campaign context to the gateway
- The gateway generates 5 subject line options
- You pick your favorite and send

### SpyDrop

When you click **"Analyze Supplier"**:
- SpyDrop sends supplier data to the gateway
- The gateway evaluates reliability and pricing
- You see a supplier score and recommendation

### PostPilot

When you click **"Create Social Post"**:
- PostPilot sends your product/brand info to the gateway
- The gateway writes engaging social media copy
- You schedule it to your accounts

### AdScale

When you click **"Generate Ad Copy"**:
- AdScale sends your campaign goals to the gateway
- The gateway creates conversion-optimized ad text
- You launch your campaign

### ShopChat

When a customer asks: **"Do you have this in blue?"**:
- ShopChat sends the question to the gateway
- The gateway generates a helpful, on-brand response
- Your customer gets an instant answer

## Admin Configuration (What Your Admin Does)

Your platform admin uses the **Super Admin Dashboard** to:

1. **Add AI Providers**
   - Configure API keys for Anthropic, OpenAI, Google, etc.
   - Set which models are available (GPT-4o, Claude Opus, etc.)

2. **Set Default Model**
   - Choose which AI model is used by default for all users
   - Balance cost vs. quality

3. **Create Premium Overrides**
   - Assign premium customers to use advanced models
   - Example: Free users get Haiku, Pro users get Opus

4. **Monitor Costs**
   - See which services/customers use the most AI
   - Set budgets and alerts

5. **Check Performance**
   - View cache hit rates (how often responses are instant)
   - Monitor AI provider uptime

## Common Questions

### Q: Can I choose which AI model to use?

Not directly. Your plan determines which AI model you get. Premium plans use more advanced models. Your admin configures this in the gateway.

### Q: Why do some AI requests feel instant?

The gateway caches responses. If you ask the same question twice (or someone else already asked it), you get the cached answer in milliseconds instead of seconds.

### Q: Does the gateway see my data?

Yes, but only temporarily. The gateway logs requests for cost tracking and debugging, but it doesn't store your prompts or AI responses long-term. Usage logs are retained for 90 days for billing purposes.

### Q: What happens if the AI is down?

You'll see an error message in the service you're using (e.g., "AI generation failed, please try again"). The gateway logs these errors so the admin can switch to a backup provider.

### Q: Can I see my AI usage?

Not directly in the gateway. Your service (e.g., ContentForge) may show you your usage. The admin can see platform-wide usage in the Super Admin Dashboard.

## Privacy & Data

### What the Gateway Logs

- **Your user ID** (to track costs per customer)
- **The service you used** (TrendScout, ContentForge, etc.)
- **Token counts** (how much AI was used)
- **Cost in USD** (for billing)
- **First 200 characters of your prompt** (for debugging errors)

### What the Gateway Does NOT Store

- Full prompts (only 200-char preview)
- Full AI responses (cached temporarily in Redis for 1 hour)
- Your personal data (name, email, payment info)

### Security

- All API calls use HTTPS encryption
- AI provider API keys are encrypted at rest
- Only services with valid keys can access the gateway
- Admins cannot see individual user prompts (only aggregated stats)

## Support

If you experience issues with AI-powered features:

1. **Contact support** for your specific service (TrendScout, ContentForge, etc.)
2. Support will check the gateway logs to diagnose the issue
3. Issues are usually related to:
   - Provider outages (Claude, OpenAI down)
   - Rate limits hit (too many requests)
   - Invalid prompts (empty or too long)

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
