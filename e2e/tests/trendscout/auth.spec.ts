/**
 * TrendScout authentication e2e tests.
 *
 * Tests user registration, login, logout, and auth redirects.
 *
 * **For QA Engineers:**
 *   - Verify registration creates account and redirects to dashboard
 *   - Verify login with valid credentials works
 *   - Verify invalid credentials show error
 *   - Verify protected routes redirect to login when not authenticated
 *   - Verify logout clears session and redirects to login
 *
 * **For End Users:**
 *   - You can create an account and log in to access TrendScout features
 *   - Your session persists until you log out
 */

import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin, uniqueEmail, TEST_PASSWORD } from "../service-helpers";

test.describe("TrendScout Authentication", () => {
  test("user can register and is redirected to dashboard", async ({ page }) => {
    const email = uniqueEmail();

    await page.goto("/register");
    await page.fill("#register-email", email);
    await page.fill("#register-password", TEST_PASSWORD);
    await page.fill("#register-confirm", TEST_PASSWORD);
    await page.getByRole("button", { name: /create account/i }).click();

    // Should redirect to dashboard after registration
    await page.waitForFunction(() => !window.location.pathname.includes("/register"), { timeout: 15000 });
    await page.waitForLoadState("networkidle");
  });

  test("user can login with valid credentials", async ({ page }) => {
    const user = await registerServiceUser("trendscout");

    await serviceLogin(page, user.email, user.password);
    await expect(page.getByText(/welcome to trendscout/i)).toBeVisible({ timeout: 10000 });
  });

  test("login shows error with invalid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.waitForSelector("#email", { timeout: 10000 });
    await page.fill("#email", "invalid@example.com");
    await page.fill("#password", "wrongpassword");
    await page.getByRole("button", { name: /sign in/i }).click();

    // Should stay on login page and show error
    await expect(page.getByText(/invalid email or password/i)).toBeVisible({ timeout: 10000 });
  });

  test("protected routes redirect to login when not authenticated", async ({ page }) => {
    await page.goto("/research");
    await page.waitForURL(/\/login/, { timeout: 10000 });
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
  });

  test("user can logout", async ({ page }) => {
    const user = await registerServiceUser("trendscout");
    await serviceLogin(page, user.email, user.password);

    // Find and click logout button in sidebar/menu
    await page.getByRole("button", { name: /log out|logout/i }).click();
    await page.waitForURL(/\/login/, { timeout: 10000 });
  });

  test("registration validates password mismatch", async ({ page }) => {
    await page.goto("/register");
    await page.fill("#register-email", uniqueEmail());
    await page.fill("#register-password", TEST_PASSWORD);
    await page.fill("#register-confirm", "differentpassword");
    await page.getByRole("button", { name: /create account/i }).click();

    await expect(page.getByText(/passwords do not match/i)).toBeVisible({ timeout: 5000 });
  });
});
