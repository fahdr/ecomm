/**
 * SourcePilot authentication e2e tests.
 *
 * Tests user registration, login, logout, and auth redirects for the
 * supplier product import dashboard.
 *
 * **For QA Engineers:**
 *   - Verify registration creates account and redirects to dashboard
 *   - Verify login with valid credentials shows welcome content
 *   - Verify invalid credentials display an error message
 *   - Verify protected routes redirect to login when unauthenticated
 *   - Verify logout clears the session and returns to login
 *   - Verify registration form validates password mismatch
 *
 * **For End Users:**
 *   - Create an account to start importing products from suppliers
 *   - Log in to manage your imports, stores, and price watches
 */

import { test, expect } from "@playwright/test";
import {
  registerServiceUser,
  serviceLogin,
  uniqueEmail,
  TEST_PASSWORD,
} from "../service-helpers";

test.describe("SourcePilot Authentication", () => {
  test("user can register and is redirected to dashboard", async ({ page }) => {
    const email = uniqueEmail();

    await page.goto("/register");
    await page.fill("#register-email", email);
    await page.fill("#register-password", TEST_PASSWORD);
    await page.fill("#register-confirm", TEST_PASSWORD);
    await page.getByRole("button", { name: /create account/i }).click();

    // Should redirect to dashboard after registration
    await page.waitForFunction(
      () => !window.location.pathname.includes("/register"),
      { timeout: 15000 }
    );
    await page.waitForLoadState("networkidle");
  });

  test("user can login with valid credentials", async ({ page }) => {
    const user = await registerServiceUser("sourcepilot");

    await serviceLogin(page, user.email, user.password);
    await expect(
      page.getByText(/welcome to sourcepilot|imports|dashboard/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("login shows error with invalid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.waitForSelector("#email", { timeout: 10000 });
    await page.fill("#email", "invalid@example.com");
    await page.fill("#password", "wrongpassword");
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(
      page.getByText(/invalid email or password/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("protected routes redirect to login when not authenticated", async ({
    page,
  }) => {
    await page.goto("/imports");
    await page.waitForURL(/\/login/, { timeout: 10000 });
    await expect(
      page.getByRole("heading", { name: /sign in/i })
    ).toBeVisible();
  });

  test("user can logout", async ({ page }) => {
    const user = await registerServiceUser("sourcepilot");
    await serviceLogin(page, user.email, user.password);

    await page.getByRole("button", { name: /log out|logout/i }).click();
    await page.waitForURL(/\/login/, { timeout: 10000 });
  });

  test("registration validates password mismatch", async ({ page }) => {
    await page.goto("/register");
    await page.fill("#register-email", uniqueEmail());
    await page.fill("#register-password", TEST_PASSWORD);
    await page.fill("#register-confirm", "differentpassword");
    await page.getByRole("button", { name: /create account/i }).click();

    await expect(
      page.getByText(/passwords do not match/i)
    ).toBeVisible({ timeout: 5000 });
  });
});
