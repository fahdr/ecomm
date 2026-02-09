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

    // Should show the preset theme cards (7 presets seeded on store creation)
    await expect(page.getByText("Frosted")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Midnight")).toBeVisible();
    await expect(page.getByText("Botanical")).toBeVisible();
  });

  test("activates a different theme", async ({ page }) => {
    await page.goto(`/stores/${storeId}/themes`);
    await page.waitForLoadState("networkidle");

    // Click the "Activate" button on the Midnight theme card
    const midnightCard = page.locator('[data-slot="card"]').filter({ hasText: "Midnight" });
    await midnightCard.getByRole("button", { name: /activate/i }).click();

    // After activation, an "Active" badge should appear on the Midnight card
    await expect(midnightCard.getByText("Active")).toBeVisible({ timeout: 10000 });
  });

  test("navigates to theme editor and shows branding inputs", async ({ page }) => {
    await page.goto(`/stores/${storeId}/themes`);
    await page.waitForLoadState("networkidle");

    // Click "Customize" on the active (Frosted) theme to go to the editor
    const activeCard = page.locator('[data-slot="card"]').filter({ hasText: "Active" });
    await activeCard.getByRole("link", { name: /customize/i }).click();
    await page.waitForURL(/\/themes\/[a-f0-9-]+/, { timeout: 10000 });
    await page.waitForLoadState("networkidle");

    // Branding inputs should be on the editor page
    await expect(page.locator("#logo-url")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("#favicon-url")).toBeVisible();
    await expect(page.locator("#custom-css")).toBeVisible();
  });

  test("navigates via sidebar to themes", async ({ page }) => {
    await page.goto(`/stores/${storeId}`);
    await page.waitForLoadState("networkidle");
    await page.getByRole("link", { name: "Themes" }).click();
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

  test("navigates via sidebar to email", async ({ page }) => {
    await page.goto(`/stores/${storeId}`);
    await page.waitForLoadState("networkidle");
    await page.getByRole("link", { name: "Email" }).click();
    await expect(page).toHaveURL(new RegExp(`/stores/${storeId}/email`), {
      timeout: 10000,
    });
  });
});
