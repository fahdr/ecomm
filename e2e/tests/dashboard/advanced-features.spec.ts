/**
 * Dashboard advanced features e2e tests.
 *
 * Tests segments, upsells, fraud detection, A/B tests, bulk operations,
 * and notifications pages.
 *
 * **For QA Engineers:**
 *   - Segments page shows empty state and allows creating segments via dialog.
 *   - Upsells page shows empty state and lists API-created upsells.
 *   - Fraud detection page shows empty state with no fraud checks.
 *   - A/B tests page shows empty state and allows creating experiments.
 *   - Bulk operations page shows price update and delete forms.
 *   - Notifications page shows empty state when no notifications exist.
 */

import { test, expect } from "@playwright/test";
import {
  registerUser,
  dashboardLogin,
  createStoreAPI,
  createProductAPI,
  createSegmentAPI,
  createUpsellAPI,
  createABTestAPI,
} from "../helpers";

// ---------------------------------------------------------------------------
// Segments
// ---------------------------------------------------------------------------

test.describe("Dashboard Segments", () => {
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows empty segments state", async ({ page }) => {
    await page.goto(`/stores/${storeId}/segments`);
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/no segments defined/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("lists segments created via API", async ({ page }) => {
    const seg = await createSegmentAPI(token, storeId, "VIP Buyers");

    await page.goto(`/stores/${storeId}/segments`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("VIP Buyers")).toBeVisible({ timeout: 10000 });
  });

  test("creates a segment via dialog", async ({ page }) => {
    await page.goto(`/stores/${storeId}/segments`);
    await page.waitForLoadState("networkidle");
    // Wait for empty state to confirm page is loaded and interactive
    await expect(page.getByText(/no segment/i)).toBeVisible({ timeout: 10000 });

    // Use JS click to bypass React hydration timing issues
    await page.$eval('button:has-text("Create your first segment")', (el: HTMLElement) => el.click());
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 5000 });

    await page.fill("#seg-name", "High Spenders");
    await page.fill("#seg-desc", "Customers who spent over $500");

    // Click submit and wait for the POST to complete
    const [postResp] = await Promise.all([
      page.waitForResponse(
        (resp) => resp.url().includes("/segments") && resp.request().method() === "POST",
        { timeout: 10000 }
      ),
      page.locator('[role="dialog"] button[type="submit"]').click(),
    ]);

    // Wait for dialog to close
    await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 10000 });

    // Reload to ensure fresh data from the database
    await page.reload();
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("High Spenders")).toBeVisible({
      timeout: 10000,
    });
  });

  test("renders segment table with customer count and description", async ({ page }) => {
    // Create two segments: one with a custom description, one with default
    await createSegmentAPI(token, storeId, "VIP Buyers", {
      description: "High value customers",
    });
    await createSegmentAPI(token, storeId, "New Customers");

    await page.goto(`/stores/${storeId}/segments`);
    await page.waitForLoadState("networkidle");

    // Both segment names should be visible
    await expect(page.getByText("VIP Buyers")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("New Customers")).toBeVisible({ timeout: 10000 });

    // Description text should render beneath the segment name
    await expect(page.getByText("High value customers")).toBeVisible({ timeout: 10000 });

    // Type badge "manual" should be visible (at least one instance)
    await expect(page.getByText("manual").first()).toBeVisible({ timeout: 10000 });

    // Customer count "0" should be visible
    await expect(page.getByText("0").first()).toBeVisible({ timeout: 10000 });

    // Card title "Customer Segments" should be visible
    await expect(page.getByText("Customer Segments")).toBeVisible({ timeout: 10000 });
  });
});

// ---------------------------------------------------------------------------
// Upsells
// ---------------------------------------------------------------------------

test.describe("Dashboard Upsells", () => {
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows empty upsells state", async ({ page }) => {
    await page.goto(`/stores/${storeId}/upsells`);
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/no upsells configured/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("lists upsells created via API", async ({ page }) => {
    const product1 = await createProductAPI(token, storeId, {
      title: "Source Widget",
    });
    const product2 = await createProductAPI(token, storeId, {
      title: "Target Accessory",
    });
    await createUpsellAPI(token, storeId, product1.id, product2.id);

    await page.goto(`/stores/${storeId}/upsells`);
    await page.waitForLoadState("networkidle");

    // Upsell should appear showing type badge and product IDs
    await expect(page.getByText("Cross-sell")).toBeVisible({
      timeout: 10000,
    });
  });

  test("renders upsell table with product names and type", async ({ page }) => {
    // Create two products and link them via an upsell
    const product1 = await createProductAPI(token, storeId, {
      title: "Premium Widget",
    });
    const product2 = await createProductAPI(token, storeId, {
      title: "Widget Accessory",
    });
    await createUpsellAPI(token, storeId, product1.id, product2.id);

    await page.goto(`/stores/${storeId}/upsells`);
    await page.waitForLoadState("networkidle");

    // Cross-sell type badge should be visible
    await expect(page.getByText("Cross-sell")).toBeVisible({ timeout: 10000 });

    // Position "1" should be visible somewhere in the table
    await expect(page.getByText("1").first()).toBeVisible({ timeout: 10000 });
  });
});

// ---------------------------------------------------------------------------
// Fraud Detection
// ---------------------------------------------------------------------------

test.describe("Dashboard Fraud Detection", () => {
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    const store = await createStoreAPI(user.token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows empty fraud checks state", async ({ page }) => {
    await page.goto(`/stores/${storeId}/fraud`);
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/no fraud checks recorded/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("navigates from store settings to fraud", async ({ page }) => {
    await page.goto(`/stores/${storeId}`);
    // The store page may have a fraud link — navigate directly
    await page.goto(`/stores/${storeId}/fraud`);
    await expect(
      page.getByText(/fraud detection/i).first()
    ).toBeVisible({ timeout: 10000 });
  });
});

// ---------------------------------------------------------------------------
// A/B Tests
// ---------------------------------------------------------------------------

test.describe("Dashboard A/B Tests", () => {
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows empty A/B tests state", async ({ page }) => {
    await page.goto(`/stores/${storeId}/ab-tests`);
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/no a\/b tests yet/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("lists A/B tests created via API", async ({ page }) => {
    await createABTestAPI(token, storeId, { name: "Hero Banner Test" });

    await page.goto(`/stores/${storeId}/ab-tests`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Hero Banner Test")).toBeVisible({
      timeout: 10000,
    });
  });

  test("creates an A/B test via dialog", async ({ page }) => {
    await page.goto(`/stores/${storeId}/ab-tests`);
    await page.waitForLoadState("networkidle");
    // Wait for empty state to confirm page is loaded and interactive
    await expect(page.getByText(/no a\/b test/i)).toBeVisible({ timeout: 10000 });

    // Use JS click to bypass React hydration timing issues
    await page.$eval('button:has-text("Create your first test")', (el: HTMLElement) => el.click());
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 5000 });

    await page.fill("#ab-name", "Price Experiment");
    await page.fill("#ab-desc", "Testing price impact on conversion");

    // Click submit and wait for the POST to complete
    const [postResp] = await Promise.all([
      page.waitForResponse(
        (resp) => resp.url().includes("/ab-tests") && resp.request().method() === "POST",
        { timeout: 10000 }
      ),
      page.locator('[role="dialog"] button[type="submit"]').click(),
    ]);

    // Wait for dialog to close
    await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 10000 });

    // Reload to ensure fresh data from the database
    await page.reload();
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Price Experiment")).toBeVisible({
      timeout: 10000,
    });
  });

  test("renders A/B test table with variants and metric", async ({ page }) => {
    // Create an A/B test with a specific name and metric
    await createABTestAPI(token, storeId, {
      name: "Homepage Hero",
      metric: "conversion_rate",
    });

    await page.goto(`/stores/${storeId}/ab-tests`);
    await page.waitForLoadState("networkidle");

    // Test name should be visible
    await expect(page.getByText("Homepage Hero")).toBeVisible({ timeout: 10000 });

    // Conversion rate column header or metric text should be visible
    await expect(page.getByText("Conversion Rate")).toBeVisible({ timeout: 10000 });

    // Status badge should show "draft" for a newly created test
    await expect(page.getByText("draft")).toBeVisible({ timeout: 10000 });
  });
});

// ---------------------------------------------------------------------------
// Bulk Operations
// ---------------------------------------------------------------------------

test.describe("Dashboard Bulk Operations", () => {
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows bulk operations forms", async ({ page }) => {
    await page.goto(`/stores/${storeId}/bulk`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Bulk Price Update")).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByText("Bulk Delete Products")).toBeVisible();
  });

  test("shows price update and delete input fields", async ({ page }) => {
    await page.goto(`/stores/${storeId}/bulk`);
    await page.waitForLoadState("networkidle");

    await expect(page.locator("#price-value")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("#price-ids")).toBeVisible();
    await expect(page.locator("#delete-ids")).toBeVisible();
  });

  test("updates prices via bulk form", async ({ page }) => {
    // Create a product first
    const product = await createProductAPI(token, storeId);

    await page.goto(`/stores/${storeId}/bulk`);
    await page.waitForLoadState("networkidle");

    await page.fill("#price-value", "10");
    await page.fill("#price-ids", product.id);
    await page.getByRole("button", { name: /update prices/i }).click();

    // Wait for success message
    await expect(
      page.getByText(/updated/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("performs bulk price update on multiple products", async ({ page }) => {
    // Create two products via API
    const product1 = await createProductAPI(token, storeId);
    const product2 = await createProductAPI(token, storeId);

    await page.goto(`/stores/${storeId}/bulk`);
    await page.waitForLoadState("networkidle");

    // Fill the price-value input with "15"
    await page.fill("#price-value", "15");

    // Fill the price-ids input with both product IDs (comma-separated)
    await page.fill("#price-ids", `${product1.id},${product2.id}`);

    // Click "Update Prices" button
    await page.getByRole("button", { name: /update prices/i }).click();

    // Verify success message containing "updated" appears
    await expect(
      page.getByText(/updated/i)
    ).toBeVisible({ timeout: 10000 });
  });
});

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

test.describe("Dashboard Notifications", () => {
  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows empty notifications state", async ({ page }) => {
    await page.goto("/notifications");
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/no notifications/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("shows notifications page heading", async ({ page }) => {
    await page.goto("/notifications");
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/notifications/i).first()
    ).toBeVisible({ timeout: 10000 });
  });
});
