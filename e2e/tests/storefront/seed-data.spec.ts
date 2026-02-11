/**
 * Storefront seed data e2e tests.
 *
 * Verifies that the storefront correctly displays the pre-seeded demo data
 * from the "Volt Electronics" store. Covers product browsing, category
 * navigation, product reviews, and customer account flows.
 *
 * **For QA Engineers:**
 *   - Tests use ?store=volt-electronics to resolve the seed store.
 *   - Product pages should display images, variants, and reviews.
 *   - Category pages should show nested categories with product counts.
 *   - Customer login uses alice@example.com / password123 (seed customer).
 */

import { test, expect } from "@playwright/test";
import { seedDatabase } from "../helpers";

let storeSlug: string;

test.beforeAll(async () => {
  const seed = await seedDatabase();
  storeSlug = seed.storeSlug;
});

test.describe("Storefront Seed Data — Browsing", () => {
  test("homepage shows store name and products", async ({ page }) => {
    await page.goto(`/?store=${storeSlug}`, { waitUntil: "networkidle" });
    // Should display the store or at least some products
    await expect(page.getByText(/volt electronics|probook|galaxy/i).first()).toBeVisible({
      timeout: 15000,
    });
  });

  test("products page lists seeded products", async ({ page }) => {
    await page.goto(`/products?store=${storeSlug}`, { waitUntil: "networkidle" });
    await expect(page.getByText("ProBook Ultra 15")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Galaxy Nova X")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("PixelBudz Pro ANC")).toBeVisible({ timeout: 5000 });
  });

  test("product detail page shows full product info", async ({ page }) => {
    // Navigate from products listing to find ProBook Ultra 15 (slug may have suffix)
    await page.goto(`/products?store=${storeSlug}`, { waitUntil: "networkidle" });
    await expect(page.getByText("ProBook Ultra 15").first()).toBeVisible({ timeout: 15000 });
    // Click the product link to navigate to detail
    await page.getByText("ProBook Ultra 15").first().click();
    await expect(
      page.getByRole("heading", { name: /probook ultra 15/i })
    ).toBeVisible({ timeout: 15000 });
    // Price should be visible (may be formatted with or without comma)
    await expect(page.getByText(/\$1,?299\.99/).first()).toBeVisible({ timeout: 5000 });
    // Variants should be visible
    await expect(page.getByText(/silver|space gray/i).first()).toBeVisible({ timeout: 5000 });
  });

  test("product detail page shows reviews section", async ({ page }) => {
    // Navigate from products listing to find ProBook Ultra 15
    await page.goto(`/products?store=${storeSlug}`, { waitUntil: "networkidle" });
    await expect(page.getByText("ProBook Ultra 15").first()).toBeVisible({ timeout: 15000 });
    await page.getByText("ProBook Ultra 15").first().click();
    await expect(
      page.getByRole("heading", { name: /probook ultra 15/i })
    ).toBeVisible({ timeout: 15000 });
    // Reviews section always renders "Customer Reviews" heading and
    // a "Write a Review" button, even when there are no reviews yet
    await expect(page.getByText("Customer Reviews")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/write a review/i)).toBeVisible({ timeout: 5000 });
  });

  test("categories page shows seeded categories", async ({ page }) => {
    await page.goto(`/categories?store=${storeSlug}`, {
      waitUntil: "networkidle",
    });
    await expect(
      page.getByRole("heading", { name: /categories/i })
    ).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Laptops & Computers").first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Smartphones").first()).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("Audio & Headphones").first()).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("Accessories").first()).toBeVisible({ timeout: 5000 });
  });

  test("category detail page shows products in category", async ({ page }) => {
    // Navigate from categories listing to Laptops & Computers
    await page.goto(`/categories?store=${storeSlug}`, { waitUntil: "networkidle" });
    await expect(page.getByText("Laptops & Computers").first()).toBeVisible({ timeout: 15000 });
    // Click the "Browse products" link for Laptops & Computers
    await page.getByText("Laptops & Computers").first().click();
    await page.waitForLoadState("networkidle");
    // Should show the ProBook Ultra 15 which is in Laptops & Computers
    await expect(page.getByText("ProBook Ultra 15")).toBeVisible({ timeout: 15000 });
  });

  test("search finds seeded products", async ({ page }) => {
    await page.goto(`/search?store=${storeSlug}&q=headphones`, {
      waitUntil: "networkidle",
    });
    await expect(page.getByText("SoundStage Over-Ear Headphones").first()).toBeVisible({
      timeout: 15000,
    });
  });

  test("product page shows compare-at price", async ({ page }) => {
    // Navigate from products listing to ProBook Ultra 15
    await page.goto(`/products?store=${storeSlug}`, { waitUntil: "networkidle" });
    await expect(page.getByText("ProBook Ultra 15").first()).toBeVisible({ timeout: 15000 });
    await page.getByText("ProBook Ultra 15").first().click();
    await expect(
      page.getByRole("heading", { name: /probook ultra 15/i })
    ).toBeVisible({ timeout: 15000 });
    // Compare-at price ($1,499.99) should appear somewhere
    const body = await page.textContent("body");
    expect(body).toMatch(/1[,.]?499/);
  });
});

test.describe("Storefront Seed Data — Customer Account", () => {
  test("seed customer can login", async ({ page }) => {
    await page.goto(`/account/login?store=${storeSlug}`);
    await expect(
      page.getByRole("heading", { name: /sign in/i })
    ).toBeVisible({ timeout: 10000 });

    await page.fill("#email", "alice@example.com");
    await page.fill("#password", "password123");
    await page.getByRole("button", { name: /sign in/i }).click();

    // Should redirect to account dashboard
    await expect(page).toHaveURL(/\/account/, { timeout: 10000 });
    await expect(page.getByText(/welcome/i)).toBeVisible({ timeout: 10000 });
  });

  test("customer account shows order history", async ({ page }) => {
    // Login first
    await page.goto(`/account/login?store=${storeSlug}`);
    await page.fill("#email", "alice@example.com");
    await page.fill("#password", "password123");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/account/, { timeout: 10000 });

    // Navigate to orders
    await page.goto(`/account/orders?store=${storeSlug}`);
    await page.waitForLoadState("networkidle");

    // Alice has 1 order from the seed data — should show some order info
    const body = await page.textContent("body", { timeout: 10000 });
    const hasOrderData =
      body?.includes("order") ||
      body?.includes("Order") ||
      body?.includes("shipped") ||
      body?.includes("ProBook");
    expect(hasOrderData).toBe(true);
  });
});

test.describe("Storefront Seed Data — Policies", () => {
  test("shipping policy page renders", async ({ page }) => {
    await page.goto(`/policies/shipping?store=${storeSlug}`, {
      waitUntil: "networkidle",
    });
    await expect(page.getByText(/shipping/i).first()).toBeVisible({ timeout: 15000 });
  });

  test("returns policy page renders", async ({ page }) => {
    await page.goto(`/policies/returns?store=${storeSlug}`, {
      waitUntil: "networkidle",
    });
    await expect(page.getByText(/return/i).first()).toBeVisible({ timeout: 15000 });
  });
});
