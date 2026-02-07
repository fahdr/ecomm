/**
 * Wishlist toggle button for product pages.
 *
 * Renders a heart icon that adds/removes a product from the customer's
 * wishlist. Only visible when the customer is logged in.
 *
 * **For Developers:**
 *   Uses ``useCustomerAuth()`` and ``useStore()`` for context.
 *   Manages its own ``wishlisted`` state with optimistic updates.
 *
 * **For QA Engineers:**
 *   - Hidden when customer is not logged in.
 *   - Heart is filled when the product is in the wishlist.
 *   - Clicking toggles the wishlist state via API.
 *   - Shows a brief loading state during the API call.
 *
 * **For End Users:**
 *   Click the heart icon to save a product to your wishlist for later.
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import { useCustomerAuth } from "@/contexts/customer-auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import type { PaginatedWishlist, WishlistItem } from "@/lib/types";

/** Props for the WishlistButton component. */
interface WishlistButtonProps {
  /** UUID of the product to add/remove from wishlist. */
  productId: string;
  /** Optional CSS class name for styling. */
  className?: string;
}

/**
 * Wishlist toggle button component.
 *
 * @param props - Component props with productId and optional className.
 * @returns A heart icon button, or null if the customer is not logged in.
 */
export function WishlistButton({ productId, className = "" }: WishlistButtonProps) {
  const { customer } = useCustomerAuth();
  const store = useStore();
  const [wishlisted, setWishlisted] = useState(false);
  const [wishlistItemId, setWishlistItemId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Check if product is already in wishlist on mount
  useEffect(() => {
    if (!customer || !store) return;

    async function check() {
      const slug = encodeURIComponent(store!.slug);
      const result = await api.get<PaginatedWishlist>(
        `/api/v1/public/stores/${slug}/account/wishlist?per_page=100`
      );
      if (result.data) {
        const found = result.data.items.find(
          (item: WishlistItem) => item.product_id === productId
        );
        if (found) {
          setWishlisted(true);
          setWishlistItemId(found.id);
        }
      }
    }

    check();
  }, [customer, store, productId]);

  const toggle = useCallback(async () => {
    if (!store || busy) return;
    setBusy(true);

    const slug = encodeURIComponent(store.slug);

    if (wishlisted && wishlistItemId) {
      await api.del(`/api/v1/public/stores/${slug}/account/wishlist/${wishlistItemId}`);
      setWishlisted(false);
      setWishlistItemId(null);
    } else {
      const result = await api.post<WishlistItem>(
        `/api/v1/public/stores/${slug}/account/wishlist`,
        { product_id: productId }
      );
      if (result.data) {
        setWishlisted(true);
        setWishlistItemId(result.data.id);
      }
    }

    setBusy(false);
  }, [store, wishlisted, wishlistItemId, productId, busy]);

  if (!customer) return null;

  return (
    <button
      onClick={toggle}
      disabled={busy}
      className={`inline-flex items-center justify-center rounded-lg border border-zinc-200 dark:border-zinc-700 p-2 transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-800 disabled:opacity-50 ${className}`}
      title={wishlisted ? "Remove from wishlist" : "Add to wishlist"}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill={wishlisted ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth={wishlisted ? 0 : 1.5}
        className={`h-5 w-5 ${wishlisted ? "text-red-500" : "text-zinc-500 dark:text-zinc-400"}`}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z"
        />
      </svg>
    </button>
  );
}
