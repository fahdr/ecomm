/**
 * Dashboard authentication e2e tests.
 *
 * Tests user registration and login flows through the dashboard UI.
 *
 * **For QA Engineers:**
 *   - Registration creates a new account and redirects to /stores.
 *   - Login authenticates an existing user and redirects to /stores.
 *   - Invalid credentials show an error message.
 *   - Unauthenticated users are redirected to /login.
 */

import { test, expect } from "@playwright/test";
import { uniqueEmail, TEST_PASSWORD, registerUser } from "../helpers";

test.describe("Dashboard Authentication", () => {
  test("redirects unauthenticated users to login", async ({ page }) => {
    await page.goto("/stores");
    await expect(page).toHaveURL(/\/login/);
  });

  test("registers a new user and redirects to stores", async ({ page }) => {
    const email = uniqueEmail();

    await page.goto("/register");
    await expect(page.getByText(/create an account/i)).toBeVisible({ timeout: 10000 });

    await page.fill("#email", email);
    await page.fill("#password", TEST_PASSWORD);
    await page.getByRole("button", { name: /create account/i }).click();

    // Auth redirects to "/" (dashboard home) after registration.
    await expect(page).toHaveURL(/\/$/, { timeout: 10000 });
    await expect(page.getByText(/welcome back/i)).toBeVisible({ timeout: 5000 });
  });

  test("logs in an existing user", async ({ page }) => {
    const { email } = await registerUser();

    await page.goto("/login");
    await expect(page.locator("[data-slot='card-title']", { hasText: /sign in/i })).toBeVisible({ timeout: 10000 });

    await page.fill("#email", email);
    await page.fill("#password", TEST_PASSWORD);
    await page.getByRole("button", { name: /sign in/i }).click();

    // Auth redirects to "/" (dashboard home) after login.
    await expect(page).toHaveURL(/\/$/, { timeout: 10000 });
    await expect(page.getByText(/welcome back/i)).toBeVisible({ timeout: 5000 });
  });

  test("shows error for invalid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.fill("#email", "nonexistent@example.com");
    await page.fill("#password", "wrongpassword");
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page.locator(".text-destructive")).toBeVisible({ timeout: 5000 });
  });

  test("navigates between login and register", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("link", { name: /register/i }).click();
    await expect(page).toHaveURL(/\/register/);

    await page.getByRole("link", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/login/);
  });
});
