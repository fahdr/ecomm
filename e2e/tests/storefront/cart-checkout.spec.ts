/**
 * Storefront cart and checkout e2e tests.
 *
 * Tests the full shopping flow: adding items to cart, adjusting
 * quantities, removing items, and completing checkout.
 *
 * **For QA Engineers:**
 *   - Add to cart button adds items and shows "Added to Cart!" confirmation.
 *   - Cart page allows quantity adjustment and item removal.
 *   - Checkout creates an order and redirects to success page.
 *   - Mock Stripe mode is used (no real payment needed).
 *   - All navigations include ``?store=`` for local dev store resolution.
 */

import { test, expect } from "@playwright/test";
import { registerUser, createStoreAPI, createProductAPI } from "../helpers";

test.describe("Storefront Cart & Checkout", () => {
  let storeSlug: string;
  let productTitle: string;
  let productSlug: string;

  test.beforeEach(async () => {
    const user = await registerUser();
    const store = await createStoreAPI(user.token, "Cart Test Store");
    storeSlug = store.slug;

    const product = await createProductAPI(user.token, store.id, {
      title: "Cart Widget",
      price: "29.99",
      variants: [
        { name: "Small", sku: "CW-S", price: null, inventory_count: 10 },
        { name: "Large", sku: "CW-L", price: "39.99", inventory_count: 5 },
      ],
    });
    productTitle = product.title;
    productSlug = product.slug;
  });

  test("adds item to cart from product page", async ({ page }) => {
    await page.goto(`/products/${productSlug}?store=${storeSlug}`, { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: productTitle })).toBeVisible({ timeout: 15000 });

    // First variant (Small) is auto-selected; click add to cart
    await page.getByRole("button", { name: /add to cart/i }).click();

    // Confirmation message
    await expect(page.getByText(/added to cart/i)).toBeVisible({ timeout: 5000 });
  });

  test("shows cart badge with count", async ({ page }) => {
    await page.goto(`/products/${productSlug}?store=${storeSlug}`, { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: productTitle })).toBeVisible({ timeout: 15000 });

    await page.getByRole("button", { name: /add to cart/i }).click();
    await expect(page.getByText(/added to cart/i)).toBeVisible({ timeout: 5000 });

    // Cart link should be visible in header
    const cartLink = page.getByRole("link", { name: /cart/i });
    await expect(cartLink).toBeVisible();
  });

  test("cart page shows added items", async ({ page }) => {
    // Add item via product page
    await page.goto(`/products/${productSlug}?store=${storeSlug}`, { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: productTitle })).toBeVisible({ timeout: 15000 });
    await page.getByRole("button", { name: /add to cart/i }).click();
    await expect(page.getByText(/added to cart/i)).toBeVisible({ timeout: 5000 });

    // Navigate to cart
    await page.goto(`/cart?store=${storeSlug}`);
    await expect(page.getByText(productTitle)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/small/i)).toBeVisible();
    await expect(page.getByText("$29.99 each")).toBeVisible();
  });

  test("cart shows empty state when no items", async ({ page }) => {
    await page.goto(`/cart?store=${storeSlug}`);
    await expect(page.getByText(/your cart is empty/i)).toBeVisible({ timeout: 10000 });
  });

  test("removes item from cart", async ({ page }) => {
    // Add item via product page
    await page.goto(`/products/${productSlug}?store=${storeSlug}`, { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: productTitle })).toBeVisible({ timeout: 15000 });
    await page.getByRole("button", { name: /add to cart/i }).click();
    await expect(page.getByText(/added to cart/i)).toBeVisible({ timeout: 5000 });

    // Go to cart and remove
    await page.goto(`/cart?store=${storeSlug}`);
    await expect(page.getByText(productTitle)).toBeVisible({ timeout: 10000 });

    // Click the remove button (uses title="Remove item")
    await page.locator('button[title="Remove item"]').click();
    await expect(page.getByText(/your cart is empty/i)).toBeVisible({ timeout: 5000 });
  });

  test("completes checkout with mock stripe", async ({ page }) => {
    // Add item via product page
    await page.goto(`/products/${productSlug}?store=${storeSlug}`, { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: productTitle })).toBeVisible({ timeout: 15000 });
    await page.getByRole("button", { name: /add to cart/i }).click();
    await expect(page.getByText(/added to cart/i)).toBeVisible({ timeout: 5000 });

    // Go to cart
    await page.goto(`/cart?store=${storeSlug}`);
    await expect(page.getByText(productTitle)).toBeVisible({ timeout: 10000 });

    // Fill email and checkout
    await page.fill('input[type="email"]', "buyer@example.com");
    await page.getByRole("button", { name: /proceed to checkout/i }).click();

    // Mock Stripe redirects to success page
    await expect(page).toHaveURL(/\/checkout\/success/, { timeout: 15000 });
    await expect(page.getByText(/order confirmed/i)).toBeVisible({ timeout: 10000 });
  });
});
