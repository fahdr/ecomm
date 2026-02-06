/**
 * Dashboard product management e2e tests.
 *
 * Tests product creation, listing, and detail views.
 *
 * **For QA Engineers:**
 *   - Products can be created with title, price, and variants.
 *   - After creation, the user is redirected to the product detail page.
 *   - Product list shows all products with status badges.
 *   - Product detail page shows full product info.
 */

import { test, expect } from "@playwright/test";
import { registerUser, dashboardLogin, createStoreAPI } from "../helpers";

test.describe("Dashboard Product Management", () => {
  let email: string;
  let password: string;
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    email = user.email;
    password = user.password;
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, email, password);
  });

  test("shows empty product state", async ({ page }) => {
    await page.goto(`/stores/${storeId}/products`);
    await expect(page.getByText("0 products")).toBeVisible({ timeout: 10000 });
  });

  test("creates a new product", async ({ page }) => {
    await page.goto(`/stores/${storeId}/products/new`);
    await expect(page.getByText("Product Details")).toBeVisible({ timeout: 10000 });

    await page.fill("#title", "E2E Test Widget");
    await page.fill("#description", "A widget for testing");
    await page.fill("#price", "19.99");

    // Scroll down to find and set status to active
    await page.getByText("Status").scrollIntoViewIfNeeded();
    await page.locator("button").filter({ hasText: /draft/i }).click();
    await page.getByRole("option", { name: /active/i }).click();

    // Add a variant
    await page.getByRole("button", { name: /add variant/i }).click();
    await page.locator('input[placeholder="e.g. Large"]').first().fill("Standard");

    await page.getByRole("button", { name: /create product/i }).click();

    // Should redirect to the product detail page
    await expect(page).toHaveURL(/\/stores\/[a-f0-9-]+\/products\/[a-f0-9-]+/, { timeout: 10000 });
    await expect(page.getByText("E2E Test Widget")).toBeVisible({ timeout: 5000 });
  });

  test("lists products after creation", async ({ page }) => {
    // Create product via UI
    await page.goto(`/stores/${storeId}/products/new`);
    await expect(page.getByText("Product Details")).toBeVisible({ timeout: 10000 });

    await page.fill("#title", "Listed Widget");
    await page.fill("#price", "15.00");

    await page.getByText("Status").scrollIntoViewIfNeeded();
    await page.locator("button").filter({ hasText: /draft/i }).click();
    await page.getByRole("option", { name: /active/i }).click();

    await page.getByRole("button", { name: /add variant/i }).click();
    await page.locator('input[placeholder="e.g. Large"]').first().fill("Default");

    await page.getByRole("button", { name: /create product/i }).click();
    // Redirects to product detail page
    await expect(page).toHaveURL(/\/products\/[a-f0-9-]+/, { timeout: 10000 });

    // Navigate to product list
    await page.goto(`/stores/${storeId}/products`);
    await expect(page.getByText("Listed Widget")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("$15.00")).toBeVisible();
  });

  test("navigates to product detail from list", async ({ page }) => {
    // Create product via UI
    await page.goto(`/stores/${storeId}/products/new`);
    await expect(page.getByText("Product Details")).toBeVisible({ timeout: 10000 });

    await page.fill("#title", "Detail Widget");
    await page.fill("#price", "25.00");

    await page.getByText("Status").scrollIntoViewIfNeeded();
    await page.locator("button").filter({ hasText: /draft/i }).click();
    await page.getByRole("option", { name: /active/i }).click();

    await page.getByRole("button", { name: /add variant/i }).click();
    await page.locator('input[placeholder="e.g. Large"]').first().fill("Default");

    await page.getByRole("button", { name: /create product/i }).click();
    await expect(page).toHaveURL(/\/products\/[a-f0-9-]+/, { timeout: 10000 });

    // Go to products list
    await page.goto(`/stores/${storeId}/products`);
    await expect(page.getByText("Detail Widget")).toBeVisible({ timeout: 10000 });

    // Click on the product
    await page.getByText("Detail Widget").click();
    await expect(page).toHaveURL(/\/products\/[a-f0-9-]+/, { timeout: 5000 });
    await expect(page.getByText("Detail Widget")).toBeVisible();
  });
});
