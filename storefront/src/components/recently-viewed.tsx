/**
 * Recently Viewed products -- displays a horizontal scrollable row of
 * products that the customer has recently viewed, stored in localStorage.
 *
 * **For Developers:**
 *   This is a **client component** that reads/writes product slugs to
 *   ``localStorage`` under the key ``recently_viewed``. It fetches product
 *   data from the public API by loading the full product list and filtering.
 *   Call ``trackView(slug)`` from product detail pages on mount.
 *
 * **For QA Engineers:**
 *   - Stores up to 8 product slugs in localStorage.
 *   - Current product is excluded from the "recently viewed" display.
 *   - Empty state (no history) renders nothing.
 *   - Horizontal scroll with snap behavior on mobile.
 *
 * **For End Users:**
 *   Quickly revisit products you've recently browsed.
 *
 * @module components/recently-viewed
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useStore } from "@/contexts/store-context";
import type { PaginatedProducts, Product } from "@/lib/types";

const STORAGE_KEY = "recently_viewed";
const MAX_ITEMS = 8;

/**
 * Track a product view by adding its slug to localStorage.
 *
 * @param slug - The product slug to track.
 */
export function trackView(slug: string) {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    const filtered = stored.filter((s: string) => s !== slug);
    filtered.unshift(slug);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered.slice(0, MAX_ITEMS)));
  } catch {
    // localStorage unavailable
  }
}

/** Props for the {@link RecentlyViewed} component. */
interface RecentlyViewedProps {
  /** Current product slug to exclude from the display. */
  currentSlug?: string;
}

/**
 * Render a horizontal row of recently viewed products.
 *
 * @param props - Component props.
 * @param props.currentSlug - Slug of the current product to exclude.
 * @returns A section with recently viewed product cards, or null if empty.
 */
export function RecentlyViewed({ currentSlug }: RecentlyViewedProps) {
  const store = useStore();
  const [products, setProducts] = useState<Product[]>([]);

  useEffect(() => {
    if (!store) return;
    let cancelled = false;

    async function load() {
      try {
        const stored: string[] = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
        const slugs = stored.filter((s) => s !== currentSlug);
        if (slugs.length === 0) return;

        const { data } = await api.get<PaginatedProducts>(
          `/api/v1/public/stores/${encodeURIComponent(store!.slug)}/products?per_page=50`
        );
        if (!cancelled && data) {
          const matched = slugs
            .map((s) => data.items.find((p) => p.slug === s))
            .filter((p): p is Product => !!p);
          setProducts(matched);
        }
      } catch {
        // Silently fail
      }
    }

    load();
    return () => { cancelled = true; };
  }, [store, currentSlug]);

  if (products.length === 0) return null;

  return (
    <section className="mx-auto max-w-7xl px-6 py-12">
      <h2 className="font-heading text-xl font-bold tracking-tight mb-6">
        Recently Viewed
      </h2>
      <div
        className="flex gap-4 overflow-x-auto snap-x snap-mandatory pb-2"
        style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
      >
        {products.map((product) => (
          <Link
            key={product.id}
            href={`/products/${product.slug}`}
            className="flex-none w-[180px] sm:w-[200px] snap-start group"
          >
            <div className="theme-card overflow-hidden">
              <div className="aspect-square bg-theme-surface overflow-hidden">
                {product.images?.[0] ? (
                  <img
                    src={product.images[0]}
                    alt={product.title}
                    className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                    loading="lazy"
                  />
                ) : (
                  <div className="h-full w-full flex items-center justify-center bg-theme-border">
                    <div className="w-10 h-10 rounded-full bg-theme-surface" />
                  </div>
                )}
              </div>
              <div className="p-3">
                <h4 className="font-medium text-xs line-clamp-1 mb-1">{product.title}</h4>
                <span className="text-sm font-semibold text-theme-primary">
                  ${Number(product.price).toFixed(2)}
                </span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
