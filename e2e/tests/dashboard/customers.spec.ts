/**
 * Dashboard customer management e2e tests.
 *
 * Tests the store owner's ability to view and manage customers
 * from the dashboard interface.
 *
 * **For QA Engineers:**
 *   - Customer list shows registered customers with search.
 *   - Customer detail shows profile and order stats.
 *   - Empty state when no customers have registered.
 *   - "View Customers" link appears on the store settings page.
 */

import { test, expect } from "@playwright/test";
import {
  registerUser,
  createStoreAPI,
  createProductAPI,
  registerCustomerAPI,
  checkoutAsCustomerAPI,
  dashboardLogin,
} from "../helpers";

test.describe("Dashboard Customer Management", () => {
  let ownerEmail: string;
  let ownerPassword: string;
  let storeId: string;
  let storeSlug: string;
  let productId: string;

  test.beforeEach(async () => {
    const user = await registerUser();
    ownerEmail = user.email;
    ownerPassword = user.password;
    const store = await createStoreAPI(user.token, "Customers Dashboard Store");
    storeId = store.id;
    storeSlug = store.slug;

    const product = await createProductAPI(user.token, store.id, {
      title: "Dashboard Product",
      price: "25.00",
    });
    productId = product.id;
  });

  test("shows Customers link on store settings page", async ({ page }) => {
    await dashboardLogin(page, ownerEmail, ownerPassword);
    await page.goto(`/stores/${storeId}`);
    await expect(page.getByRole("button", { name: /view customers/i })).toBeVisible({ timeout: 10000 });
  });

  test("shows empty customer list", async ({ page }) => {
    await dashboardLogin(page, ownerEmail, ownerPassword);
    await page.goto(`/stores/${storeId}/customers`);
    await expect(page.getByText(/no customers yet/i)).toBeVisible({ timeout: 10000 });
  });

  test("lists customers after registration", async ({ page }) => {
    // Register a customer via API
    const customer = await registerCustomerAPI(storeSlug);

    await dashboardLogin(page, ownerEmail, ownerPassword);
    await page.goto(`/stores/${storeId}/customers`);
    await expect(page.getByText(customer.email)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/1 customer/)).toBeVisible();
  });

  test("searches customers by email", async ({ page }) => {
    const customer1 = await registerCustomerAPI(storeSlug, `alpha-${Date.now()}@test.com`);
    await registerCustomerAPI(storeSlug, `beta-${Date.now()}@test.com`);

    await dashboardLogin(page, ownerEmail, ownerPassword);
    await page.goto(`/stores/${storeId}/customers`);
    await expect(page.getByText(/2 customers/)).toBeVisible({ timeout: 10000 });

    // Search for alpha
    await page.fill('input[placeholder*="Search"]', "alpha");
    await expect(page.getByText(/1 customer/)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(customer1.email)).toBeVisible();
  });

  test("views customer detail with order stats", async ({ page }) => {
    const customer = await registerCustomerAPI(storeSlug);

    // Create order for this customer
    await checkoutAsCustomerAPI(
      storeSlug,
      customer.accessToken,
      [{ product_id: productId, quantity: 2 }],
      customer.email
    );

    await dashboardLogin(page, ownerEmail, ownerPassword);
    await page.goto(`/stores/${storeId}/customers`);
    await expect(page.getByText(customer.email)).toBeVisible({ timeout: 10000 });

    // Click customer to see detail
    await page.locator(`a[href*="/customers/"]`).first().click();

    // Should see customer profile
    await expect(page.getByText(customer.email)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Test Customer")).toBeVisible(); // full name from helper

    // Should see order stats — total spent: 2 * $25.00
    await expect(page.getByText("Total Spent")).toBeVisible({ timeout: 5000 });
  });

  test("navigates from store settings to customers", async ({ page }) => {
    await dashboardLogin(page, ownerEmail, ownerPassword);
    await page.goto(`/stores/${storeId}`);

    await page.getByRole("button", { name: /view customers/i }).click();
    await expect(page).toHaveURL(new RegExp(`/stores/${storeId}/customers`), { timeout: 10000 });
    await expect(page.getByRole("heading", { name: "Customers" })).toBeVisible();
  });
});
