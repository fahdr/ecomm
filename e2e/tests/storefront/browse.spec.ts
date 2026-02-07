/**
 * Storefront browsing e2e tests.
 *
 * Tests store homepage, product listing, and product detail pages.
 * A store with products is seeded via the API before each test.
 *
 * **For QA Engineers:**
 *   - Store homepage shows store name and product listing.
 *   - Product detail shows title, price, description, and variants.
 *   - Without a valid store slug, shows "store not found".
 *   - The ``?store=`` query param is required in local dev to resolve the store.
 */

import { test, expect } from "@playwright/test";
import { registerUser, createStoreAPI, createProductAPI } from "../helpers";

test.describe("Storefront Browsing", () => {
  let storeSlug: string;
  let productTitle: string;
  let productSlug: string;

  test.beforeEach(async () => {
    const user = await registerUser();
    const store = await createStoreAPI(user.token, "Browse Test Store");
    storeSlug = store.slug;

    const product = await createProductAPI(user.token, store.id, {
      title: "Browseable Widget",
      description: "A great widget for browsing tests",
      price: "49.99",
    });
    productTitle = product.title;
    productSlug = product.slug;
  });

  test("shows store not found without slug", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText(/store not found/i)).toBeVisible({ timeout: 10000 });
  });

  test("shows store homepage with products", async ({ page }) => {
    await page.goto(`/?store=${storeSlug}`, { waitUntil: "networkidle" });
    await expect(page.getByText(/welcome to/i)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(productTitle)).toBeVisible({ timeout: 15000 });
  });

  test("shows product detail page", async ({ page }) => {
    // Navigate directly with store context (client-side nav loses ?store= param)
    await page.goto(`/products/${productSlug}?store=${storeSlug}`, { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: productTitle })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("$49.99", { exact: true })).toBeVisible({ timeout: 5000 });
  });

  test("shows product description on detail page", async ({ page }) => {
    await page.goto(`/products/${productSlug}?store=${storeSlug}`, { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: productTitle })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("A great widget for browsing tests")).toBeVisible({ timeout: 10000 });
  });

  test("products page lists all products", async ({ page }) => {
    await page.goto(`/products?store=${storeSlug}`, { waitUntil: "networkidle" });
    await expect(page.getByText(productTitle)).toBeVisible({ timeout: 15000 });
  });
});
