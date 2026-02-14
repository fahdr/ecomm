/**
 * ContentForge authentication e2e tests.
 *
 * Tests user registration, login, logout, and auth redirects.
 *
 * **For QA Engineers:**
 *   - Verify registration creates account and redirects to dashboard
 *   - Verify login with valid credentials works
 *   - Verify invalid credentials show error
 *   - Verify protected routes redirect to login
 *
 * **For End Users:**
 *   - Create an account to access AI content generation features
 */

import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin, uniqueEmail, TEST_PASSWORD } from "../service-helpers";

test.describe("ContentForge Authentication", () => {
  test("user can register and is redirected to dashboard", async ({ page }) => {
    const email = uniqueEmail();

    await page.goto("/register");
    await page.fill("#register-email", email);
    await page.fill("#register-password", TEST_PASSWORD);
    await page.fill("#register-confirm", TEST_PASSWORD);
    await page.getByRole("button", { name: /create account/i }).click();

    await page.waitForFunction(() => !window.location.pathname.includes("/register"), { timeout: 15000 });
    await page.waitForLoadState("networkidle");
  });

  test("user can login with valid credentials", async ({ page }) => {
    const user = await registerServiceUser("contentforge");

    await serviceLogin(page, user.email, user.password);
    await expect(page.getByText(/welcome to contentforge/i)).toBeVisible({ timeout: 10000 });
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
    await page.goto("/content");
    await page.waitForURL(/\/login/, { timeout: 10000 });
  });

  test("user can logout", async ({ page }) => {
    const user = await registerServiceUser("contentforge");
    await serviceLogin(page, user.email, user.password);

    await page.getByRole("button", { name: /log out|logout/i }).click();
    await page.waitForURL(/\/login/, { timeout: 10000 });
  });
});
