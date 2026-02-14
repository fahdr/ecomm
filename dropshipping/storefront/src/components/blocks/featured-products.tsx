/**
 * Featured Products block -- a client-side grid of product cards fetched
 * from the store's public API.
 *
 * Displays a configurable number of products in a responsive grid layout.
 * Each card shows the product image, title, price, and links to the
 * product detail page.
 *
 * **For Developers:**
 *   This is a **client component** (``"use client"``).  It fetches products
 *   on mount via ``api.get`` using the store slug from ``useStore()``.
 *   The ``count`` config value controls how many products to request
 *   (default 8).  The ``columns`` config adjusts the grid layout
 *   (default 4).  A loading skeleton is shown during the fetch.
 *
 * **For QA Engineers:**
 *   - Products are fetched from ``GET /api/v1/public/stores/{slug}/products``.
 *   - If the store context is null, the block renders nothing.
 *   - If the API returns an error or empty list, a "no products" message appears.
 *   - Loading state shows animated placeholder cards.
 *   - Product images fall back to a neutral placeholder when missing.
 *   - ``count`` defaults to 8; ``columns`` defaults to 4.
 *   - Clicking a product card navigates to ``/products/{slug}``.
 *
 * **For Project Managers:**
 *   This block lets store owners highlight products on their homepage.
 *   The number of visible products and grid columns are configurable
 *   through the theme editor, giving owners flexibility over the layout.
 *
 * **For End Users:**
 *   Browse highlighted products directly from the homepage and click any
 *   card to view full product details.
 *
 * @module blocks/featured-products
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useStore } from "@/contexts/store-context";
import type { PaginatedProducts, Product } from "@/lib/types";

/**
 * Props accepted by the {@link FeaturedProducts} component.
 */
interface FeaturedProductsProps {
  /**
   * Block configuration object.  Expected keys:
   * - ``count``   (number) -- Number of products to display (default 8).
   * - ``columns`` (number) -- Number of grid columns on large screens (default 4).
   */
  config: Record<string, unknown>;
}

/**
 * Map a column count to the corresponding Tailwind grid-cols class for the
 * ``lg`` breakpoint.
 *
 * @param cols - Desired number of columns (2--6).
 * @returns A Tailwind ``lg:grid-cols-*`` class string.
 */
function gridColsClass(cols: number): string {
  const map: Record<number, string> = {
    2: "lg:grid-cols-2",
    3: "lg:grid-cols-3",
    4: "lg:grid-cols-4",
    5: "lg:grid-cols-5",
    6: "lg:grid-cols-6",
  };
  return map[cols] || "lg:grid-cols-4";
}

/**
 * Render a grid of featured product cards, fetched from the public API.
 *
 * @param props - Component props.
 * @param props.config - Block configuration from the store theme.
 * @returns A section with a product grid, loading skeleton, or empty state.
 */
export function FeaturedProducts({ config }: FeaturedProductsProps) {
  const store = useStore();
  const count = typeof config.count === "number" ? config.count : 8;
  const columns = typeof config.columns === "number" ? config.columns : 4;

  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  /**
   * Fetch products from the public API on component mount.
   * Requests ``count`` products sorted by creation date (newest first).
   */
  useEffect(() => {
    if (!store) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function fetchProducts() {
      const { data } = await api.get<PaginatedProducts>(
        `/api/v1/public/stores/${encodeURIComponent(store!.slug)}/products?per_page=${count}`
      );
      if (!cancelled && data) {
        setProducts(data.items);
      }
      if (!cancelled) {
        setLoading(false);
      }
    }

    fetchProducts();
    return () => {
      cancelled = true;
    };
  }, [store, count]);

  // Don't render anything if no store context is available
  if (!store) return null;

  return (
    <section className="mx-auto max-w-7xl px-6 py-16">
      <h2 className="font-heading text-3xl font-bold tracking-tight mb-8 text-center">
        Featured Products
      </h2>

      {/* Loading skeleton */}
      {loading && (
        <div className={`grid grid-cols-1 sm:grid-cols-2 ${gridColsClass(columns)} gap-6`}>
          {Array.from({ length: count }).map((_, i) => (
            <div key={i} className="theme-card overflow-hidden animate-pulse">
              <div className="aspect-square bg-theme-border" />
              <div className="p-4 space-y-3">
                <div className="h-4 rounded bg-theme-border w-3/4" />
                <div className="h-5 rounded bg-theme-border w-1/3" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && products.length === 0 && (
        <div className="text-center py-12">
          <p className="text-theme-muted">
            No products available yet. Check back soon!
          </p>
        </div>
      )}

      {/* Product grid */}
      {!loading && products.length > 0 && (
        <div className={`grid grid-cols-1 sm:grid-cols-2 ${gridColsClass(columns)} gap-6`}>
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </section>
  );
}

/**
 * Individual product card within the featured products grid.
 *
 * Displays the product image (or a placeholder), title, and formatted
 * price.  Wraps everything in a link to the product detail page.
 *
 * @param props - Component props.
 * @param props.product - The product data to render.
 * @returns A linked card element for the product.
 */
function ProductCard({ product }: { product: Product }) {
  return (
    <Link href={`/products/${product.slug}`} className="group">
      <div className="theme-card overflow-hidden">
        {/* Product image */}
        <div className="aspect-square bg-theme-surface overflow-hidden">
          {product.images && product.images.length > 0 ? (
            <img
              src={product.images[0]}
              alt={product.title}
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
              loading="lazy"
            />
          ) : (
            <div className="h-full w-full flex items-center justify-center bg-theme-border">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-12 w-12 text-theme-muted opacity-40"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z"
                />
              </svg>
            </div>
          )}
        </div>

        {/* Product info */}
        <div className="p-4">
          <h3 className="font-medium text-sm line-clamp-2 mb-2 min-h-[2.5rem]">
            {product.title}
          </h3>
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold text-theme-primary">
              ${Number(product.price).toFixed(2)}
            </span>
            {product.compare_at_price && (
              <span className="text-sm text-theme-muted line-through">
                ${Number(product.compare_at_price).toFixed(2)}
              </span>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
