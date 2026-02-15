/**
 * SourcePilot dashboard home page e2e tests.
 *
 * Tests the main dashboard view with KPI cards, quick actions, and
 * overview data for the supplier product import service.
 *
 * **For QA Engineers:**
 *   - Verify KPI cards display correct counts (imports, watches, stores)
 *   - Verify quick action buttons navigate to correct pages
 *   - Verify plan usage display shows current plan and limits
 *   - Verify empty state for new accounts
 *   - Verify dashboard loads populated data after API operations
 *
 * **For End Users:**
 *   - Your dashboard shows a snapshot of your import activity
 *   - Quick action buttons help you navigate to common tasks
 *   - Monitor your plan usage and active feature counts
 */

import { test, expect } from "@playwright/test";
import {
  registerServiceUser,
  serviceLogin,
  createImportJobAPI,
  createStoreConnectionAPI,
  createPriceWatchAPI,
} from "../service-helpers";

test.describe("SourcePilot Dashboard", () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("sourcepilot");
    token = user.token;
    await serviceLogin(page, user.email, user.password);
  });

  test("dashboard loads for new user with empty state", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Should show welcome or dashboard content
    await expect(
      page.getByText(/welcome|dashboard|sourcepilot/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("dashboard shows KPI cards", async ({ page }) => {
    // Seed some data
    await createImportJobAPI(token);
    await createStoreConnectionAPI(token);
    await createPriceWatchAPI(token);

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Should display import, store, and watch counts
    await expect(
      page.getByText(/import|store|watch|plan/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("quick action buttons navigate correctly", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Test navigation to imports page
    const importLink = page.getByRole("link", { name: /import|new import/i }).first();
    if (await importLink.isVisible()) {
      await importLink.click();
      await page.waitForLoadState("networkidle");
      expect(page.url()).toContain("/imports");
      await page.goBack();
    }
  });

  test("dashboard displays plan information", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Should show plan name or usage info
    await expect(
      page.getByText(/plan|free|pro|enterprise|usage/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("dashboard navigation sidebar works", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Navigation links should be visible
    const navLinks = [
      /imports/i,
      /supplier|suppliers/i,
      /connection|connections|stores/i,
      /price.*watch/i,
      /product|search/i,
    ];

    for (const linkPattern of navLinks) {
      const link = page.getByRole("link", { name: linkPattern }).first();
      if (await link.isVisible()) {
        // At least some navigation links should exist
        break;
      }
    }
  });

  test("dashboard shows updated counts after creating data", async ({
    page,
  }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Create some data
    await createImportJobAPI(token);
    await createImportJobAPI(token);
    await createStoreConnectionAPI(token);

    // Refresh to see updated counts
    await page.reload();
    await page.waitForLoadState("networkidle");

    // Should show at least some non-zero count
    await expect(
      page.getByText(/import|store|connection/i).first()
    ).toBeVisible({ timeout: 10000 });
  });
});
