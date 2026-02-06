/**
 * Cart badge component for the storefront header.
 *
 * Displays a cart icon with the current item count as a badge.
 * Links to the cart page. Only renders the count badge when the
 * cart has items.
 *
 * **For Developers:**
 *   This is a client component that reads from the cart context.
 *   Must be rendered within a ``CartProvider``.
 *
 * **For QA Engineers:**
 *   - Badge shows total item count (sum of quantities).
 *   - Badge is hidden when cart is empty.
 *   - Clicking navigates to ``/cart``.
 *
 * **For End Users:**
 *   The cart icon in the header shows how many items are in your cart.
 *   Click it to view your cart.
 */

"use client";

import Link from "next/link";
import { useCart } from "@/contexts/cart-context";

/**
 * Cart icon with item count badge.
 *
 * @returns A link to the cart page with an SVG cart icon and optional count badge.
 */
export function CartBadge() {
  const { cartCount } = useCart();

  return (
    <Link
      href="/cart"
      className="relative inline-flex items-center text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={1.5}
        stroke="currentColor"
        className="h-6 w-6"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 0 0-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 0 0-16.536-1.84M7.5 14.25 5.106 5.272M6 20.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm12.75 0a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z"
        />
      </svg>
      {cartCount > 0 && (
        <span className="absolute -top-2 -right-2 inline-flex h-5 w-5 items-center justify-center rounded-full bg-zinc-900 dark:bg-zinc-100 text-xs font-medium text-white dark:text-zinc-900">
          {cartCount}
        </span>
      )}
    </Link>
  );
}
