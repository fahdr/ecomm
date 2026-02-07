/**
 * Customer wishlist page.
 *
 * Displays a grid of products the customer has saved to their wishlist.
 * Each item can be removed or added to the cart.
 *
 * **For Developers:**
 *   Client component fetching from the customer account wishlist API.
 *   Uses ``useCart()`` for add-to-cart functionality.
 *
 * **For QA Engineers:**
 *   - Empty state shows "Your wishlist is empty" with a shop link.
 *   - Each item shows product image, title, price, and action buttons.
 *   - "Remove" removes the item from the wishlist.
 *   - "Add to Cart" adds the product to the shopping cart.
 *   - Pagination controls appear when needed.
 *
 * **For End Users:**
 *   View products you've saved for later. Add them to your cart when ready.
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useCustomerAuth } from "@/contexts/customer-auth-context";
import { useStore } from "@/contexts/store-context";
import { useCart } from "@/contexts/cart-context";
import { api } from "@/lib/api";
import type { PaginatedWishlist, WishlistItem } from "@/lib/types";

/**
 * Wishlist page component.
 *
 * @returns A grid of wishlisted products with actions.
 */
export default function WishlistPage() {
  const { customer, loading: authLoading } = useCustomerAuth();
  const store = useStore();
  const { addItem } = useCart();
  const router = useRouter();

  const [wishlist, setWishlist] = useState<PaginatedWishlist | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !customer) {
      router.replace("/login");
    }
  }, [authLoading, customer, router]);

  const fetchWishlist = useCallback(async () => {
    if (!customer || !store) return;
    setLoading(true);
    const slug = encodeURIComponent(store.slug);
    const result = await api.get<PaginatedWishlist>(
      `/api/v1/public/stores/${slug}/account/wishlist?page=${page}&per_page=12`
    );
    if (result.data) {
      setWishlist(result.data);
    }
    setLoading(false);
  }, [customer, store, page]);

  useEffect(() => {
    fetchWishlist();
  }, [fetchWishlist]);

  async function handleRemove(itemId: string) {
    if (!store) return;
    const slug = encodeURIComponent(store.slug);
    await api.del(`/api/v1/public/stores/${slug}/account/wishlist/${itemId}`);
    fetchWishlist();
  }

  function handleAddToCart(item: WishlistItem) {
    const product = item.product;
    addItem({
      productId: product.id,
      variantId: null,
      title: product.title,
      variantName: null,
      price: Number(product.price),
      quantity: 1,
      image: product.images?.[0] || null,
      slug: product.slug,
    });
  }

  if (authLoading || loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-zinc-500 dark:text-zinc-400">Loading wishlist...</p>
      </div>
    );
  }

  return (
    <div className="py-12">
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-4 mb-8">
          <Link
            href="/account"
            className="text-sm text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
          >
            Account
          </Link>
          <span className="text-zinc-300 dark:text-zinc-600">/</span>
          <h2 className="text-2xl font-bold tracking-tight">Wishlist</h2>
        </div>

        {!wishlist || wishlist.items.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-zinc-500 dark:text-zinc-400 mb-4">
              Your wishlist is empty.
            </p>
            <Link
              href="/products"
              className="text-sm font-medium text-zinc-900 dark:text-zinc-100 hover:underline"
            >
              Browse products
            </Link>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {wishlist.items.map((item) => (
                <div
                  key={item.id}
                  className="rounded-lg border border-zinc-200 dark:border-zinc-800 overflow-hidden"
                >
                  <Link href={`/products/${item.product.slug}`}>
                    {item.product.images?.[0] ? (
                      <img
                        src={item.product.images[0]}
                        alt={item.product.title}
                        className="h-48 w-full object-cover"
                      />
                    ) : (
                      <div className="h-48 w-full bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center">
                        <div className="h-12 w-12 rounded-full bg-zinc-200 dark:bg-zinc-700" />
                      </div>
                    )}
                  </Link>
                  <div className="p-4">
                    <Link href={`/products/${item.product.slug}`}>
                      <h3 className="font-medium hover:underline truncate">
                        {item.product.title}
                      </h3>
                    </Link>
                    <p className="text-lg font-semibold mt-1">
                      ${Number(item.product.price).toFixed(2)}
                    </p>
                    <div className="flex gap-2 mt-3">
                      <button
                        onClick={() => handleAddToCart(item)}
                        className="flex-1 rounded-lg bg-zinc-900 dark:bg-zinc-100 px-3 py-2 text-xs font-medium text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors"
                      >
                        Add to Cart
                      </button>
                      <button
                        onClick={() => handleRemove(item.id)}
                        className="rounded-lg border border-zinc-300 dark:border-zinc-700 px-3 py-2 text-xs text-zinc-500 hover:text-red-500 hover:border-red-300 transition-colors"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {wishlist.pages > 1 && (
              <div className="flex items-center justify-center gap-4 mt-8">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="rounded-lg border border-zinc-300 dark:border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-50 dark:hover:bg-zinc-800 disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="text-sm text-zinc-500">
                  Page {page} of {wishlist.pages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(wishlist!.pages, p + 1))}
                  disabled={page >= wishlist.pages}
                  className="rounded-lg border border-zinc-300 dark:border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-50 dark:hover:bg-zinc-800 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
