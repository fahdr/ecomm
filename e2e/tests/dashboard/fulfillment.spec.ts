/**
 * Dashboard order fulfillment e2e tests.
 *
 * Tests the full order fulfillment lifecycle through the dashboard UI:
 * marking orders as paid, fulfilling with tracking info, and delivering.
 *
 * **For QA Engineers:**
 *   - Paid orders show fulfillment form with tracking number input.
 *   - "Mark as Shipped" transitions order to shipped status.
 *   - Shipped orders display tracking info and "Mark as Delivered" button.
 *   - Delivered orders show a completion state with timestamps.
 */

import { test, expect } from "@playwright/test";
import {
  registerUser,
  dashboardLogin,
  createStoreAPI,
  createProductAPI,
  createOrderAPI,
  updateOrderStatusAPI,
} from "../helpers";

const API_BASE = "http://localhost:8000";

test.describe("Dashboard Order Fulfillment", () => {
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

  test("shows fulfillment form for paid orders", async ({ page }) => {
    // Create order and mark as paid
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    const checkout = await createOrderAPI(storeSlug, "fulfill@example.com", [
      { product_id: product.id, variant_id: variantId, quantity: 1 },
    ]);
    await updateOrderStatusAPI(token, storeId, checkout.order_id, "paid");

    // Navigate to order detail
    await page.goto(`/stores/${storeId}/orders/${checkout.order_id}`);
    await expect(page.getByText("Fulfillment", { exact: true })).toBeVisible({ timeout: 10000 });

    // Should show tracking number input for paid orders
    await expect(page.getByLabel(/tracking number/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /mark as shipped/i })).toBeVisible();
  });

  test("fulfills order with tracking number", async ({ page }) => {
    // Create order and mark as paid
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    const checkout = await createOrderAPI(storeSlug, "ship@example.com", [
      { product_id: product.id, variant_id: variantId, quantity: 1 },
    ]);
    await updateOrderStatusAPI(token, storeId, checkout.order_id, "paid");

    // Navigate to order detail
    await page.goto(`/stores/${storeId}/orders/${checkout.order_id}`);
    await expect(page.getByText("Fulfillment", { exact: true })).toBeVisible({ timeout: 10000 });

    // Fill tracking info
    await page.fill("#tracking", "1Z999AA10123456784");
    await page.fill("#carrier", "UPS");

    // Click ship button
    await page.getByRole("button", { name: /mark as shipped/i }).click();

    // Should show updated status and tracking info
    await expect(page.getByText("Updated!")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("1Z999AA10123456784")).toBeVisible({ timeout: 5000 });
  });

  test("delivers a shipped order", async ({ page }) => {
    // Create order, mark paid, then fulfill via API
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    const checkout = await createOrderAPI(storeSlug, "deliver@example.com", [
      { product_id: product.id, variant_id: variantId, quantity: 1 },
    ]);
    await updateOrderStatusAPI(token, storeId, checkout.order_id, "paid");

    // Wait for status update to commit before fulfilling
    await new Promise((r) => setTimeout(r, 500));

    // Fulfill via API to get to shipped state (retry for race condition)
    for (let attempt = 0; attempt < 5; attempt++) {
      const fulfillRes = await fetch(
        `${API_BASE}/api/v1/stores/${storeId}/orders/${checkout.order_id}/fulfill`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            tracking_number: "TRACK123",
            carrier: "FedEx",
          }),
        }
      );
      if (fulfillRes.ok) break;
      if (attempt < 4) {
        await new Promise((r) => setTimeout(r, 300));
        continue;
      }
      throw new Error(`Fulfill failed: ${fulfillRes.status} ${await fulfillRes.text()}`);
    }

    // Navigate to order detail
    await page.goto(`/stores/${storeId}/orders/${checkout.order_id}`);
    await expect(page.getByText("Fulfillment", { exact: true })).toBeVisible({ timeout: 10000 });

    // Should show tracking info and deliver button
    await expect(page.getByText("TRACK123")).toBeVisible();
    await expect(page.getByRole("button", { name: /mark as delivered/i })).toBeVisible();

    // Click deliver
    await page.getByRole("button", { name: /mark as delivered/i }).click();

    // Should show delivered state
    await expect(page.getByText("Updated!")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("Order Delivered")).toBeVisible({ timeout: 5000 });
  });

  test("shows shipping address on order detail", async ({ page }) => {
    // Create order with shipping address
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    const checkout = await createOrderAPI(storeSlug, "address@example.com", [
      { product_id: product.id, variant_id: variantId, quantity: 1 },
    ]);

    // Navigate to order detail
    await page.goto(`/stores/${storeId}/orders/${checkout.order_id}`);
    await expect(page.getByText("Order Details")).toBeVisible({ timeout: 10000 });

    // Should show shipping address (from TEST_SHIPPING_ADDRESS default)
    await expect(page.getByText("Shipping Address")).toBeVisible();
    await expect(page.getByText("123 Test Street")).toBeVisible();
    await expect(page.getByText("Testville")).toBeVisible();
  });

  test("pending order shows awaiting payment message", async ({ page }) => {
    // Create order (pending status by default)
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    const checkout = await createOrderAPI(storeSlug, "pending@example.com", [
      { product_id: product.id, variant_id: variantId, quantity: 1 },
    ]);

    // Navigate to order detail
    await page.goto(`/stores/${storeId}/orders/${checkout.order_id}`);
    await expect(page.getByText("Fulfillment", { exact: true })).toBeVisible({ timeout: 10000 });

    // Should show awaiting payment message
    await expect(page.getByText(/awaiting payment/i)).toBeVisible();
  });
});
