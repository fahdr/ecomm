/**
 * Storefront customer authentication e2e tests.
 *
 * Tests customer registration, login, profile management, order history,
 * and wishlist functionality on the storefront.
 *
 * **For QA Engineers:**
 *   - Customer registration creates an account and redirects to /account.
 *   - Login with valid credentials redirects to /account.
 *   - Logged-in customers see their name in the header.
 *   - Account page shows order history and wishlist links.
 *   - Order history shows orders placed by the customer.
 *   - Wishlist shows saved products with remove functionality.
 *   - Guest users are redirected to /login when accessing /account.
 */

import { test, expect } from "@playwright/test";
import {
  registerUser,
  createStoreAPI,
  createProductAPI,
  registerCustomerAPI,
  checkoutAsCustomerAPI,
  TEST_PASSWORD,
} from "../helpers";

test.describe("Storefront Customer Auth", () => {
  let storeSlug: string;
  let storeId: string;

  test.beforeEach(async () => {
    const user = await registerUser();
    const store = await createStoreAPI(user.token, "Customer Auth Store");
    storeSlug = store.slug;
    storeId = store.id;
  });

  test("registers a new customer and redirects to account", async ({ page }) => {
    await page.goto(`/register?store=${storeSlug}`);
    await expect(page.getByRole("heading", { name: /create account/i })).toBeVisible({ timeout: 15000 });

    await page.fill("#reg-first-name", "Jane");
    await page.fill("#reg-last-name", "Doe");
    await page.fill("#reg-email", `customer-${Date.now()}@example.com`);
    await page.fill("#reg-password", TEST_PASSWORD);
    await page.getByRole("button", { name: /create account/i }).click();

    await expect(page).toHaveURL(/\/account/, { timeout: 15000 });
    await expect(page.getByRole("heading", { name: /my account/i })).toBeVisible({ timeout: 10000 });
  });

  test("logs in an existing customer", async ({ page }) => {
    const customer = await registerCustomerAPI(storeSlug);

    await page.goto(`/login?store=${storeSlug}`);
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible({ timeout: 15000 });

    await page.fill("#login-email", customer.email);
    await page.fill("#login-password", customer.password);
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/account/, { timeout: 15000 });
    await expect(page.getByRole("heading", { name: /my account/i })).toBeVisible({ timeout: 10000 });
  });

  test("shows error for wrong password", async ({ page }) => {
    const customer = await registerCustomerAPI(storeSlug);

    await page.goto(`/login?store=${storeSlug}`);
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible({ timeout: 15000 });

    await page.fill("#login-email", customer.email);
    await page.fill("#login-password", "wrongpassword");
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page.getByText(/invalid/i)).toBeVisible({ timeout: 5000 });
  });

  test("redirects guest to login when accessing account", async ({ page }) => {
    await page.goto(`/account?store=${storeSlug}`);
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
  });

  test("header shows customer name when logged in", async ({ page }) => {
    const customer = await registerCustomerAPI(storeSlug);

    await page.goto(`/login?store=${storeSlug}`);
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible({ timeout: 15000 });

    await page.fill("#login-email", customer.email);
    await page.fill("#login-password", customer.password);
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/account/, { timeout: 15000 });
    // Header shows first name "Test" from registerCustomerAPI — use the header nav link
    await expect(page.locator("header").getByText("Test")).toBeVisible({ timeout: 5000 });
  });

  test("sign out clears session", async ({ page }) => {
    const customer = await registerCustomerAPI(storeSlug);

    await page.goto(`/login?store=${storeSlug}`);
    await page.fill("#login-email", customer.email);
    await page.fill("#login-password", customer.password);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/account/, { timeout: 15000 });
    // Wait for account page to fully render
    await expect(page.getByRole("heading", { name: /my account/i })).toBeVisible({ timeout: 10000 });

    // Click Sign Out (use first match — header or account page both work)
    await page.getByRole("button", { name: /sign out/i }).first().click();
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });

    // Trying to access account redirects to login
    await page.goto(`/account?store=${storeSlug}`);
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
  });
});

test.describe("Storefront Customer Orders", () => {
  let storeSlug: string;
  let storeId: string;
  let productId: string;

  test.beforeEach(async () => {
    const user = await registerUser();
    const store = await createStoreAPI(user.token, "Order History Store");
    storeSlug = store.slug;
    storeId = store.id;

    const product = await createProductAPI(user.token, store.id, {
      title: "Order Test Product",
      price: "19.99",
    });
    productId = product.id;
  });

  test("shows empty order history for new customer", async ({ page }) => {
    const customer = await registerCustomerAPI(storeSlug);

    await page.goto(`/login?store=${storeSlug}`);
    await page.fill("#login-email", customer.email);
    await page.fill("#login-password", customer.password);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/account/, { timeout: 15000 });

    await page.goto(`/account/orders?store=${storeSlug}`);
    await expect(page.getByText(/no orders yet/i)).toBeVisible({ timeout: 10000 });
  });

  test("shows orders after checkout", async ({ page }) => {
    const customer = await registerCustomerAPI(storeSlug);

    // Create order via API
    await checkoutAsCustomerAPI(
      storeSlug,
      customer.accessToken,
      [{ product_id: productId, quantity: 1 }],
      customer.email
    );

    // Login and check orders
    await page.goto(`/login?store=${storeSlug}`);
    await page.fill("#login-email", customer.email);
    await page.fill("#login-password", customer.password);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/account/, { timeout: 15000 });

    await page.goto(`/account/orders?store=${storeSlug}`);
    await expect(page.getByText(/\$19\.99/)).toBeVisible({ timeout: 10000 });
  });

  test("views order detail", async ({ page }) => {
    const customer = await registerCustomerAPI(storeSlug);

    const checkout = await checkoutAsCustomerAPI(
      storeSlug,
      customer.accessToken,
      [{ product_id: productId, quantity: 2 }],
      customer.email
    );

    await page.goto(`/login?store=${storeSlug}`);
    await page.fill("#login-email", customer.email);
    await page.fill("#login-password", customer.password);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/account/, { timeout: 15000 });

    await page.goto(`/account/orders?store=${storeSlug}`);
    // Click the order
    await page.locator("a[href*='/account/orders/']").first().click();
    await expect(page.getByText(/Order Test Product/)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Qty: 2/)).toBeVisible();
  });
});

test.describe("Storefront Customer Wishlist", () => {
  let storeSlug: string;
  let storeId: string;
  let productSlug: string;
  let productId: string;

  test.beforeEach(async () => {
    const user = await registerUser();
    const store = await createStoreAPI(user.token, "Wishlist Store");
    storeSlug = store.slug;
    storeId = store.id;

    const product = await createProductAPI(user.token, store.id, {
      title: "Wishlist Widget",
      price: "49.99",
    });
    productSlug = product.slug;
    productId = product.id;
  });

  test("shows empty wishlist for new customer", async ({ page }) => {
    const customer = await registerCustomerAPI(storeSlug);

    await page.goto(`/login?store=${storeSlug}`);
    await page.fill("#login-email", customer.email);
    await page.fill("#login-password", customer.password);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/account/, { timeout: 15000 });

    await page.goto(`/account/wishlist?store=${storeSlug}`);
    await expect(page.getByText(/your wishlist is empty/i)).toBeVisible({ timeout: 10000 });
  });

  test("adds product to wishlist from product page", async ({ page }) => {
    const customer = await registerCustomerAPI(storeSlug);

    // Login first
    await page.goto(`/login?store=${storeSlug}`);
    await page.fill("#login-email", customer.email);
    await page.fill("#login-password", customer.password);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/account/, { timeout: 15000 });

    // Go to product page and click wishlist button
    await page.goto(`/products/${productSlug}?store=${storeSlug}`);
    await expect(page.getByRole("heading", { name: /Wishlist Widget/ })).toBeVisible({ timeout: 15000 });

    // Click the heart/wishlist button
    await page.getByTitle(/add to wishlist/i).click();
    // Wait for it to toggle to "Remove from wishlist"
    await expect(page.getByTitle(/remove from wishlist/i)).toBeVisible({ timeout: 5000 });

    // Verify on wishlist page
    await page.goto(`/account/wishlist?store=${storeSlug}`);
    await expect(page.getByText(/Wishlist Widget/)).toBeVisible({ timeout: 10000 });
  });

  test("removes product from wishlist page", async ({ page }) => {
    const customer = await registerCustomerAPI(storeSlug);

    // Add to wishlist via API
    await fetch(
      `http://localhost:8000/api/v1/public/stores/${storeSlug}/account/wishlist`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${customer.accessToken}`,
        },
        body: JSON.stringify({ product_id: productId }),
      }
    );

    // Login and go to wishlist
    await page.goto(`/login?store=${storeSlug}`);
    await page.fill("#login-email", customer.email);
    await page.fill("#login-password", customer.password);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/account/, { timeout: 15000 });

    await page.goto(`/account/wishlist?store=${storeSlug}`);
    await expect(page.getByText(/Wishlist Widget/)).toBeVisible({ timeout: 10000 });

    // Click Remove
    await page.getByRole("button", { name: /remove/i }).click();
    await expect(page.getByText(/your wishlist is empty/i)).toBeVisible({ timeout: 10000 });
  });
});
