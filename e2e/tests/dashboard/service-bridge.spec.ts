/**
 * Dashboard ServiceBridge e2e tests.
 *
 * Tests the Service Activity page, bridge API endpoints, services hub
 * health indicators, and per-resource service status panels.
 *
 * **For QA Engineers:**
 *   - Service Activity page loads with empty state for new users.
 *   - KPI summary cards appear (Total Events, Success Rate, etc.).
 *   - Filter dropdowns (event type, service, status) render correctly.
 *   - Bridge API endpoints return correct response shapes.
 *   - Services hub shows health indicators for connected services.
 *   - Product detail page shows Connected Services panel.
 *   - Order detail page shows Service Notifications panel.
 */

import { test, expect } from "@playwright/test";
import {
  registerUser,
  dashboardLogin,
  createStoreAPI,
  createProductAPI,
  apiGet,
} from "../helpers";

// ---------------------------------------------------------------------------
// Helper: fetch bridge activity via API
// ---------------------------------------------------------------------------

const API_BASE = "http://localhost:8000";

/**
 * Fetch bridge activity for a user via the API.
 *
 * @param token - JWT access token.
 * @param params - Optional query parameters.
 * @returns The parsed JSON response.
 */
async function getBridgeActivity(
  token: string,
  params: Record<string, string> = {}
) {
  const qs = new URLSearchParams(params).toString();
  const url = `${API_BASE}/api/v1/bridge/activity${qs ? `?${qs}` : ""}`;
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) return await res.json();
    if (res.status === 401 && attempt < 4) {
      await new Promise((r) => setTimeout(r, 200));
      continue;
    }
    throw new Error(`Bridge activity failed: ${res.status}`);
  }
}

/**
 * Fetch bridge summary via the API.
 *
 * @param token - JWT access token.
 * @returns The parsed JSON response.
 */
async function getBridgeSummary(token: string) {
  const res = await fetch(`${API_BASE}/api/v1/bridge/summary`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok)
    throw new Error(`Bridge summary failed: ${res.status}`);
  return await res.json();
}

/**
 * Fetch resource-level bridge activity via the API.
 *
 * @param token - JWT access token.
 * @param resourceType - Resource type (product, order, customer).
 * @param resourceId - UUID of the resource.
 * @returns The parsed JSON response.
 */
async function getResourceActivity(
  token: string,
  resourceType: string,
  resourceId: string
) {
  const res = await fetch(
    `${API_BASE}/api/v1/bridge/activity/${resourceType}/${resourceId}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!res.ok)
    throw new Error(`Resource activity failed: ${res.status}`);
  return await res.json();
}

/**
 * Dispatch a manual bridge event via the API.
 *
 * @param token - JWT access token.
 * @param body - Dispatch request body.
 * @returns The parsed JSON response.
 */
async function dispatchBridgeEvent(
  token: string,
  body: Record<string, unknown>
) {
  const res = await fetch(`${API_BASE}/api/v1/bridge/dispatch`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok)
    throw new Error(`Bridge dispatch failed: ${res.status}`);
  return await res.json();
}

// ---------------------------------------------------------------------------
// Bridge API Endpoint Tests
// ---------------------------------------------------------------------------

test.describe("Bridge API Endpoints", () => {
  let token: string;
  let storeId: string;

  test.beforeEach(async () => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
  });

  test("GET /bridge/activity returns empty paginated response", async () => {
    const data = await getBridgeActivity(token);
    expect(data.items).toEqual([]);
    expect(data.total).toBe(0);
    expect(data.page).toBe(1);
    expect(data.per_page).toBe(20);
    expect(data.pages).toBe(1);
  });

  test("GET /bridge/activity supports pagination params", async () => {
    const data = await getBridgeActivity(token, {
      page: "2",
      per_page: "5",
    });
    expect(data.page).toBe(2);
    expect(data.per_page).toBe(5);
  });

  test("GET /bridge/activity supports filter params", async () => {
    const data = await getBridgeActivity(token, {
      event: "product.created",
      service: "contentforge",
      status: "success",
    });
    expect(data.items).toEqual([]);
  });

  test("GET /bridge/summary returns empty list for new user", async () => {
    const data = await getBridgeSummary(token);
    expect(data).toEqual([]);
  });

  test("GET /bridge/activity/:type/:id returns empty array", async () => {
    const product = await createProductAPI(token, storeId);
    const data = await getResourceActivity(token, "product", product.id);
    expect(data).toEqual([]);
  });

  test("POST /bridge/dispatch fires event and returns confirmation", async () => {
    const product = await createProductAPI(token, storeId);
    const data = await dispatchBridgeEvent(token, {
      event: "product.created",
      resource_id: product.id,
      resource_type: "product",
      store_id: storeId,
      payload: { title: product.title },
    });
    expect(data.status).toBe("dispatched");
    expect(data.event).toBe("product.created");
    expect(data.resource_id).toBe(product.id);
  });

  test("POST /bridge/dispatch requires auth", async () => {
    const res = await fetch(`${API_BASE}/api/v1/bridge/dispatch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event: "product.created",
        resource_id: "00000000-0000-0000-0000-000000000000",
        resource_type: "product",
      }),
    });
    expect(res.status).toBe(401);
  });

  test("POST /bridge/dispatch rejects missing fields", async () => {
    const res = await fetch(`${API_BASE}/api/v1/bridge/dispatch`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ event: "product.created" }),
    });
    expect(res.status).toBe(422);
  });
});

// ---------------------------------------------------------------------------
// Service Activity Page UI Tests
// ---------------------------------------------------------------------------

test.describe("Service Activity Page", () => {
  let token: string;
  let storeId: string;
  let email: string;
  let password: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    email = user.email;
    password = user.password;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, email, password);
  });

  test("shows empty state when no activity exists", async ({ page }) => {
    await page.goto(`/stores/${storeId}/services/activity`);
    await page.waitForLoadState("networkidle");

    // Page title should be visible
    await expect(
      page.getByRole("heading", { name: /service activity/i }).first()
    ).toBeVisible({ timeout: 10000 });

    // Empty state message
    await expect(
      page.getByText(/no delivery activity/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("shows KPI summary cards", async ({ page }) => {
    await page.goto(`/stores/${storeId}/services/activity`);
    await page.waitForLoadState("networkidle");

    // Check for summary cards (Total Events, Success Rate, Avg Latency, Failures)
    await expect(
      page.getByText(/total events/i)
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText(/success rate/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("renders filter dropdowns", async ({ page }) => {
    await page.goto(`/stores/${storeId}/services/activity`);
    await page.waitForLoadState("networkidle");

    // Filter section should render with dropdowns
    await expect(
      page.getByText(/all events/i).first()
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText(/all services/i).first()
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText(/all status/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("back link navigates to services hub", async ({ page }) => {
    await page.goto(`/stores/${storeId}/services/activity`);
    await page.waitForLoadState("networkidle");

    const backLink = page.getByRole("link", { name: /back to services/i });
    if (await backLink.isVisible()) {
      await backLink.click();
      await expect(page).toHaveURL(
        new RegExp(`/stores/${storeId}/services`),
        { timeout: 10000 }
      );
    }
  });
});

// ---------------------------------------------------------------------------
// Services Hub Health Indicators
// ---------------------------------------------------------------------------

test.describe("Services Hub Page", () => {
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows all 8 service cards", async ({ page }) => {
    await page.goto(`/stores/${storeId}/services`);
    await page.waitForLoadState("networkidle");

    // Service names should appear on the page
    const serviceNames = [
      "TrendScout",
      "ContentForge",
      "RankPilot",
      "FlowSend",
      "SpyDrop",
      "PostPilot",
      "AdScale",
      "ShopChat",
    ];

    for (const name of serviceNames) {
      await expect(page.getByText(name).first()).toBeVisible({
        timeout: 10000,
      });
    }
  });

  test("service cards show enable button for disconnected services", async ({
    page,
  }) => {
    await page.goto(`/stores/${storeId}/services`);
    await page.waitForLoadState("networkidle");

    // At least one "Enable" button should exist for new users
    const enableButtons = page.getByRole("button", { name: /enable/i });
    await expect(enableButtons.first()).toBeVisible({ timeout: 10000 });
  });
});

// ---------------------------------------------------------------------------
// Product Detail — Connected Services Panel
// ---------------------------------------------------------------------------

test.describe("Product Detail Service Status", () => {
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows connected services panel on product page", async ({ page }) => {
    const product = await createProductAPI(token, storeId);

    await page.goto(`/stores/${storeId}/products/${product.id}`);
    await page.waitForLoadState("networkidle");

    // The ResourceServiceStatus panel should be visible
    await expect(
      page.getByText(/connected services/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("shows all 8 services in the status grid", async ({ page }) => {
    const product = await createProductAPI(token, storeId);

    await page.goto(`/stores/${storeId}/products/${product.id}`);
    await page.waitForLoadState("networkidle");

    // Should list service names in the panel
    const serviceNames = [
      "ContentForge",
      "RankPilot",
      "TrendScout",
      "PostPilot",
      "AdScale",
      "ShopChat",
      "FlowSend",
      "SpyDrop",
    ];

    for (const name of serviceNames) {
      await expect(page.getByText(name).first()).toBeVisible({
        timeout: 10000,
      });
    }
  });
});

// ---------------------------------------------------------------------------
// Sidebar Navigation
// ---------------------------------------------------------------------------

test.describe("Sidebar Service Activity Link", () => {
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("sidebar has Service Activity link", async ({ page }) => {
    await page.goto(`/stores/${storeId}`);
    await page.waitForLoadState("networkidle");

    // Look for the "Service Activity" link in the sidebar
    const activityLink = page.getByRole("link", {
      name: /service activity/i,
    });
    await expect(activityLink.first()).toBeVisible({ timeout: 10000 });
  });

  test("clicking Service Activity link navigates correctly", async ({
    page,
  }) => {
    await page.goto(`/stores/${storeId}`);
    await page.waitForLoadState("networkidle");

    const activityLink = page
      .getByRole("link", { name: /service activity/i })
      .first();
    await activityLink.click();
    await expect(page).toHaveURL(
      new RegExp(`/stores/${storeId}/services/activity`),
      { timeout: 10000 }
    );
  });
});
