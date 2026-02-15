/**
 * ContentForge template management e2e tests.
 */

import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin, createContentTemplateAPI } from "../service-helpers";

test.describe("ContentForge Templates", () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("contentforge");
    token = user.token;
    await serviceLogin(page, user.email, user.password);
  });

  test("displays templates page with heading", async ({ page }) => {
    await page.goto("/templates");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: /content templates/i })).toBeVisible({ timeout: 10000 });
  });

  test("can create a new template via dialog", async ({ page }) => {
    await page.goto("/templates");
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: /new template/i }).click();

    await expect(page.getByRole("heading", { name: /new template/i })).toBeVisible();

    // Fill template details
    await page.fill("#tpl-name", "Luxury Brand Voice");

    // Create — click inside dialog
    await page.locator("[role=dialog]").getByRole("button", { name: /create/i }).click();

    // Should show in templates list
    await expect(page.getByText(/luxury brand voice/i)).toBeVisible({ timeout: 10000 });
  });

  test("displays templates created via API", async ({ page }) => {
    await createContentTemplateAPI(token, {
      name: "Technical Specs Template",
      content_type: "product_description",
    });

    await page.goto("/templates");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(/technical specs template/i)).toBeVisible({ timeout: 10000 });
  });

  test("can edit an existing template", async ({ page }) => {
    await createContentTemplateAPI(token, {
      name: "Template to Edit",
    });

    await page.goto("/templates");
    await page.waitForLoadState("networkidle");

    // Click edit button
    await page.getByRole("button", { name: /edit/i }).first().click();

    // Dialog should open
    await expect(page.getByRole("heading", { name: /edit template/i })).toBeVisible();

    // Change name
    await page.fill("#tpl-name", "Updated Template Name");

    // Save
    await page.getByRole("button", { name: /save/i }).click();

    // Should show updated name
    await expect(page.getByText(/updated template name/i)).toBeVisible({ timeout: 10000 });
  });
});
