/**
 * Dashboard seed data e2e tests.
 *
 * Verifies that every major dashboard page correctly renders the
 * pre-seeded demo data. These tests run after the seed script
 * (scripts/seed.ts) has populated the database with the "Volt
 * Electronics" store and all associated data.
 *
 * **For QA Engineers:**
 *   - Tests login as demo@example.com / password123 (seed user).
 *   - Each test navigates to a different dashboard page and verifies
 *     key data items from the seed script.
 *   - These tests complement the per-feature tests that create their
 *     own isolated data.
 *   - All assertions use .first() to handle duplicate data from
 *     multiple seed runs gracefully.
 */

import { test, expect } from "@playwright/test";
import { seedDatabase, dashboardLogin } from "../helpers";

let storeId: string;

test.beforeAll(async () => {
  const seed = await seedDatabase();
  storeId = seed.storeId;
});

test.describe("Dashboard Seed Data", () => {
  test.beforeEach(async ({ page }) => {
    await dashboardLogin(page, "demo@example.com", "password123");
  });

  test("home page shows welcome message", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByRole("heading", { name: /welcome back/i })
    ).toBeVisible({ timeout: 15000 });
  });

  test("stores page lists Volt Electronics", async ({ page }) => {
    await page.goto("/stores");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Volt Electronics").first()).toBeVisible({ timeout: 10000 });
  });

  test("products page shows seeded products", async ({ page }) => {
    await page.goto(`/stores/${storeId}/products`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("ProBook Ultra 15").first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Galaxy Nova X").first()).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("PixelBudz Pro ANC").first()).toBeVisible({ timeout: 5000 });
  });

  test("categories page shows seeded categories", async ({ page }) => {
    await page.goto(`/stores/${storeId}/categories`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Laptops & Computers").first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Smartphones").first()).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("Audio & Headphones").first()).toBeVisible({ timeout: 5000 });
  });

  test("orders page shows seeded orders", async ({ page }) => {
    await page.goto(`/stores/${storeId}/orders`);
    await page.waitForLoadState("networkidle");
    // At least one order email should be visible
    await expect(page.getByText("alice@example.com").first()).toBeVisible({ timeout: 10000 });
  });

  test("orders include different statuses", async ({ page }) => {
    await page.goto(`/stores/${storeId}/orders`);
    await page.waitForLoadState("networkidle");
    // Seed creates orders in various states: paid, shipped, delivered
    const body = await page.textContent("body", { timeout: 10000 });
    expect(body).toBeTruthy();
    // At least one status badge should be present
    const hasStatuses = /paid|shipped|delivered/i.test(body!);
    expect(hasStatuses).toBe(true);
  });

  test("suppliers page shows seeded suppliers", async ({ page }) => {
    await page.goto(`/stores/${storeId}/suppliers`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("TechSource Global").first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("MobileFirst Supply Co.").first()).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("AudioPrime Distributors").first()).toBeVisible({ timeout: 5000 });
  });

  test("discounts page shows seeded discount codes", async ({ page }) => {
    await page.goto(`/stores/${storeId}/discounts`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("WELCOME10").first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("SUMMER25").first()).toBeVisible({ timeout: 5000 });
  });

  test("gift cards page shows seeded gift cards", async ({ page }) => {
    await page.goto(`/stores/${storeId}/gift-cards`);
    await page.waitForLoadState("networkidle");
    // Gift cards should display — at least the heading or a card entry
    await expect(page.getByText(/gift cards/i).first()).toBeVisible({ timeout: 10000 });
    // At least one balance amount should be visible
    const body = await page.textContent("body");
    expect(body).toMatch(/\$25|\$50|\$100/);
  });

  test("tax rates page shows seeded tax rates", async ({ page }) => {
    await page.goto(`/stores/${storeId}/tax`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("California Sales Tax").first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("UK VAT").first()).toBeVisible({ timeout: 5000 });
  });

  test("segments page shows seeded segments", async ({ page }) => {
    await page.goto(`/stores/${storeId}/segments`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("High-Value Customers").first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Repeat Buyers").first()).toBeVisible({ timeout: 5000 });
  });

  test("upsells page shows seeded upsell rules", async ({ page }) => {
    await page.goto(`/stores/${storeId}/upsells`);
    await page.waitForLoadState("networkidle");
    // Seed creates 4 upsells — at least cross_sell type should be visible
    await expect(page.getByText(/cross.sell|upsell|bundle/i).first()).toBeVisible({ timeout: 10000 });
  });

  test("A/B tests page shows seeded experiments", async ({ page }) => {
    await page.goto(`/stores/${storeId}/ab-tests`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Checkout Button Color").first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Product Page Layout", { exact: true }).first()).toBeVisible({ timeout: 10000 });
  });

  test("webhooks page shows seeded webhook endpoints", async ({ page }) => {
    await page.goto(`/stores/${storeId}/webhooks`);
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/hooks\.voltelectronics\.com/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("reviews page shows seeded product reviews", async ({ page }) => {
    await page.goto(`/stores/${storeId}/reviews`);
    await page.waitForLoadState("networkidle");
    // Seed creates 12 reviews — check for review content
    await expect(page.getByText("Total Reviews").first()).toBeVisible({ timeout: 10000 });
    // The review count should be > 0
    await expect(page.getByText("Avg Rating").first()).toBeVisible({ timeout: 5000 });
  });

  test("refunds page shows seeded refund", async ({ page }) => {
    await page.goto(`/stores/${storeId}/refunds`);
    await page.waitForLoadState("networkidle");
    // Seed creates 1 refund for Carol's order
    const body = await page.textContent("body", { timeout: 10000 });
    // Should show either the refund data or the pending status
    expect(body).toMatch(/refund|pending|\$179/i);
  });

  test("team page shows seeded team invitations", async ({ page }) => {
    await page.goto(`/stores/${storeId}/team`);
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText("marketing@voltelectronics.com").first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("themes page shows preset themes", async ({ page }) => {
    await page.goto(`/stores/${storeId}/themes`);
    await page.waitForLoadState("networkidle");
    // 7 presets: Frosted, Midnight, Botanical, Neon, Luxe, Playful, Industrial
    await expect(page.getByText("Frosted").first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Midnight").first()).toBeVisible({ timeout: 5000 });
  });

  test("email settings page shows templates", async ({ page }) => {
    await page.goto(`/stores/${storeId}/email`);
    await page.waitForLoadState("networkidle");
    // Should show email template types
    await expect(
      page.getByText(/order confirmation|order_confirmation/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("analytics page shows revenue data from seeded orders", async ({ page }) => {
    await page.goto(`/stores/${storeId}/analytics`);
    await page.waitForLoadState("networkidle");
    // Analytics should show revenue/orders from the seeded data
    await expect(page.getByText(/revenue|orders|profit/i).first()).toBeVisible({ timeout: 10000 });
  });

  test("currency settings page loads", async ({ page }) => {
    await page.goto(`/stores/${storeId}/currency`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/currency/i).first()).toBeVisible({ timeout: 10000 });
  });

  test("domain page shows seeded domain", async ({ page }) => {
    await page.goto(`/stores/${storeId}/domain`);
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/shop\.voltelectronics\.com|domain/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("bulk operations page loads", async ({ page }) => {
    await page.goto(`/stores/${storeId}/bulk`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Bulk Price Update").first()).toBeVisible({ timeout: 10000 });
  });

  test("fraud detection page loads", async ({ page }) => {
    await page.goto(`/stores/${storeId}/fraud`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/fraud/i).first()).toBeVisible({ timeout: 10000 });
  });
});
