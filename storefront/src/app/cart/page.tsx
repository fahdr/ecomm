/**
 * Shopping cart page for the storefront.
 *
 * Displays all items in the cart with quantity controls, individual
 * and total prices, and a checkout button. Items can be removed or
 * have their quantities adjusted.
 *
 * **For Developers:**
 *   This is a client component that reads from the cart context.
 *   Checkout calls the public checkout API to create a Stripe session
 *   and redirects to the checkout URL.
 *
 * **For QA Engineers:**
 *   - Empty cart shows a "Your cart is empty" message with a shop link.
 *   - Each item shows title, variant name, unit price, quantity, and line total.
 *   - Quantity can be increased/decreased with +/- buttons.
 *   - Remove button deletes the item entirely.
 *   - Checkout button is disabled during processing.
 *   - Invalid email shows a validation error.
 *
 * **For End Users:**
 *   Review your cart before checkout. Adjust quantities or remove items
 *   as needed. Enter your email and click "Checkout" to proceed to payment.
 */

"use client";

import { useState } from "react";
import Link from "next/link";
import { useCart } from "@/contexts/cart-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";

/**
 * Cart page client component.
 *
 * @returns The cart page with item list, totals, and checkout form.
 */
export default function CartPage() {
  const { items, removeItem, updateQuantity, cartTotal, clearCart } = useCart();
  const store = useStore();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Handle checkout by calling the public checkout API.
   * Redirects to the Stripe Checkout URL on success.
   */
  async function handleCheckout() {
    if (!store) return;
    if (!email || !email.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }

    setLoading(true);
    setError(null);

    const checkoutItems = items.map((item) => ({
      product_id: item.productId,
      variant_id: item.variantId || undefined,
      quantity: item.quantity,
    }));

    const { data, error: apiError } = await api.post<{
      checkout_url: string;
      session_id: string;
      order_id: string;
    }>(
      `/api/v1/public/stores/${encodeURIComponent(store.slug)}/checkout`,
      {
        customer_email: email,
        items: checkoutItems,
      }
    );

    if (apiError) {
      setError(apiError.message || "Checkout failed. Please try again.");
      setLoading(false);
      return;
    }

    if (data?.checkout_url) {
      clearCart();
      window.location.href = data.checkout_url;
    }
  }

  if (items.length === 0) {
    return (
      <div className="py-16">
        <div className="mx-auto max-w-2xl px-4 text-center">
          <h2 className="text-2xl font-bold tracking-tight mb-4">
            Your cart is empty
          </h2>
          <p className="text-zinc-500 dark:text-zinc-400 mb-8">
            Browse our products and add items to your cart.
          </p>
          <Link
            href="/products"
            className="inline-flex items-center rounded-lg bg-zinc-900 dark:bg-zinc-100 px-6 py-3 text-sm font-medium text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors"
          >
            Continue Shopping
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="py-12">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
        <h2 className="text-3xl font-bold tracking-tight mb-8">Shopping Cart</h2>

        {/* Cart Items */}
        <div className="space-y-4">
          {items.map((item) => (
            <div
              key={`${item.productId}-${item.variantId}`}
              className="flex items-center gap-4 rounded-lg border border-zinc-200 dark:border-zinc-800 p-4"
            >
              {/* Image */}
              <Link href={`/products/${item.slug}`} className="shrink-0">
                {item.image ? (
                  <img
                    src={item.image}
                    alt={item.title}
                    className="h-20 w-20 rounded-lg object-cover"
                  />
                ) : (
                  <div className="h-20 w-20 rounded-lg bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center">
                    <div className="h-8 w-8 rounded-full bg-zinc-200 dark:bg-zinc-700" />
                  </div>
                )}
              </Link>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <Link
                  href={`/products/${item.slug}`}
                  className="font-medium hover:underline"
                >
                  {item.title}
                </Link>
                {item.variantName && (
                  <p className="text-sm text-zinc-500 dark:text-zinc-400">
                    {item.variantName}
                  </p>
                )}
                <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                  ${item.price.toFixed(2)} each
                </p>
              </div>

              {/* Quantity Controls */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() =>
                    updateQuantity(item.productId, item.variantId, item.quantity - 1)
                  }
                  className="h-8 w-8 rounded border border-zinc-300 dark:border-zinc-700 flex items-center justify-center text-sm hover:bg-zinc-50 dark:hover:bg-zinc-900"
                >
                  -
                </button>
                <span className="w-8 text-center text-sm font-medium">
                  {item.quantity}
                </span>
                <button
                  onClick={() =>
                    updateQuantity(item.productId, item.variantId, item.quantity + 1)
                  }
                  className="h-8 w-8 rounded border border-zinc-300 dark:border-zinc-700 flex items-center justify-center text-sm hover:bg-zinc-50 dark:hover:bg-zinc-900"
                >
                  +
                </button>
              </div>

              {/* Line Total */}
              <div className="text-right w-24">
                <p className="font-semibold">
                  ${(item.price * item.quantity).toFixed(2)}
                </p>
              </div>

              {/* Remove */}
              <button
                onClick={() => removeItem(item.productId, item.variantId)}
                className="text-zinc-400 hover:text-red-500 transition-colors"
                title="Remove item"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                  className="h-5 w-5"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 18 18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          ))}
        </div>

        {/* Cart Summary & Checkout */}
        <div className="mt-8 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
          <div className="flex items-center justify-between mb-6">
            <span className="text-lg font-medium">Total</span>
            <span className="text-2xl font-bold">${cartTotal.toFixed(2)}</span>
          </div>

          {/* Email Input */}
          <div className="mb-4">
            <label
              htmlFor="checkout-email"
              className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1"
            >
              Email address
            </label>
            <input
              id="checkout-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
            />
          </div>

          {error && (
            <p className="text-sm text-red-500 mb-4">{error}</p>
          )}

          <button
            onClick={handleCheckout}
            disabled={loading}
            className="w-full rounded-lg bg-zinc-900 dark:bg-zinc-100 px-6 py-3 text-sm font-medium text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Processing..." : "Proceed to Checkout"}
          </button>

          <Link
            href="/products"
            className="block text-center mt-4 text-sm text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100"
          >
            Continue Shopping
          </Link>
        </div>
      </div>
    </div>
  );
}
