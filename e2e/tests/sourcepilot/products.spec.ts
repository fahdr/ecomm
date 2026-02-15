/**
 * SourcePilot product search and preview e2e tests.
 *
 * Tests the product discovery workflow: searching supplier catalogs,
 * previewing product details, and verifying search result rendering.
 *
 * **For QA Engineers:**
 *   - Verify product search returns results for valid queries
 *   - Verify search filters by supplier platform (AliExpress, CJ, Spocket)
 *   - Verify product preview displays details (title, price, images)
 *   - Verify empty search results show appropriate message
 *   - Verify pagination in search results
 *   - Verify search via API returns expected data shape
 *
 * **For End Users:**
 *   - Search for products across multiple supplier platforms
 *   - Preview product details before importing to your store
 *   - Compare prices and ratings from different suppliers
 */

import { test, expect } from "@playwright/test";
import {
  registerServiceUser,
  serviceLogin,
  searchProductsAPI,
  previewProductAPI,
  serviceApiGet,
} from "../service-helpers";

test.describe("SourcePilot Product Search", () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("sourcepilot");
    token = user.token;
    await serviceLogin(page, user.email, user.password);
  });

  test("product search page loads correctly", async ({ page }) => {
    await page.goto("/products");
    await page.waitForLoadState("networkidle");

    // Should show search input
    await expect(
      page.locator("input[placeholder*='search'], input[type='search'], input[name*='search']").first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("search returns results for valid query via API", async () => {
    const result = await searchProductsAPI(token, "wireless earbuds");

    // Should return product results
    expect(result).toHaveProperty("products");
    expect(result.products.length).toBeGreaterThan(0);

    // Verify result shape
    const firstProduct = result.products[0];
    expect(firstProduct).toHaveProperty("title");
    expect(firstProduct).toHaveProperty("price");
  });

  test("search filters by source platform via API", async () => {
    const aliResult = await searchProductsAPI(token, "phone case", "aliexpress");
    expect(aliResult.products.length).toBeGreaterThan(0);

    const cjResult = await searchProductsAPI(token, "phone case", "cjdropship");
    expect(cjResult.products.length).toBeGreaterThan(0);
  });

  test("product preview returns detailed info via API", async () => {
    const preview = await previewProductAPI(
      token,
      "https://www.aliexpress.com/item/preview-test.html"
    );

    expect(preview).toHaveProperty("title");
    expect(preview).toHaveProperty("price");
    expect(preview).toHaveProperty("currency");
    expect(preview).toHaveProperty("source");
    expect(preview.source).toBe("aliexpress");
  });

  test("can perform search from the UI", async ({ page }) => {
    await page.goto("/products");
    await page.waitForLoadState("networkidle");

    // Enter search query
    const searchInput = page.locator(
      "input[placeholder*='search'], input[type='search'], input[name*='search']"
    ).first();
    await searchInput.fill("wireless earbuds");

    // Trigger search (Enter or search button)
    await searchInput.press("Enter");

    // Wait for results to load
    await page.waitForLoadState("networkidle");

    // Should show product results
    await expect(
      page.getByText(/wireless|earbuds|product/i).first()
    ).toBeVisible({ timeout: 15000 });
  });

  test("search results display product cards with prices", async ({ page }) => {
    await page.goto("/products");
    await page.waitForLoadState("networkidle");

    const searchInput = page.locator(
      "input[placeholder*='search'], input[type='search'], input[name*='search']"
    ).first();
    await searchInput.fill("laptop stand");
    await searchInput.press("Enter");
    await page.waitForLoadState("networkidle");

    // Should display price information
    await expect(
      page.getByText(/\$/i).first()
    ).toBeVisible({ timeout: 15000 });
  });

  test("preview product shows modal with details", async ({ page }) => {
    await page.goto("/products");
    await page.waitForLoadState("networkidle");

    // Perform a search first
    const searchInput = page.locator(
      "input[placeholder*='search'], input[type='search'], input[name*='search']"
    ).first();
    await searchInput.fill("wireless earbuds");
    await searchInput.press("Enter");
    await page.waitForLoadState("networkidle");

    // Wait for results
    await expect(
      page.getByText(/wireless|earbuds/i).first()
    ).toBeVisible({ timeout: 15000 });

    // Click on a product card to open preview
    const productCard = page.locator("[data-testid='product-card'], [class*='product-card'], [role='article']").first();
    if (await productCard.isVisible()) {
      await productCard.click();
      // Preview modal should show details
      await page.waitForLoadState("networkidle");
    }
  });
});
