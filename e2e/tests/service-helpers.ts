/**
 * Shared helpers for SaaS service e2e tests.
 *
 * Provides utility functions for authentication, API calls, and data setup
 * across all 8 SaaS services (TrendScout, ContentForge, RankPilot, FlowSend,
 * SpyDrop, PostPilot, AdScale, ShopChat) and the Admin dashboard.
 *
 * **For Developers:**
 *   Import these helpers in service test files. Each helper accepts a service
 *   base URL parameter so the same functions work across all services.
 *
 * **For QA Engineers:**
 *   Helpers call service APIs directly at their respective ports (8101-8108, 8300).
 *   Each service's dashboard runs on ports 3101-3108 and 3300.
 *
 * **For Project Managers:**
 *   This file centralizes test infrastructure for all SaaS services,
 *   reducing duplication and ensuring consistent test patterns.
 *
 * **For End Users:**
 *   These utilities power automated tests that verify your dashboard workflows.
 */

import { type Page } from "@playwright/test";

/** Service API base URLs indexed by slug. */
export const SERVICE_APIS: Record<string, string> = {
  trendscout: "http://localhost:8101",
  contentforge: "http://localhost:8102",
  rankpilot: "http://localhost:8103",
  flowsend: "http://localhost:8104",
  spydrop: "http://localhost:8105",
  postpilot: "http://localhost:8106",
  adscale: "http://localhost:8107",
  shopchat: "http://localhost:8108",
  admin: "http://localhost:8300",
};

/** Default test password for all service users. */
export const TEST_PASSWORD = "testpass123";

/** Seed user credentials (shared across all services). */
export const SEED_EMAIL = "demo@example.com";
export const SEED_PASSWORD = "password123";

/** Admin seed credentials. */
export const ADMIN_EMAIL = "admin@ecomm.com";
export const ADMIN_PASSWORD = "admin123";

/**
 * Generate a unique email for test isolation.
 *
 * @returns A collision-free test email address.
 */
export function uniqueEmail(): string {
  return `test-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`;
}

/**
 * Wait until a JWT token is accepted by a service's auth endpoint.
 *
 * @param apiBase - Service API base URL.
 * @param token - JWT access token to verify.
 * @param maxWaitMs - Maximum wait time (default 3000ms).
 */
async function waitForServiceToken(
  apiBase: string,
  token: string,
  maxWaitMs = 3000
): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    const res = await fetch(`${apiBase}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) return;
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error(`Token not valid on ${apiBase} after waiting`);
}

/**
 * Register a user on a SaaS service via the API.
 *
 * @param serviceSlug - Service identifier (e.g. "trendscout").
 * @param email - Optional email; generated if not provided.
 * @returns Object with email, password, and JWT token.
 */
export async function registerServiceUser(
  serviceSlug: string,
  email?: string
) {
  const apiBase = SERVICE_APIS[serviceSlug];
  const userEmail = email || uniqueEmail();
  const res = await fetch(`${apiBase}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: userEmail, password: TEST_PASSWORD }),
  });
  if (!res.ok) throw new Error(`Register on ${serviceSlug} failed: ${res.status} ${await res.text()}`);
  const data = await res.json();
  await waitForServiceToken(apiBase, data.access_token);
  return { email: userEmail, password: TEST_PASSWORD, token: data.access_token };
}

/**
 * Login a user on a SaaS service via the API.
 *
 * @param serviceSlug - Service identifier.
 * @param email - User email.
 * @param password - User password.
 * @returns The JWT access token.
 */
export async function loginServiceUser(
  serviceSlug: string,
  email: string,
  password: string
): Promise<string> {
  const apiBase = SERVICE_APIS[serviceSlug];
  const res = await fetch(`${apiBase}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(`Login on ${serviceSlug} failed: ${res.status}`);
  const data = await res.json();
  return data.access_token;
}

/**
 * Login via a SaaS service dashboard UI.
 *
 * All SaaS dashboards share the same login page pattern:
 * - #email and #password input fields
 * - "Sign in" submit button
 * - Redirects to "/" on success
 *
 * @param page - Playwright page instance.
 * @param email - User email.
 * @param password - User password.
 */
export async function serviceLogin(
  page: Page,
  email: string,
  password: string
) {
  // Navigate to login first, then clear localStorage to avoid auto-redirect
  await page.goto("/login");
  await page.evaluate(() => localStorage.clear());
  // Reload to ensure the login page renders fresh (without cached auth)
  await page.goto("/login");
  // Wait for the login form to be fully rendered
  await page.waitForSelector("#email", { timeout: 10000 });
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.getByRole("button", { name: /sign in/i }).click();
  // Wait for navigation away from login page (dashboard content must load)
  await page.waitForFunction(
    () => !window.location.pathname.includes("/login"),
    { timeout: 15000 }
  );
  await page.waitForLoadState("networkidle");
}

/**
 * Generic POST helper with retry logic for a SaaS service.
 *
 * @param serviceSlug - Service identifier.
 * @param token - JWT access token.
 * @param path - API path (e.g. "/api/v1/research/runs").
 * @param body - Request body object.
 * @returns Parsed JSON response.
 */
export async function serviceApiPost(
  serviceSlug: string,
  token: string,
  path: string,
  body: unknown
) {
  const apiBase = SERVICE_APIS[serviceSlug];
  // Ensure trailing slash to avoid 307 redirects on FastAPI routers
  const normalizedPath = path.endsWith("/") ? path : `${path}/`;
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(`${apiBase}${normalizedPath}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
      redirect: "follow",
    });
    if (res.ok) return await res.json();
    if ((res.status === 400 || res.status === 401 || res.status === 404) && attempt < 4) {
      await new Promise((r) => setTimeout(r, 300));
      continue;
    }
    throw new Error(`POST ${path} on ${serviceSlug} failed: ${res.status} ${await res.text()}`);
  }
}

/**
 * Generic GET helper with retry logic for a SaaS service.
 *
 * @param serviceSlug - Service identifier.
 * @param token - JWT access token.
 * @param path - API path.
 * @returns Parsed JSON response.
 */
export async function serviceApiGet(
  serviceSlug: string,
  token: string,
  path: string
) {
  const apiBase = SERVICE_APIS[serviceSlug];
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(`${apiBase}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) return await res.json();
    if ((res.status === 401 || res.status === 404) && attempt < 4) {
      await new Promise((r) => setTimeout(r, 200));
      continue;
    }
    throw new Error(`GET ${path} on ${serviceSlug} failed: ${res.status} ${await res.text()}`);
  }
}

/**
 * Generic PATCH helper with retry logic for a SaaS service.
 *
 * @param serviceSlug - Service identifier.
 * @param token - JWT access token.
 * @param path - API path.
 * @param body - Request body object.
 * @returns Parsed JSON response.
 */
export async function serviceApiPatch(
  serviceSlug: string,
  token: string,
  path: string,
  body: unknown
) {
  const apiBase = SERVICE_APIS[serviceSlug];
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(`${apiBase}${path}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });
    if (res.ok) return await res.json();
    if ((res.status === 401 || res.status === 404) && attempt < 4) {
      await new Promise((r) => setTimeout(r, 200));
      continue;
    }
    throw new Error(`PATCH ${path} on ${serviceSlug} failed: ${res.status} ${await res.text()}`);
  }
}

/**
 * Generic DELETE helper with retry logic for a SaaS service.
 *
 * @param serviceSlug - Service identifier.
 * @param token - JWT access token.
 * @param path - API path.
 */
export async function serviceApiDelete(
  serviceSlug: string,
  token: string,
  path: string
) {
  const apiBase = SERVICE_APIS[serviceSlug];
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(`${apiBase}${path}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok || res.status === 204) return;
    if ((res.status === 401 || res.status === 404) && attempt < 4) {
      await new Promise((r) => setTimeout(r, 200));
      continue;
    }
    throw new Error(`DELETE ${path} on ${serviceSlug} failed: ${res.status} ${await res.text()}`);
  }
}

// ---------------------------------------------------------------------------
// Service-specific API helpers
// ---------------------------------------------------------------------------

// ── TrendScout ──────────────────────────────────────────────────────────────

/**
 * Create a research run on TrendScout.
 *
 * @param token - JWT token.
 * @param keywords - Search keywords.
 * @param sources - Data sources to query.
 * @returns The created research run.
 */
export async function createResearchRunAPI(
  token: string,
  keywords: string[] = ["wireless earbuds", "phone case"],
  sources: string[] = ["aliexpress", "google_trends"]
) {
  return serviceApiPost("trendscout", token, "/api/v1/research/runs", {
    keywords,
    sources,
  });
}

/**
 * Add an item to TrendScout watchlist.
 *
 * @param token - JWT token.
 * @param overrides - Optional field overrides.
 * @returns The created watchlist item.
 */
export async function addToWatchlistAPI(
  token: string,
  overrides: Record<string, unknown> = {}
) {
  return serviceApiPost("trendscout", token, "/api/v1/watchlist", {
    product_name: `Watch Item ${Date.now()}`,
    source: "aliexpress",
    source_url: "https://example.com/product/123",
    price: 19.99,
    score: 85,
    ...overrides,
  });
}

// ── ContentForge ────────────────────────────────────────────────────────────

/**
 * Create a content template on ContentForge.
 *
 * @param token - JWT token.
 * @param overrides - Optional field overrides.
 * @returns The created template.
 */
export async function createContentTemplateAPI(
  token: string,
  overrides: Record<string, unknown> = {}
) {
  return serviceApiPost("contentforge", token, "/api/v1/templates", {
    name: `Template ${Date.now()}`,
    content_type: "product_description",
    template_body: "Write a compelling description for {{product_name}}.",
    ...overrides,
  });
}

/**
 * Generate content on ContentForge.
 *
 * @param token - JWT token.
 * @param overrides - Optional field overrides.
 * @returns The generation job.
 */
export async function generateContentAPI(
  token: string,
  overrides: Record<string, unknown> = {}
) {
  return serviceApiPost("contentforge", token, "/api/v1/content/generate", {
    source_type: "manual",
    source_data: { name: "Wireless Earbuds" },
    content_types: ["description"],
    ...overrides,
  });
}

// ── RankPilot ───────────────────────────────────────────────────────────────

/**
 * Create a site on RankPilot.
 *
 * @param token - JWT token.
 * @param domain - Site domain.
 * @returns The created site.
 */
export async function createSiteAPI(
  token: string,
  domain?: string
) {
  return serviceApiPost("rankpilot", token, "/api/v1/sites", {
    domain: domain || `test-${Date.now()}.example.com`,
  });
}

/**
 * Add a tracked keyword on RankPilot.
 *
 * @param token - JWT token.
 * @param siteId - Site UUID.
 * @param keyword - Keyword to track.
 * @returns The created keyword.
 */
export async function createTrackedKeywordAPI(
  token: string,
  siteId: string,
  keyword?: string
) {
  return serviceApiPost("rankpilot", token, "/api/v1/keywords", {
    site_id: siteId,
    keyword: keyword || `keyword-${Date.now()}`,
  });
}

/**
 * Run an SEO audit on RankPilot.
 *
 * @param token - JWT token.
 * @param siteId - Site UUID.
 * @returns The audit result.
 */
export async function runSeoAuditAPI(token: string, siteId: string) {
  return serviceApiPost("rankpilot", token, "/api/v1/audits/run", {
    site_id: siteId,
  });
}

// ── FlowSend ────────────────────────────────────────────────────────────────

/**
 * Create a contact on FlowSend.
 *
 * @param token - JWT token.
 * @param overrides - Optional field overrides.
 * @returns The created contact.
 */
export async function createContactAPI(
  token: string,
  overrides: Record<string, unknown> = {}
) {
  return serviceApiPost("flowsend", token, "/api/v1/contacts", {
    email: uniqueEmail(),
    first_name: "Test",
    last_name: "Contact",
    ...overrides,
  });
}

/**
 * Create an email campaign on FlowSend.
 *
 * @param token - JWT token.
 * @param overrides - Optional field overrides.
 * @returns The created campaign.
 */
export async function createCampaignAPI(
  token: string,
  overrides: Record<string, unknown> = {}
) {
  return serviceApiPost("flowsend", token, "/api/v1/campaigns", {
    name: `Campaign ${Date.now()}`,
    subject: "Test Campaign Subject",
    html_body: "<h1>Hello!</h1><p>This is a test campaign.</p>",
    ...overrides,
  });
}

/**
 * Create an email template on FlowSend.
 *
 * @param token - JWT token.
 * @param overrides - Optional field overrides.
 * @returns The created template.
 */
export async function createEmailTemplateAPI(
  token: string,
  overrides: Record<string, unknown> = {}
) {
  return serviceApiPost("flowsend", token, "/api/v1/templates", {
    name: `Template ${Date.now()}`,
    subject: "Welcome {{first_name}}!",
    html_body: "<h1>Welcome!</h1>",
    ...overrides,
  });
}

/**
 * Create an automation flow on FlowSend.
 *
 * @param token - JWT token.
 * @param overrides - Optional field overrides.
 * @returns The created flow.
 */
export async function createFlowAPI(
  token: string,
  overrides: Record<string, unknown> = {}
) {
  return serviceApiPost("flowsend", token, "/api/v1/flows", {
    name: `Flow ${Date.now()}`,
    trigger_type: "signup",
    steps: [
      { type: "email", delay_minutes: 0, subject: "Welcome!", body: "<p>Hi!</p>" },
      { type: "email", delay_minutes: 1440, subject: "Day 2", body: "<p>Follow up</p>" },
    ],
    ...overrides,
  });
}

// ── SpyDrop ─────────────────────────────────────────────────────────────────

/**
 * Create a competitor on SpyDrop.
 *
 * @param token - JWT token.
 * @param overrides - Optional field overrides.
 * @returns The created competitor.
 */
export async function createCompetitorAPI(
  token: string,
  overrides: Record<string, unknown> = {}
) {
  return serviceApiPost("spydrop", token, "/api/v1/competitors", {
    name: `Competitor ${Date.now()}`,
    url: `https://competitor-${Date.now()}.example.com`,
    platform: "shopify",
    ...overrides,
  });
}

// ── PostPilot ───────────────────────────────────────────────────────────────

/**
 * Create a social account on PostPilot.
 *
 * @param token - JWT token.
 * @param overrides - Optional field overrides.
 * @returns The created account.
 */
export async function createSocialAccountAPI(
  token: string,
  overrides: Record<string, unknown> = {}
) {
  return serviceApiPost("postpilot", token, "/api/v1/accounts", {
    platform: "instagram",
    account_name: `@test_account_${Date.now()}`,
    access_token: "mock_access_token",
    ...overrides,
  });
}

/**
 * Create a social media post on PostPilot.
 *
 * @param token - JWT token.
 * @param accountId - Social account UUID.
 * @param overrides - Optional field overrides.
 * @returns The created post.
 */
export async function createSocialPostAPI(
  token: string,
  accountId: string,
  overrides: Record<string, unknown> = {}
) {
  return serviceApiPost("postpilot", token, "/api/v1/posts", {
    account_id: accountId,
    content: `Test post content ${Date.now()}`,
    platform: "instagram",
    ...overrides,
  });
}

// ── AdScale ─────────────────────────────────────────────────────────────────

/**
 * Create an ad account on AdScale.
 *
 * @param token - JWT token.
 * @param overrides - Optional field overrides.
 * @returns The created account.
 */
export async function createAdAccountAPI(
  token: string,
  overrides: Record<string, unknown> = {}
) {
  return serviceApiPost("adscale", token, "/api/v1/accounts", {
    platform: "meta",
    account_name: `Ad Account ${Date.now()}`,
    account_id_external: `act_${Date.now()}`,
    access_token: "mock_token",
    ...overrides,
  });
}

/**
 * Create an ad campaign on AdScale.
 *
 * @param token - JWT token.
 * @param accountId - Ad account UUID.
 * @param overrides - Optional field overrides.
 * @returns The created campaign.
 */
export async function createAdCampaignAPI(
  token: string,
  accountId: string,
  overrides: Record<string, unknown> = {}
) {
  return serviceApiPost("adscale", token, "/api/v1/campaigns", {
    ad_account_id: accountId,
    name: `Ad Campaign ${Date.now()}`,
    objective: "conversions",
    daily_budget: 50.0,
    status: "active",
    ...overrides,
  });
}

/**
 * Create an ad creative on AdScale.
 *
 * @param token - JWT token.
 * @param overrides - Optional field overrides.
 * @returns The created creative.
 */
export async function createAdCreativeAPI(
  token: string,
  overrides: Record<string, unknown> = {}
) {
  return serviceApiPost("adscale", token, "/api/v1/creatives", {
    name: `Creative ${Date.now()}`,
    headline: "Shop Now!",
    body: "Get 50% off today only",
    image_url: "https://example.com/ad.jpg",
    call_to_action: "SHOP_NOW",
    ...overrides,
  });
}

// ── ShopChat ────────────────────────────────────────────────────────────────

/**
 * Create a chatbot on ShopChat.
 *
 * @param token - JWT token.
 * @param overrides - Optional field overrides.
 * @returns The created chatbot.
 */
export async function createChatbotAPI(
  token: string,
  overrides: Record<string, unknown> = {}
) {
  return serviceApiPost("shopchat", token, "/api/v1/chatbots", {
    name: `Bot ${Date.now()}`,
    welcome_message: "Hi! How can I help you today?",
    ...overrides,
  });
}

/**
 * Add a knowledge base entry on ShopChat.
 *
 * @param token - JWT token.
 * @param chatbotId - Chatbot UUID.
 * @param overrides - Optional field overrides.
 * @returns The created KB entry.
 */
export async function createKnowledgeEntryAPI(
  token: string,
  chatbotId: string,
  overrides: Record<string, unknown> = {}
) {
  return serviceApiPost("shopchat", token, "/api/v1/knowledge", {
    chatbot_id: chatbotId,
    question: `FAQ ${Date.now()}: What is your return policy?`,
    answer: "We offer 30-day hassle-free returns on all orders.",
    ...overrides,
  });
}

// ── Admin ───────────────────────────────────────────────────────────────────

/**
 * Login to the admin dashboard via the API.
 *
 * @param email - Admin email.
 * @param password - Admin password.
 * @returns The JWT access token.
 */
export async function loginAdminAPI(
  email = ADMIN_EMAIL,
  password = ADMIN_PASSWORD
): Promise<string> {
  const res = await fetch(
    `${SERVICE_APIS.admin}/api/v1/admin/auth/login`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }
  );
  if (!res.ok) throw new Error(`Admin login failed: ${res.status}`);
  const data = await res.json();
  return data.access_token;
}

/**
 * Login via the admin dashboard UI.
 *
 * @param page - Playwright page instance.
 * @param email - Admin email.
 * @param password - Admin password.
 */
export async function adminLogin(
  page: Page,
  email = ADMIN_EMAIL,
  password = ADMIN_PASSWORD
) {
  // Navigate to login, clear localStorage, and reload to avoid auto-redirect
  await page.goto("/login");
  await page.evaluate(() => localStorage.clear());
  await page.goto("/login");
  await page.waitForSelector("#email", { timeout: 10000 });
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.getByRole("button", { name: /sign in|create account/i }).click();
  // Wait for navigation away from login page
  await page.waitForFunction(
    () => !window.location.pathname.includes("/login"),
    { timeout: 15000 }
  );
  await page.waitForLoadState("networkidle");
}

/**
 * Get or create the seed user token on a SaaS service.
 *
 * Tries to login with seed credentials first; registers if not found.
 * This is used for seed data e2e tests that validate pre-populated data.
 *
 * @param serviceSlug - Service identifier.
 * @returns JWT access token for the seed user.
 */
export async function getSeedToken(serviceSlug: string): Promise<string> {
  const apiBase = SERVICE_APIS[serviceSlug];
  for (let attempt = 0; attempt < 10; attempt++) {
    try {
      const res = await fetch(`${apiBase}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: SEED_EMAIL, password: SEED_PASSWORD }),
      });
      if (res.ok) return (await res.json()).access_token;
    } catch {
      // Service not ready
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`Cannot get seed token for ${serviceSlug}`);
}

/**
 * Seed the entire database using the seed script.
 *
 * Idempotent — safe to call multiple times. Checks if seed data already
 * exists by attempting to login as the demo user on the core platform.
 */
export async function seedAllServices(): Promise<void> {
  const coreApi = "http://localhost:8000";
  const loginRes = await fetch(`${coreApi}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: SEED_EMAIL, password: SEED_PASSWORD }),
  }).catch(() => null);

  if (loginRes?.ok) return; // Already seeded

  const { execSync } = await import("child_process");
  execSync("npx tsx /workspaces/ecomm/scripts/seed.ts", {
    cwd: "/workspaces/ecomm",
    timeout: 180000,
    stdio: "pipe",
  });
  await new Promise((r) => setTimeout(r, 3000));
}
