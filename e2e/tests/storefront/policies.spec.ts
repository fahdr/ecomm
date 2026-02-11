/**
 * Storefront policy pages e2e tests.
 *
 * Tests that all policy pages render correctly with proper headings,
 * breadcrumbs, and content sections.
 *
 * **For QA Engineers:**
 *   - Valid policy slugs: shipping, returns, privacy, terms.
 *   - Invalid slugs show "Policy not found".
 *   - Each page shows a title heading and at least one content section.
 *   - Breadcrumbs link back to home.
 */

import { test, expect } from "@playwright/test";
import { registerUser, createStoreAPI } from "../helpers";

test.describe("Storefront Policy Pages", () => {
  let storeSlug: string;

  test.beforeEach(async () => {
    const user = await registerUser();
    const store = await createStoreAPI(user.token, "Policy Test Store");
    storeSlug = store.slug;
  });

  test("shows shipping policy page", async ({ page }) => {
    await page.goto(`/policies/shipping?store=${storeSlug}`);
    await expect(page.getByRole("heading", { name: /shipping policy/i })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/processing time/i)).toBeVisible();
  });

  test("shows returns policy page", async ({ page }) => {
    await page.goto(`/policies/returns?store=${storeSlug}`);
    await expect(page.getByRole("heading", { name: /returns policy/i })).toBeVisible({ timeout: 10000 });
  });

  test("shows privacy policy page", async ({ page }) => {
    await page.goto(`/policies/privacy?store=${storeSlug}`);
    await expect(page.getByRole("heading", { name: /privacy policy/i })).toBeVisible({ timeout: 10000 });
  });

  test("shows terms and conditions page", async ({ page }) => {
    await page.goto(`/policies/terms?store=${storeSlug}`);
    await expect(page.getByRole("heading", { name: /terms.*conditions/i })).toBeVisible({ timeout: 15000 });
  });

  test("shows not found for invalid policy slug", async ({ page }) => {
    await page.goto(`/policies/nonexistent?store=${storeSlug}`);
    await expect(page.getByText(/policy not found|not found/i)).toBeVisible({ timeout: 10000 });
  });

  test("breadcrumb links back to home", async ({ page }) => {
    await page.goto(`/policies/shipping?store=${storeSlug}`);
    await expect(page.getByRole("heading", { name: /shipping policy/i })).toBeVisible({ timeout: 10000 });

    // Breadcrumb should have a "Home" link
    const homeLink = page.getByRole("link", { name: /home/i });
    await expect(homeLink).toBeVisible();
  });
});
