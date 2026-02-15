/**
 * TrendScout watchlist e2e tests.
 *
 * Note: Adding items to the watchlist requires research results (from a
 * completed research run), which depends on Celery processing. These tests
 * focus on UI behavior that doesn't require seeded data.
 */

import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin } from "../service-helpers";

test.describe("TrendScout Watchlist", () => {
  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("trendscout");
    await serviceLogin(page, user.email, user.password);
  });

  test("shows empty state when watchlist is empty", async ({ page }) => {
    await page.goto("/watchlist");
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("heading", { name: /your watchlist is empty/i })).toBeVisible({ timeout: 10000 });
  });

  test("displays watchlist page with status tabs", async ({ page }) => {
    await page.goto("/watchlist");
    await page.waitForLoadState("networkidle");

    // Verify the page renders with filter tabs
    await expect(page.getByRole("heading", { name: /watchlist/i }).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole("button", { name: /^all$/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /^watching$/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /^dismissed$/i })).toBeVisible();
  });

  test("shows filtered empty state when switching tabs", async ({ page }) => {
    await page.goto("/watchlist");
    await page.waitForLoadState("networkidle");

    // Click Watching tab
    await page.getByRole("button", { name: /^watching$/i }).click();
    await page.waitForLoadState("networkidle");

    // Should show empty state for this tab
    await expect(page.getByRole("heading", { name: /no watching items/i })).toBeVisible({ timeout: 10000 });
  });
});
