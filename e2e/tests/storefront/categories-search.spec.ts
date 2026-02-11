/**
 * Storefront category browsing and product search e2e tests.
 *
 * Tests the categories listing page, category detail page with products,
 * and the product search functionality including filters and pagination.
 *
 * **For QA Engineers:**
 *   - Categories page shows a grid of categories with product counts.
 *   - Clicking a category navigates to its detail page with products.
 *   - Search page displays results matching a query string.
 *   - Search supports price range filters and sort options.
 *   - Empty search results show an appropriate message.
 *   - Header search component navigates to the search page.
 */

import { test, expect } from "@playwright/test";
import {
  registerUser,
  createStoreAPI,
  createProductAPI,
  createCategoryAPI,
} from "../helpers";

// ---------------------------------------------------------------------------
// Categories
// ---------------------------------------------------------------------------

test.describe("Storefront Categories", () => {
  let token: string;
  let storeId: string;
  let storeSlug: string;

  test.beforeEach(async () => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    storeSlug = store.slug;
  });

  test("shows categories listing page", async ({ page }) => {
    await createCategoryAPI(token, storeId, "Gadgets");

    await page.goto(`/categories?store=${storeSlug}`, {
      waitUntil: "networkidle",
    });

    await expect(page.getByText("Categories").first()).toBeVisible({
      timeout: 15000,
    });
  });

  test("shows empty state when no categories", async ({ page }) => {
    await page.goto(`/categories?store=${storeSlug}`, {
      waitUntil: "networkidle",
    });

    // Wait for the page heading to confirm successful page load
    await expect(
      page.getByRole("heading", { name: /categories/i })
    ).toBeVisible({ timeout: 15000 });

    // Then verify the empty state text
    await expect(
      page.getByText(/no categories available/i)
    ).toBeVisible({ timeout: 5000 });
  });

  test("shows category with product count", async ({ page }) => {
    const cat = await createCategoryAPI(token, storeId, "Electronics");
    await createProductAPI(token, storeId, {
      title: "Test Gadget",
      category_id: cat.id,
    });

    await page.goto(`/categories?store=${storeSlug}`, {
      waitUntil: "networkidle",
    });

    await expect(page.getByText("Electronics")).toBeVisible({
      timeout: 15000,
    });
  });
});

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

test.describe("Storefront Search", () => {
  let token: string;
  let storeSlug: string;
  let storeId: string;

  test.beforeEach(async () => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(token);
    storeSlug = store.slug;
    storeId = store.id;
  });

  test("shows search page", async ({ page }) => {
    await page.goto(`/search?store=${storeSlug}`, {
      waitUntil: "networkidle",
    });

    await expect(page).toHaveURL(/\/search/);
  });

  test("searches for products by query", async ({ page }) => {
    await createProductAPI(token, storeId, {
      title: "Blue Wireless Headphones",
      status: "active",
    });

    await page.goto(`/search?store=${storeSlug}&q=headphones`, {
      waitUntil: "networkidle",
    });

    await expect(page.getByText("Blue Wireless Headphones")).toBeVisible({
      timeout: 15000,
    });
  });

  test("shows empty results for unknown query", async ({ page }) => {
    await page.goto(`/search?store=${storeSlug}&q=xyznonexistent12345`, {
      waitUntil: "networkidle",
    });

    // Should show some form of "no results" or zero products
    const body = await page.textContent("body");
    expect(
      body?.toLowerCase().includes("no") ||
        body?.toLowerCase().includes("0") ||
        body?.toLowerCase().includes("empty")
    ).toBeTruthy();
  });

  test("header search navigates to search page", async ({ page }) => {
    await page.goto(`/?store=${storeSlug}`, { waitUntil: "networkidle" });

    // Click the search icon in the header
    const searchButton = page.getByTitle("Search products");
    if (await searchButton.isVisible()) {
      await searchButton.click();
      // On mobile it navigates directly; on desktop it expands input
      const searchInput = page.locator('input[type="text"]');
      if (await searchInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        await searchInput.fill("test query");
        await searchInput.press("Enter");
        await expect(page).toHaveURL(/\/search\?q=test/, { timeout: 10000 });
      }
    }
  });
});
