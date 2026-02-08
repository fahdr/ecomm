/**
 * Dashboard gift card management e2e tests.
 *
 * Tests gift card creation, listing, and empty state.
 *
 * **For QA Engineers:**
 *   - Gift card list shows code, balance, and status.
 *   - Creating a gift card generates a unique code (GC-XXXX-XXXX-XXXX).
 *   - Empty state is shown when no gift cards exist.
 */

import { test, expect } from "@playwright/test";
import {
  registerUser,
  dashboardLogin,
  createStoreAPI,
  createGiftCardAPI,
} from "../helpers";

test.describe("Dashboard Gift Card Management", () => {
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows empty state when no gift cards exist", async ({ page }) => {
    await page.goto(`/stores/${storeId}/gift-cards`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/no gift card/i)).toBeVisible({ timeout: 10000 });
  });

  test("lists gift cards created via API", async ({ page }) => {
    await createGiftCardAPI(token, storeId, 100);

    await page.goto(`/stores/${storeId}/gift-cards`);

    // Wait for the table to appear with the gift card data
    await expect(page.locator("table")).toBeVisible({ timeout: 15000 });
    await expect(page.locator("code").first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator("code").first()).toContainText("GC-");
    // Balance should be visible
    await expect(page.getByText("$100.00").first()).toBeVisible();
  });

  test("creates a gift card via dialog", async ({ page }) => {
    await page.goto(`/stores/${storeId}/gift-cards`);
    await page.waitForLoadState("networkidle");
    // Wait for empty state to confirm page is loaded and interactive
    await expect(page.getByText(/no gift card/i)).toBeVisible({ timeout: 10000 });

    // Use JS click to bypass React hydration timing issues
    await page.$eval('button:has-text("Issue your first gift card")', (el: HTMLElement) => el.click());
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 5000 });

    await page.fill("#gc-balance", "75");

    // Click submit and wait for the API response
    const [response] = await Promise.all([
      page.waitForResponse(
        (resp) => resp.url().includes("/gift-cards") && resp.request().method() === "POST",
        { timeout: 10000 }
      ),
      page.locator('[role="dialog"] button[type="submit"]').click(),
    ]);

    // Wait for dialog to close
    await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 10000 });

    // Reload to ensure fresh data from the database
    await page.reload();
    await page.waitForLoadState("networkidle");

    // New gift card should appear with GC- code
    await expect(page.locator("table")).toBeVisible({ timeout: 15000 });
    await expect(page.locator("code").first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator("code").first()).toContainText("GC-");
  });

  test("renders gift card table with multiple cards and formatted balances", async ({
    page,
  }) => {
    // Create two gift cards with different balances
    const card1 = await createGiftCardAPI(token, storeId, 150);
    const card2 = await createGiftCardAPI(token, storeId, 25.5);

    await page.goto(`/stores/${storeId}/gift-cards`);
    await page.waitForLoadState("networkidle");

    // Verify the table is visible
    await expect(page.locator("table")).toBeVisible({ timeout: 10000 });

    // Both GC- codes should be present
    const code1 = card1.code;
    const code2 = card2.code;
    await expect(page.getByText(code1).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(code2).first()).toBeVisible({ timeout: 10000 });

    // Formatted balances should be visible
    await expect(page.getByText("$150.00").first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("$25.50").first()).toBeVisible({ timeout: 10000 });

    // Card count text should be visible
    await expect(page.getByText(/2 cards issued/i).first()).toBeVisible({
      timeout: 10000,
    });
  });
});
