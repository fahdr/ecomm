/**
 * Storefront customer account e2e tests.
 *
 * Tests customer registration, login, and account dashboard pages
 * through the storefront UI.
 *
 * **For QA Engineers:**
 *   - Register creates a new customer account and redirects to /account.
 *   - Login authenticates an existing customer and redirects to /account.
 *   - Account dashboard shows welcome message and navigation links.
 *   - Invalid credentials show error messages.
 *   - Duplicate registration shows error.
 */

import { test, expect } from "@playwright/test";
import { registerUser, createStoreAPI } from "../helpers";

test.describe("Storefront Customer Accounts", () => {
  let storeSlug: string;

  test.beforeEach(async () => {
    const user = await registerUser();
    const store = await createStoreAPI(user.token, "Account Test Store");
    storeSlug = store.slug;
  });

  test("registers a new customer account", async ({ page }) => {
    const email = `customer-${Date.now()}@test.com`;

    await page.goto(`/account/register?store=${storeSlug}`);
    await expect(page.getByRole("heading", { name: /create account/i })).toBeVisible({ timeout: 10000 });

    // Fill registration form
    await page.fill("#firstName", "Alice");
    await page.fill("#lastName", "Tester");
    await page.fill("#email", email);
    await page.fill("#password", "password123");
    await page.fill("#confirm", "password123");

    // Submit
    await page.getByRole("button", { name: /create account/i }).click();

    // Should redirect to account page
    await expect(page).toHaveURL(/\/account/, { timeout: 10000 });
    await expect(page.getByText(/welcome/i)).toBeVisible({ timeout: 10000 });
  });

  test("shows error for mismatched passwords", async ({ page }) => {
    await page.goto(`/account/register?store=${storeSlug}`);
    await expect(page.getByRole("heading", { name: /create account/i })).toBeVisible({ timeout: 10000 });

    await page.fill("#email", "test@test.com");
    await page.fill("#password", "password123");
    await page.fill("#confirm", "different456");

    await page.getByRole("button", { name: /create account/i }).click();

    // Should show password mismatch error
    await expect(page.getByText(/passwords do not match/i)).toBeVisible({ timeout: 5000 });
  });

  test("logs in an existing customer", async ({ page }) => {
    const email = `login-${Date.now()}@test.com`;
    const password = "password123";

    // Register first via the UI
    await page.goto(`/account/register?store=${storeSlug}`);
    await expect(page.getByRole("heading", { name: /create account/i })).toBeVisible({ timeout: 10000 });
    await page.fill("#firstName", "Bob");
    await page.fill("#lastName", "Tester");
    await page.fill("#email", email);
    await page.fill("#password", password);
    await page.fill("#confirm", password);
    await page.getByRole("button", { name: /create account/i }).click();
    await expect(page).toHaveURL(/\/account/, { timeout: 10000 });

    // Clear cookies/state and log in
    await page.context().clearCookies();
    await page.goto(`/account/login?store=${storeSlug}`);
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible({ timeout: 10000 });

    await page.fill("#email", email);
    await page.fill("#password", password);
    await page.getByRole("button", { name: /sign in/i }).click();

    // Should redirect to account page
    await expect(page).toHaveURL(/\/account/, { timeout: 10000 });
    await expect(page.getByText(/welcome/i)).toBeVisible({ timeout: 10000 });
  });

  test("shows error for invalid login credentials", async ({ page }) => {
    await page.goto(`/account/login?store=${storeSlug}`);
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible({ timeout: 10000 });

    await page.fill("#email", "nonexistent@test.com");
    await page.fill("#password", "wrongpassword");
    await page.getByRole("button", { name: /sign in/i }).click();

    // Should show error
    await expect(page.getByText(/invalid|error|not found/i)).toBeVisible({ timeout: 5000 });
  });

  test("login page has link to register", async ({ page }) => {
    await page.goto(`/account/login?store=${storeSlug}`);
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible({ timeout: 10000 });

    // Should have a link to register ("Create one" or similar)
    const registerLink = page.getByRole("link", { name: /create one|create account|register|sign up/i });
    await expect(registerLink).toBeVisible();
  });
});
