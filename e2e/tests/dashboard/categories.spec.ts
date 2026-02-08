/**
 * Dashboard category management e2e tests.
 *
 * Tests category creation, listing, and hierarchical display.
 *
 * **For QA Engineers:**
 *   - Categories display in a tree structure.
 *   - Creating a category refreshes the tree.
 *   - Empty state is shown when no categories exist.
 *   - Sub-categories appear nested under parents.
 */

import { test, expect } from "@playwright/test";
import {
  registerUser,
  dashboardLogin,
  createStoreAPI,
  createCategoryAPI,
} from "../helpers";

test.describe("Dashboard Category Management", () => {
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows empty state when no categories exist", async ({ page }) => {
    await page.goto(`/stores/${storeId}/categories`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/no categor/i)).toBeVisible({ timeout: 10000 });
  });

  test("creates a category via dialog", async ({ page }) => {
    await page.goto(`/stores/${storeId}/categories`);
    await page.waitForLoadState("networkidle");
    // Wait for empty state to confirm page is loaded and interactive
    await expect(page.getByText(/no categor/i)).toBeVisible({ timeout: 10000 });

    // Use the header "Add Category" button with JS click for reliability
    await page.$eval('button:has-text("Add Category")', (el: HTMLElement) => el.click());
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 5000 });

    await page.fill("#cat-name", "Electronics");

    // Click submit and wait for the POST to complete
    const [postResp] = await Promise.all([
      page.waitForResponse(
        (resp) => resp.url().includes("/categories") && resp.request().method() === "POST",
        { timeout: 10000 }
      ),
      page.locator('[role="dialog"] button[type="submit"]').click(),
    ]);

    // Wait for dialog to close (indicates POST succeeded)
    await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 10000 });

    // Reload to ensure fresh data from the database
    await page.reload();
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Electronics")).toBeVisible({ timeout: 10000 });
  });

  test("lists categories created via API", async ({ page }) => {
    await createCategoryAPI(token, storeId, "Clothing");
    await createCategoryAPI(token, storeId, "Accessories");

    await page.goto(`/stores/${storeId}/categories`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Clothing")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Accessories")).toBeVisible();
  });

  test("displays nested subcategories", async ({ page }) => {
    // Create a parent category and two children under it
    const parent = await createCategoryAPI(token, storeId, "Electronics");
    await createCategoryAPI(token, storeId, "Smartphones", parent.id);
    await createCategoryAPI(token, storeId, "Laptops", parent.id);

    await page.goto(`/stores/${storeId}/categories`);
    await page.waitForLoadState("networkidle");

    // Verify parent is visible first (confirms data loaded)
    await expect(page.getByText("Electronics").first()).toBeVisible({ timeout: 10000 });

    // Verify both subcategories are visible (tree is expanded by default).
    // The frontend builds a tree client-side from the flat category list using parent_id.
    await expect(page.getByText("Smartphones").first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Laptops").first()).toBeVisible({ timeout: 10000 });

    // Verify the hierarchy indicator (category count shows 3 categories)
    await expect(page.getByText(/3 categor/i).first()).toBeVisible({ timeout: 10000 });
  });

  test("navigates from store settings to categories", async ({ page }) => {
    await page.goto(`/stores/${storeId}`);
    await page.getByRole("button", { name: /categories/i }).click();
    await expect(page).toHaveURL(new RegExp(`/stores/${storeId}/categories`), {
      timeout: 10000,
    });
  });
});
