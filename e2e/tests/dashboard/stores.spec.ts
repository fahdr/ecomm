/**
 * Dashboard store management e2e tests.
 *
 * Tests store creation, listing, settings update, and deletion flows.
 *
 * **For QA Engineers:**
 *   - Store creation form validates required fields.
 *   - New stores appear in the stores list.
 *   - Store settings can be updated.
 *   - Store deletion requires confirmation dialog.
 */

import { test, expect } from "@playwright/test";
import { registerUser, dashboardLogin } from "../helpers";

test.describe("Dashboard Store Management", () => {
  let email: string;
  let password: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    email = user.email;
    password = user.password;
    await dashboardLogin(page, email, password);
    await page.goto("/stores");
    await page.waitForLoadState("networkidle");
  });

  test("shows empty state when no stores exist", async ({ page }) => {
    await expect(page.getByText(/no stores yet/i)).toBeVisible();
    await expect(page.getByRole("link", { name: /create your first store/i })).toBeVisible();
  });

  test("creates a new store", async ({ page }) => {
    await page.getByRole("link", { name: /create.*store/i }).first().click();
    await expect(page).toHaveURL(/\/stores\/new/);

    await page.fill("#name", "My E2E Store");

    // Select niche via the dropdown
    await page.locator("#niche").click();
    await page.getByRole("option", { name: /electronics/i }).click();

    await page.fill("#description", "An automated test store");
    await page.getByRole("button", { name: /create store/i }).click();

    // Should redirect to store settings page
    await expect(page).toHaveURL(/\/stores\/[a-f0-9-]+/, { timeout: 10000 });
    await expect(page.getByText("My E2E Store")).toBeVisible();
  });

  test("lists created stores", async ({ page }) => {
    // Create a store via the UI
    await page.getByRole("link", { name: /create.*store/i }).first().click();
    await page.fill("#name", "Listed Store");
    await page.locator("#niche").click();
    await page.getByRole("option", { name: /fashion/i }).click();
    await page.getByRole("button", { name: /create store/i }).click();
    await expect(page).toHaveURL(/\/stores\/[a-f0-9-]+/, { timeout: 10000 });

    // Navigate back to stores list
    await page.goto("/stores");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Listed Store")).toBeVisible({ timeout: 10000 });
  });

  test("updates store settings", async ({ page }) => {
    // Create store first
    await page.getByRole("link", { name: /create.*store/i }).first().click();
    await page.fill("#name", "Original Name");
    await page.locator("#niche").click();
    await page.getByRole("option", { name: /electronics/i }).click();
    await page.getByRole("button", { name: /create store/i }).click();
    await expect(page).toHaveURL(/\/stores\/[a-f0-9-]+/, { timeout: 10000 });

    // Update the store name
    await page.fill("#name", "Updated Name");
    await page.getByRole("button", { name: /save changes/i }).click();

    await expect(page.getByText(/store updated successfully/i)).toBeVisible({ timeout: 5000 });
    await expect(page.locator("#name")).toHaveValue("Updated Name");
  });

  test("deletes a store with confirmation", async ({ page }) => {
    // Create store first
    await page.getByRole("link", { name: /create.*store/i }).first().click();
    await page.fill("#name", "Store To Delete");
    await page.locator("#niche").click();
    await page.getByRole("option", { name: /electronics/i }).click();
    await page.getByRole("button", { name: /create store/i }).click();
    await expect(page).toHaveURL(/\/stores\/[a-f0-9-]+/, { timeout: 10000 });

    // Click delete button to open dialog
    await page.getByRole("button", { name: /delete store/i }).click();
    await expect(page.getByText(/this action cannot be undone/i)).toBeVisible();

    // Confirm deletion
    await page.getByRole("button", { name: /^delete$/i }).click();

    // Should redirect to stores list
    await expect(page).toHaveURL(/\/stores$/, { timeout: 10000 });
  });
});
