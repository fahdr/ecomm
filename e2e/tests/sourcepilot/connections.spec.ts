/**
 * SourcePilot store connection management e2e tests.
 *
 * Tests connecting, listing, updating, disconnecting stores, and
 * setting a default import target.
 *
 * **For QA Engineers:**
 *   - Verify store connection creation via UI
 *   - Verify connections list shows connected stores with platform badges
 *   - Verify first store is auto-set as default
 *   - Verify set-default changes the default indicator
 *   - Verify store deletion removes from list
 *   - Verify empty state when no stores connected
 *
 * **For End Users:**
 *   - Connect your Shopify, WooCommerce, or other stores
 *   - Set a default store for quick one-click imports
 *   - Manage and disconnect stores as needed
 */

import { test, expect } from "@playwright/test";
import {
  registerServiceUser,
  serviceLogin,
  createStoreConnectionAPI,
  serviceApiPost,
  serviceApiDelete,
  serviceApiGet,
} from "../service-helpers";

test.describe("SourcePilot Store Connections", () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("sourcepilot");
    token = user.token;
    await serviceLogin(page, user.email, user.password);
  });

  test("shows empty state when no stores connected", async ({ page }) => {
    await page.goto("/connections");
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/no store|connect.*store|get started/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("lists store connections created via API", async ({ page }) => {
    await createStoreConnectionAPI(token, {
      store_name: "My Shopify Store",
      platform: "shopify",
      store_url: "https://myshop.myshopify.com",
    });

    await page.goto("/connections");
    await page.waitForLoadState("networkidle");

    await expect(
      page.getByText(/my shopify store/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("first connection is auto-set as default", async ({ page }) => {
    const conn = await createStoreConnectionAPI(token, {
      store_name: "Default Store",
      platform: "shopify",
      store_url: "https://default.myshopify.com",
    });

    // Verify via API that it's the default
    const list = await serviceApiGet(
      "sourcepilot",
      token,
      "/api/v1/connections"
    );
    expect(list.items[0].is_default).toBe(true);

    await page.goto("/connections");
    await page.waitForLoadState("networkidle");

    await expect(
      page.getByText(/default store/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("can set a different store as default", async ({ page }) => {
    const conn1 = await createStoreConnectionAPI(token, {
      store_name: "Store One",
      platform: "shopify",
      store_url: "https://store-one.myshopify.com",
    });
    const conn2 = await createStoreConnectionAPI(token, {
      store_name: "Store Two",
      platform: "woocommerce",
      store_url: "https://store-two.example.com",
    });

    // Set Store Two as default
    await serviceApiPost(
      "sourcepilot",
      token,
      `/api/v1/connections/${conn2.id}/default`,
      {}
    );

    // Verify via API
    const list = await serviceApiGet(
      "sourcepilot",
      token,
      "/api/v1/connections"
    );
    const defaultConn = list.items.find((c: any) => c.is_default);
    expect(defaultConn.store_name).toBe("Store Two");

    await page.goto("/connections");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(/store one/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/store two/i)).toBeVisible({ timeout: 5000 });
  });

  test("can connect store via dialog", async ({ page }) => {
    await page.goto("/connections");
    await page.waitForLoadState("networkidle");

    // Click connect store button
    await page.getByRole("button", { name: /connect.*store|add.*store/i }).click();

    // Dialog should open
    await expect(
      page.getByRole("heading", { name: /connect|new.*store/i })
    ).toBeVisible();

    // Fill the form
    const nameInput = page.locator("input[placeholder*='name'], input[name*='name']").first();
    await nameInput.fill("My New Store");

    const urlInput = page.locator("input[placeholder*='url'], input[name*='url']").first();
    await urlInput.fill("https://mynewstore.myshopify.com");

    // Submit
    await page.getByRole("button", { name: /connect|save|submit/i }).last().click();

    // Should appear in list
    await expect(
      page.getByText(/my new store/i)
    ).toBeVisible({ timeout: 15000 });
  });

  test("shows platform badges for different store types", async ({ page }) => {
    await createStoreConnectionAPI(token, {
      store_name: "Shopify Store",
      platform: "shopify",
      store_url: "https://shop1.myshopify.com",
    });
    await createStoreConnectionAPI(token, {
      store_name: "WooCommerce Store",
      platform: "woocommerce",
      store_url: "https://woo.example.com",
    });

    await page.goto("/connections");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(/shopify/i).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/woocommerce/i).first()).toBeVisible({ timeout: 5000 });
  });

  test("can delete a store connection", async ({ page }) => {
    const conn = await createStoreConnectionAPI(token, {
      store_name: "Removable Store",
      platform: "shopify",
      store_url: "https://remove.myshopify.com",
    });

    await page.goto("/connections");
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/removable store/i)
    ).toBeVisible({ timeout: 10000 });

    // Delete via API
    await serviceApiDelete(
      "sourcepilot",
      token,
      `/api/v1/connections/${conn.id}`
    );

    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/removable store/i)
    ).not.toBeVisible({ timeout: 5000 });
  });
});
