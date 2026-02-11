/**
 * Dashboard order management e2e tests.
 *
 * Tests order listing and status update flows. Orders are created
 * via the API to focus tests on the dashboard UI.
 *
 * **For QA Engineers:**
 *   - Orders list shows all orders with status badges.
 *   - Order detail page shows items, totals, and customer info.
 *   - Status can be updated via dropdown.
 *   - Status filter narrows the order list.
 */

import { test, expect } from "@playwright/test";
import {
  registerUser,
  dashboardLogin,
  createStoreAPI,
  createProductAPI,
  createOrderAPI,
} from "../helpers";

test.describe("Dashboard Order Management", () => {
  let email: string;
  let password: string;
  let token: string;
  let storeId: string;
  let storeSlug: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    email = user.email;
    password = user.password;
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    storeSlug = store.slug;
    await dashboardLogin(page, email, password);
  });

  test("shows empty orders state", async ({ page }) => {
    await page.goto(`/stores/${storeId}/orders`);
    await expect(page.getByText(/no orders yet/i)).toBeVisible({ timeout: 10000 });
  });

  test("lists orders after checkout", async ({ page }) => {
    // Create product and order via API
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    await createOrderAPI(storeSlug, "customer@example.com", [
      { product_id: product.id, variant_id: variantId, quantity: 2 },
    ]);

    await page.goto(`/stores/${storeId}/orders`);
    await expect(page.getByText("customer@example.com")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/pending/i)).toBeVisible();
  });

  test("views order detail", async ({ page }) => {
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    await createOrderAPI(storeSlug, "customer@example.com", [
      { product_id: product.id, variant_id: variantId, quantity: 2 },
    ]);

    await page.goto(`/stores/${storeId}/orders`);
    await expect(page.getByText("customer@example.com")).toBeVisible({ timeout: 10000 });

    // Click on the order
    await page.getByText("customer@example.com").click();
    await expect(page).toHaveURL(/\/orders\/[a-f0-9-]+/, { timeout: 5000 });

    // Check order details are visible
    await expect(page.getByText("customer@example.com")).toBeVisible();
    await expect(page.getByText("Order Details")).toBeVisible();
    await expect(page.getByText(/items/i)).toBeVisible();
  });

  test("updates order status", async ({ page }) => {
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    await createOrderAPI(storeSlug, "customer@example.com", [
      { product_id: product.id, variant_id: variantId, quantity: 2 },
    ]);

    await page.goto(`/stores/${storeId}/orders`);
    await expect(page.getByText("customer@example.com")).toBeVisible({ timeout: 10000 });
    await page.getByText("customer@example.com").click();
    await expect(page).toHaveURL(/\/orders\/[a-f0-9-]+/, { timeout: 5000 });

    // Update status to shipped via the .w-48 select trigger
    await page.locator(".w-48").click();
    await page.getByRole("option", { name: /shipped/i }).click();

    await expect(page.getByText("Updated!")).toBeVisible({ timeout: 5000 });
  });

  test("filters orders by status", async ({ page }) => {
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    await createOrderAPI(storeSlug, "customer@example.com", [
      { product_id: product.id, variant_id: variantId, quantity: 2 },
    ]);

    await page.goto(`/stores/${storeId}/orders`);
    await expect(page.getByText("customer@example.com")).toBeVisible({ timeout: 10000 });

    // Filter to paid (should show nothing since order is pending)
    await page.locator(".w-40").click();
    await page.getByRole("option", { name: /^paid$/i }).click();

    await expect(page.getByText(/no orders yet/i)).toBeVisible({ timeout: 5000 });
  });
});
