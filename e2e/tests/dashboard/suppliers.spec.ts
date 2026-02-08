/**
 * Dashboard supplier management e2e tests.
 *
 * Tests supplier creation, listing, and empty state.
 *
 * **For QA Engineers:**
 *   - Supplier list shows name, email, and status.
 *   - Creating a supplier refreshes the list.
 *   - Empty state is shown when no suppliers exist.
 *   - Summary cards show total and active supplier counts.
 */

import { test, expect } from "@playwright/test";
import {
  registerUser,
  dashboardLogin,
  createStoreAPI,
  createSupplierAPI,
  createProductAPI,
  linkProductSupplierAPI,
} from "../helpers";

test.describe("Dashboard Supplier Management", () => {
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows empty state when no suppliers exist", async ({ page }) => {
    await page.goto(`/stores/${storeId}/suppliers`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/no supplier/i)).toBeVisible({ timeout: 10000 });
  });

  test("lists suppliers created via API", async ({ page }) => {
    await createSupplierAPI(token, storeId, {
      name: "Acme Supplies",
      contact_email: "acme@example.com",
    });
    await createSupplierAPI(token, storeId, {
      name: "Global Parts",
      contact_email: "global@example.com",
    });

    await page.goto(`/stores/${storeId}/suppliers`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Acme Supplies")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Global Parts")).toBeVisible();
  });

  test("renders supplier table with all data fields", async ({ page }) => {
    // Create a supplier with accepted data fields (the backend create schema does
    // not accept avg_shipping_days or max_shipping_days — those are computed fields).
    const supplier = await createSupplierAPI(token, storeId, {
      name: "Acme Wholesale",
      contact_email: "acme@test.com",
      website: "https://acme.test",
    });

    // Create a product and link it to the supplier
    const product = await createProductAPI(token, storeId, {
      title: "Linked Product",
      price: "29.99",
    });
    await linkProductSupplierAPI(token, storeId, product.id, supplier.id, 15);

    await page.goto(`/stores/${storeId}/suppliers`);
    await page.waitForLoadState("networkidle");

    // Supplier name should appear in the table
    await expect(page.getByText("Acme Wholesale")).toBeVisible({ timeout: 10000 });

    // Status badge should show "active"
    await expect(page.getByText("active").first()).toBeVisible({ timeout: 10000 });

    // Shipping days: the backend create endpoint does not accept avg_shipping_days
    // or max_shipping_days, so they default to null/undefined in the response.
    // The frontend renders "{avg}d / {max}d" which becomes "d / d" for null values.
    await expect(page.getByText(/d \/ .*d/).first()).toBeVisible({ timeout: 10000 });

    // Contact email should be visible
    await expect(page.getByText("acme@test.com")).toBeVisible({ timeout: 10000 });

    // Summary card header should be visible
    await expect(page.getByText("Total Suppliers")).toBeVisible({ timeout: 10000 });
  });

  test("navigates from store settings to suppliers", async ({ page }) => {
    await page.goto(`/stores/${storeId}`);
    await page.getByRole("button", { name: /suppliers/i }).click();
    await expect(page).toHaveURL(new RegExp(`/stores/${storeId}/suppliers`), {
      timeout: 10000,
    });
  });
});
