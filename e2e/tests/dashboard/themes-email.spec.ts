/**
 * Dashboard themes and email settings e2e tests.
 *
 * Tests theme selection/customization and email template listing.
 *
 * **For QA Engineers:**
 *   - Themes page shows theme cards and branding inputs.
 *   - Selecting a theme highlights it as active.
 *   - Saving theme settings persists via the store API.
 *   - Email page shows all 7 transactional email templates.
 *   - Email page displays "Dev Mode" badge.
 */

import { test, expect } from "@playwright/test";
import { registerUser, dashboardLogin, createStoreAPI } from "../helpers";

test.describe("Dashboard Theme Customization", () => {
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    const store = await createStoreAPI(user.token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows theme selection cards", async ({ page }) => {
    await page.goto(`/stores/${storeId}/themes`);
    await page.waitForLoadState("networkidle");

    // Should show the theme cards
    await expect(page.getByText("Default")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Modern")).toBeVisible();
    await expect(page.getByText("Ocean")).toBeVisible();
  });

  test("selects a different theme", async ({ page }) => {
    await page.goto(`/stores/${storeId}/themes`);
    await page.waitForLoadState("networkidle");

    // Click on the "Midnight" theme card
    await page.getByText("Midnight").click();

    // The active badge should appear on the selected theme
    await expect(
      page.locator("button").filter({ hasText: /midnight/i }).locator("..").getByText("Active")
    ).toBeVisible({ timeout: 5000 });
  });

  test("saves theme settings", async ({ page }) => {
    await page.goto(`/stores/${storeId}/themes`);
    await page.waitForLoadState("networkidle");

    // Fill branding fields
    await page.fill("#logo-url", "https://example.com/logo.png");
    await page.fill("#favicon-url", "https://example.com/favicon.ico");

    await page.getByRole("button", { name: /save theme/i }).click();
    await expect(page.getByText(/saved successfully/i)).toBeVisible({
      timeout: 10000,
    });
  });

  test("shows branding input fields", async ({ page }) => {
    await page.goto(`/stores/${storeId}/themes`);
    await page.waitForLoadState("networkidle");

    await expect(page.locator("#logo-url")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("#favicon-url")).toBeVisible();
    await expect(page.locator("#custom-css")).toBeVisible();
  });

  test("navigates from store settings to themes", async ({ page }) => {
    await page.goto(`/stores/${storeId}`);
    await page.getByRole("button", { name: /themes/i }).click();
    await expect(page).toHaveURL(new RegExp(`/stores/${storeId}/themes`), {
      timeout: 10000,
    });
  });
});

test.describe("Dashboard Email Settings", () => {
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    const store = await createStoreAPI(user.token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows email templates list", async ({ page }) => {
    await page.goto(`/stores/${storeId}/email`);
    await page.waitForLoadState("networkidle");

    // Should show template names
    await expect(page.getByText("Order Confirmation")).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByText("Order Shipped")).toBeVisible();
    await expect(page.getByText("Refund Notification")).toBeVisible();
    await expect(page.getByText("Welcome Email")).toBeVisible();
    await expect(page.getByText("Gift Card Delivery")).toBeVisible();
    await expect(page.getByText("Team Invitation")).toBeVisible();
  });

  test("shows dev mode banner", async ({ page }) => {
    await page.goto(`/stores/${storeId}/email`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(/dev mode/i)).toBeVisible({ timeout: 10000 });
  });

  test("shows summary cards with template counts", async ({ page }) => {
    await page.goto(`/stores/${storeId}/email`);
    await page.waitForLoadState("networkidle");

    // Total templates count
    await expect(page.getByText("7", { exact: true })).toBeVisible({ timeout: 10000 });
  });

  test("navigates from store settings to email", async ({ page }) => {
    await page.goto(`/stores/${storeId}`);
    await page.getByRole("button", { name: /email/i }).click();
    await expect(page).toHaveURL(new RegExp(`/stores/${storeId}/email`), {
      timeout: 10000,
    });
  });
});
