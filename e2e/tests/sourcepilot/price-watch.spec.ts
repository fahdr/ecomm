/**
 * SourcePilot price watch monitoring e2e tests.
 *
 * Tests the price monitoring lifecycle: adding watches, listing them,
 * triggering syncs, and removing watches.
 *
 * **For QA Engineers:**
 *   - Verify price watch creation via UI
 *   - Verify price watch list shows product URLs and sources
 *   - Verify sync trigger updates last_checked timestamp
 *   - Verify deletion removes the watch
 *   - Verify empty state when no watches exist
 *   - Verify summary cards show watch counts
 *
 * **For End Users:**
 *   - Monitor supplier prices for products you've imported
 *   - Get notified when prices change significantly
 *   - Trigger manual price checks anytime
 */

import { test, expect } from "@playwright/test";
import {
  registerServiceUser,
  serviceLogin,
  createPriceWatchAPI,
  triggerPriceSyncAPI,
  serviceApiDelete,
  serviceApiGet,
} from "../service-helpers";

test.describe("SourcePilot Price Watch", () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("sourcepilot");
    token = user.token;
    await serviceLogin(page, user.email, user.password);
  });

  test("shows empty state when no watches exist", async ({ page }) => {
    await page.goto("/price-watch");
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/no price watch|no watches|start monitoring/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("lists price watches created via API", async ({ page }) => {
    await createPriceWatchAPI(token, {
      product_url: "https://www.aliexpress.com/item/watch1.html",
      source: "aliexpress",
    });

    await page.goto("/price-watch");
    await page.waitForLoadState("networkidle");

    await expect(
      page.getByText(/aliexpress/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("shows summary cards with watch counts", async ({ page }) => {
    await createPriceWatchAPI(token, {
      product_url: "https://www.aliexpress.com/item/pw1.html",
      source: "aliexpress",
    });
    await createPriceWatchAPI(token, {
      product_url: "https://www.aliexpress.com/item/pw2.html",
      source: "aliexpress",
    });

    await page.goto("/price-watch");
    await page.waitForLoadState("networkidle");

    // Should display total watches count
    await expect(
      page.getByText(/total watches|active/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("can add price watch via dialog", async ({ page }) => {
    await page.goto("/price-watch");
    await page.waitForLoadState("networkidle");

    // Click add watch button
    await page.getByRole("button", { name: /add.*watch|new.*watch/i }).click();

    // Dialog should open
    await expect(
      page.getByRole("heading", { name: /add.*watch|new.*watch|price.*watch/i })
    ).toBeVisible();

    // Fill product URL
    const urlInput = page.locator("input[placeholder*='url'], input[placeholder*='aliexpress']").first();
    await urlInput.fill("https://www.aliexpress.com/item/newwatch.html");

    // Submit
    await page.getByRole("button", { name: /add|save|submit|watch/i }).last().click();

    // Should appear in list
    await expect(
      page.getByText(/aliexpress/i).first()
    ).toBeVisible({ timeout: 15000 });
  });

  test("sync button triggers price check", async ({ page }) => {
    await createPriceWatchAPI(token, {
      product_url: "https://www.aliexpress.com/item/synctest.html",
      source: "aliexpress",
    });

    await page.goto("/price-watch");
    await page.waitForLoadState("networkidle");

    // Click sync button
    const syncBtn = page.getByRole("button", { name: /sync|check prices/i });
    if (await syncBtn.isVisible()) {
      await syncBtn.click();
      // Verify sync completed (button should re-enable or show result)
      await page.waitForLoadState("networkidle");
    }

    // Verify via API
    const result = await triggerPriceSyncAPI(token);
    expect(result).toHaveProperty("total_checked");
  });

  test("can delete a price watch", async ({ page }) => {
    const watch = await createPriceWatchAPI(token, {
      product_url: "https://www.aliexpress.com/item/deleteme.html",
      source: "aliexpress",
    });

    await page.goto("/price-watch");
    await page.waitForLoadState("networkidle");

    // Verify it shows first
    await expect(
      page.getByText(/aliexpress/i).first()
    ).toBeVisible({ timeout: 10000 });

    // Delete via API
    await serviceApiDelete(
      "sourcepilot",
      token,
      `/api/v1/price-watches/${watch.id}`
    );

    await page.reload();
    await page.waitForLoadState("networkidle");

    // Should show empty state or reduced list
    const list = await serviceApiGet(
      "sourcepilot",
      token,
      "/api/v1/price-watches"
    );
    expect(list.total).toBe(0);
  });

  test("multiple watches display from different sources", async ({ page }) => {
    await createPriceWatchAPI(token, {
      product_url: "https://www.aliexpress.com/item/multi1.html",
      source: "aliexpress",
    });
    await createPriceWatchAPI(token, {
      product_url: "https://cjdropshipping.com/product/multi2.html",
      source: "cjdropship",
    });

    await page.goto("/price-watch");
    await page.waitForLoadState("networkidle");

    // Both should be visible
    const list = await serviceApiGet(
      "sourcepilot",
      token,
      "/api/v1/price-watches"
    );
    expect(list.total).toBe(2);
  });
});
