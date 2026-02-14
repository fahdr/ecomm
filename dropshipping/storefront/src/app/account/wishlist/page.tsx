/**
 * Customer wishlist page.
 *
 * **For End Users:**
 *   View and manage products you've saved for later. Remove items
 *   or add them to your cart.
 *
 * **For QA Engineers:**
 *   - Fetches wishlist from ``GET /public/stores/{slug}/customers/me/wishlist``.
 *   - Remove button calls ``DELETE .../wishlist/{product_id}``.
 *   - Empty state shown when wishlist is empty.
 */

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useCustomerAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";

interface WishlistItem {
  id: string;
  product_id: string;
  product_title: string | null;
  product_slug: string | null;
  product_price: number | null;
  product_image: string | null;
  added_at: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function WishlistPage() {
  const { customer, loading: authLoading, getAuthHeaders } = useCustomerAuth();
  const store = useStore();
  const router = useRouter();
  const [items, setItems] = useState<WishlistItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !customer) {
      router.replace("/account/login");
    }
  }, [customer, authLoading, router]);

  useEffect(() => {
    if (!customer || !store) return;

    async function fetchWishlist() {
      const res = await fetch(
        `${API_BASE}/api/v1/public/stores/${store!.slug}/customers/me/wishlist`,
        { headers: getAuthHeaders() }
      );
      if (res.ok) {
        setItems(await res.json());
      }
      setLoading(false);
    }

    fetchWishlist();
  }, [customer, store, getAuthHeaders]);

  async function handleRemove(productId: string) {
    if (!store) return;
    await fetch(
      `${API_BASE}/api/v1/public/stores/${store.slug}/customers/me/wishlist/${productId}`,
      { method: "DELETE", headers: getAuthHeaders() }
    );
    setItems((prev) => prev.filter((item) => item.product_id !== productId));
  }

  if (authLoading || loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="size-6 animate-spin rounded-full border-2 border-theme-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-heading font-bold">Wishlist</h1>
        <Link
          href="/account"
          className="text-sm text-theme-muted hover:text-theme-primary"
        >
          Back to Account
        </Link>
      </div>

      {items.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-theme-muted mb-4">Your wishlist is empty.</p>
          <Link
            href="/products"
            className="inline-block rounded-lg bg-theme-primary px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            Browse Products
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex items-center gap-4 rounded-xl border border-theme bg-theme-surface p-4"
            >
              {item.product_image && (
                <img
                  src={item.product_image}
                  alt={item.product_title || "Product"}
                  className="size-16 rounded-lg object-cover"
                />
              )}
              <div className="flex-1 min-w-0">
                {item.product_slug ? (
                  <Link
                    href={`/products/${item.product_slug}`}
                    className="font-medium text-sm hover:text-theme-primary transition-colors truncate block"
                  >
                    {item.product_title || "Unknown Product"}
                  </Link>
                ) : (
                  <span className="font-medium text-sm truncate block">
                    {item.product_title || "Unknown Product"}
                  </span>
                )}
                {item.product_price != null && (
                  <p className="text-sm text-theme-muted">
                    ${Number(item.product_price).toFixed(2)}
                  </p>
                )}
              </div>
              <button
                onClick={() => handleRemove(item.product_id)}
                className="text-sm text-red-500 hover:text-red-700 transition-colors shrink-0"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
