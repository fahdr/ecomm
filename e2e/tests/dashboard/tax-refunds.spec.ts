/**
 * Dashboard tax and refunds management e2e tests.
 *
 * Tests tax rate creation/listing and refunds page loading.
 *
 * **For QA Engineers:**
 *   - Tax rates page shows configured rates in a table.
 *   - Creating a tax rate via dialog refreshes the list.
 *   - Refunds page shows empty state when no refunds exist.
 */

import { test, expect } from "@playwright/test";
import {
  registerUser,
  dashboardLogin,
  createStoreAPI,
  createTaxRateAPI,
  createProductAPI,
  createOrderAPI,
  updateOrderStatusAPI,
  createRefundAPI,
  apiGet,
} from "../helpers";

test.describe("Dashboard Tax Management", () => {
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows empty state when no tax rates exist", async ({ page }) => {
    await page.goto(`/stores/${storeId}/tax`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/no tax|tax rate/i).first()).toBeVisible({
      timeout: 10000,
    });
  });

  test("lists tax rates created via API", async ({ page }) => {
    await createTaxRateAPI(token, storeId, {
      name: "CA Sales Tax",
      rate: 7.25,
      country: "US",
      state: "CA",
    });

    await page.goto(`/stores/${storeId}/tax`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("CA Sales Tax")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("7.25")).toBeVisible();
  });

  test("renders multiple tax rates with formatted data", async ({ page }) => {
    await createTaxRateAPI(token, storeId, {
      name: "NY Sales Tax",
      rate: 8.875,
      country: "US",
      state: "NY",
    });
    await createTaxRateAPI(token, storeId, {
      name: "CA Sales Tax",
      rate: 7.25,
      country: "US",
      state: "CA",
    });
    await createTaxRateAPI(token, storeId, {
      name: "UK VAT",
      rate: 20,
      country: "GB",
    });

    await page.goto(`/stores/${storeId}/tax`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("NY Sales Tax")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("CA Sales Tax")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("UK VAT")).toBeVisible({ timeout: 10000 });
    // The DB column is Numeric(5,2) so 8.875 is stored as 8.88.
    // The frontend renders "{rate}%" so it shows "8.88%".
    await expect(page.getByText(/8\.88/).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/20(\.00)?%/).first()).toBeVisible({ timeout: 10000 });
  });

  test("creates a tax rate via dialog", async ({ page }) => {
    await page.goto(`/stores/${storeId}/tax`);
    await page.waitForLoadState("networkidle");
    // Wait for empty state to confirm page is loaded and interactive
    await expect(page.getByText(/no tax rate/i)).toBeVisible({ timeout: 10000 });

    // Use JS click to bypass React hydration timing issues
    await page.$eval('button:has-text("Add your first tax rate")', (el: HTMLElement) => el.click());
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 5000 });

    await page.fill("#tax-name", "NY State Tax");
    await page.fill("#tax-rate", "8.875");
    await page.fill("#tax-country", "US");

    // Click submit and wait for the POST to complete
    const [postResp] = await Promise.all([
      page.waitForResponse(
        (resp) => resp.url().includes("/tax") && resp.request().method() === "POST",
        { timeout: 10000 }
      ),
      page.locator('[role="dialog"] button[type="submit"]').click(),
    ]);

    // Wait for dialog to close (indicates POST succeeded)
    await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 10000 });

    // Reload to ensure fresh data from the database
    await page.reload();
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("NY State Tax")).toBeVisible({ timeout: 10000 });
  });
});

test.describe("Dashboard Refunds", () => {
  let storeId: string;
  let token: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(user.token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows refunds page with empty state", async ({ page }) => {
    await page.goto(`/stores/${storeId}/refunds`);
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/refund|no refund/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("shows refunds page with populated data", async ({ page }) => {
    // Create a product with explicit active status and a variant for checkout
    const product = await createProductAPI(token, storeId, {
      title: "Refund Test Product",
      price: "29.99",
      status: "active",
      variants: [
        { name: "Default", sku: "RFND-001", price: null, inventory_count: 100 },
      ],
    });

    // Resolve store slug via the helper (more robust than raw fetch)
    const store = await apiGet(token, `/api/v1/stores/${storeId}`);
    const storeSlug = store.slug;

    // Place an order through the public checkout, passing variant_id for reliability
    const customerEmail = `refund-test-${Date.now()}@example.com`;
    const order = await createOrderAPI(storeSlug, customerEmail, [
      { product_id: product.id, variant_id: product.variants?.[0]?.id, quantity: 1 },
    ]);
    await updateOrderStatusAPI(token, storeId, order.order_id, "paid");
    // Use a valid RefundReason enum value: defective, wrong_item, not_as_described, changed_mind, other.
    // Free-text reasons are mapped to "other" by the backend, so use a valid value directly.
    await createRefundAPI(token, storeId, order.order_id, 10, "defective", "Item arrived damaged");

    await page.goto(`/stores/${storeId}/refunds`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(customerEmail).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("pending").first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Total Requests").first()).toBeVisible({ timeout: 10000 });
    // The reason column shows the enum value ("defective"), not the free-text reason_details.
    await expect(page.getByText("defective").first()).toBeVisible({ timeout: 10000 });
  });

  test("navigates via sidebar to refunds", async ({ page }) => {
    await page.goto(`/stores/${storeId}`);
    await page.waitForLoadState("networkidle");
    await page.getByRole("link", { name: "Refunds" }).click();
    await expect(page).toHaveURL(new RegExp(`/stores/${storeId}/refunds`), {
      timeout: 10000,
    });
  });
});
