/**
 * Shopping cart page for the storefront.
 *
 * Displays all items in the cart with quantity controls, individual
 * and total prices, and a "Proceed to Checkout" button that navigates
 * to the dedicated checkout page.
 *
 * **For Developers:**
 *   Client component that reads from the cart context. No API calls
 *   happen on this page — checkout logic lives in ``/checkout``.
 *
 * **For QA Engineers:**
 *   - Empty cart shows a "Your cart is empty" message with a shop link.
 *   - Each item shows title, variant name, unit price, quantity, and line total.
 *   - Quantity can be increased/decreased with +/- buttons.
 *   - Remove button deletes the item entirely.
 *   - "Proceed to Checkout" navigates to /checkout.
 *
 * **For End Users:**
 *   Review your cart before checkout. Adjust quantities or remove items
 *   as needed. Click "Proceed to Checkout" to enter your shipping details
 *   and complete your purchase.
 */

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCart } from "@/contexts/cart-context";

/**
 * Cart page client component.
 *
 * @returns The cart page with item list, totals, and checkout link.
 */
export default function CartPage() {
  const { items, removeItem, updateQuantity, cartTotal } = useCart();
  const router = useRouter();

  if (items.length === 0) {
    return (
      <div className="py-16">
        <div className="mx-auto max-w-2xl px-4 text-center">
          {/* Empty cart illustration */}
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-800">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="h-10 w-10 text-zinc-400 dark:text-zinc-500"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 0 0-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 0 0-16.536-1.84M7.5 14.25 5.106 5.272M6 20.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm12.75 0a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z"
              />
            </svg>
          </div>
          <h2 className="text-2xl font-heading font-bold tracking-tight mb-3">
            Your cart is empty
          </h2>
          <p className="text-theme-muted mb-8">
            Browse our products and add items to your cart.
          </p>
          <Link
            href="/products"
            className="inline-flex items-center rounded-lg bg-theme-primary px-6 py-3 text-sm font-medium text-white hover:opacity-90 transition-opacity"
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
        <h2 className="text-3xl font-heading font-bold tracking-tight mb-8">
          Shopping Cart
        </h2>

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
                  <p className="text-sm text-theme-muted">{item.variantName}</p>
                )}
                <p className="text-sm text-theme-muted mt-1">
                  ${item.price.toFixed(2)} each
                </p>
              </div>

              {/* Quantity Controls */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() =>
                    updateQuantity(
                      item.productId,
                      item.variantId,
                      item.quantity - 1
                    )
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
                    updateQuantity(
                      item.productId,
                      item.variantId,
                      item.quantity + 1
                    )
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

        {/* Cart Summary */}
        <div className="mt-8 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-lg font-medium">Subtotal</span>
            <span className="text-2xl font-bold">${cartTotal.toFixed(2)}</span>
          </div>
          <p className="text-sm text-theme-muted mb-6">
            Shipping, taxes, and discounts calculated at checkout
          </p>

          <button
            onClick={() => router.push("/checkout")}
            className="w-full rounded-lg bg-theme-primary px-6 py-3.5 text-sm font-semibold text-white hover:opacity-90 transition-opacity"
          >
            Proceed to Checkout
          </button>

          <Link
            href="/products"
            className="block text-center mt-4 text-sm text-theme-muted hover:text-theme-primary transition-colors"
          >
            Continue Shopping
          </Link>
        </div>
      </div>
    </div>
  );
}
