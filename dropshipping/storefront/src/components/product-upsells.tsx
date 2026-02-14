/**
 * Product upsells / cross-sells component for the storefront.
 *
 * Displays "You might also like" product recommendations below the
 * main product details. Recommendations are fetched from the public
 * upsells API endpoint.
 *
 * **For Developers:**
 *   This is a client component (``"use client"``). Upsells are loaded
 *   on mount from the public API. The component handles loading,
 *   empty, and error states gracefully.
 *
 * **For QA Engineers:**
 *   - Only active upsell rules with active target products are shown.
 *   - Discount badges appear when a discount_percent is set.
 *   - Products link to their detail pages.
 *   - Section is hidden entirely if there are no upsells.
 *
 * **For End Users:**
 *   Discover related products that complement your current selection.
 *   Click any recommendation to see its full details.
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { UpsellRecommendation } from "@/lib/types";

/**
 * Props for the ProductUpsells component.
 */
interface ProductUpsellsProps {
  /** The store's URL slug. */
  storeSlug: string;
  /** The current product's URL slug. */
  productSlug: string;
}

/**
 * Upsell recommendations section.
 *
 * @param props - Store and product slugs for API calls.
 * @returns The upsells section, or null if there are no recommendations.
 */
export function ProductUpsells({ storeSlug, productSlug }: ProductUpsellsProps) {
  const [upsells, setUpsells] = useState<UpsellRecommendation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchUpsells() {
      const { data } = await api.get<UpsellRecommendation[]>(
        `/api/v1/public/stores/${encodeURIComponent(storeSlug)}/products/${encodeURIComponent(productSlug)}/upsells`
      );
      if (data && data.length > 0) {
        setUpsells(data);
      }
      setLoading(false);
    }
    fetchUpsells();
  }, [storeSlug, productSlug]);

  /* Do not render section if loading or no upsells available. */
  if (loading || upsells.length === 0) {
    return null;
  }

  return (
    <section className="mt-16 border-t border-zinc-200 dark:border-zinc-800 pt-12">
      <h3 className="text-2xl font-bold tracking-tight mb-8">
        You Might Also Like
      </h3>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {upsells.map((upsell) => (
          <UpsellCard key={upsell.target_product_id} upsell={upsell} />
        ))}
      </div>
    </section>
  );
}

/**
 * Individual upsell recommendation card.
 *
 * @param props - Component props.
 * @param props.upsell - The upsell recommendation data.
 * @returns A linked card with product image, title, price, and optional discount badge.
 */
function UpsellCard({ upsell }: { upsell: UpsellRecommendation }) {
  const price = Number(upsell.target_product_price);
  const discount = upsell.discount_percent ? Number(upsell.discount_percent) : null;
  const discountedPrice = discount ? price * (1 - discount / 100) : null;

  /* Map upsell_type to a label. */
  const typeLabels: Record<string, string> = {
    upsell: "Upgrade",
    cross_sell: "Pairs well",
    bundle: "Bundle deal",
  };
  const typeLabel = typeLabels[upsell.upsell_type] || "";

  return (
    <Link href={`/products/${upsell.target_product_slug}`} className="group">
      <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 overflow-hidden transition-shadow hover:shadow-md">
        {/* Image */}
        <div className="relative aspect-square bg-zinc-100 dark:bg-zinc-900 overflow-hidden">
          {upsell.target_product_image ? (
            <img
              src={upsell.target_product_image}
              alt={upsell.target_product_title}
              className="h-full w-full object-cover transition-transform group-hover:scale-105"
            />
          ) : (
            <div className="h-full w-full flex items-center justify-center">
              <div className="w-12 h-12 rounded-full bg-zinc-200 dark:bg-zinc-700" />
            </div>
          )}

          {/* Discount badge */}
          {discount && discount > 0 && (
            <span className="absolute top-2 left-2 rounded-md bg-rose-600 px-2 py-0.5 text-xs font-bold text-white">
              -{discount.toFixed(0)}%
            </span>
          )}

          {/* Type badge */}
          {typeLabel && (
            <span className="absolute top-2 right-2 rounded-md bg-white/80 dark:bg-zinc-900/80 px-2 py-0.5 text-xs font-medium backdrop-blur-sm text-zinc-600 dark:text-zinc-300">
              {typeLabel}
            </span>
          )}
        </div>

        {/* Info */}
        <div className="p-3">
          <h4 className="font-medium text-sm line-clamp-2 mb-1">
            {upsell.title || upsell.target_product_title}
          </h4>
          <div className="flex items-center gap-2">
            {discountedPrice !== null ? (
              <>
                <span className="text-sm font-semibold text-rose-600">
                  ${discountedPrice.toFixed(2)}
                </span>
                <span className="text-xs text-zinc-400 line-through">
                  ${price.toFixed(2)}
                </span>
              </>
            ) : (
              <span className="text-sm font-semibold">
                ${price.toFixed(2)}
              </span>
            )}
          </div>
          {upsell.description && (
            <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400 line-clamp-1">
              {upsell.description}
            </p>
          )}
        </div>
      </div>
    </Link>
  );
}
