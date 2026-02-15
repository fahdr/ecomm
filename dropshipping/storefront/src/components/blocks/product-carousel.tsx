/**
 * Product Carousel block -- a horizontally scrollable row of product cards
 * with snap scrolling, optional auto-advance, and dot navigation.
 *
 * Fetches products from the public API and displays them in a sleek
 * horizontal carousel with smooth scroll-snap behavior.
 *
 * **For Developers:**
 *   This is a **client component** (``"use client"``).  Config options:
 *   - ``product_ids`` (string[])  -- Specific product IDs to show (optional).
 *   - ``auto_scroll`` (boolean)   -- Enable auto-advance (default false).
 *   - ``interval``    (number)    -- Auto-scroll interval in ms (default 4000).
 *   - ``show_prices`` (boolean)   -- Show prices below cards (default true).
 *   - ``title``       (string)    -- Section heading.
 *   - ``count``       (number)    -- Number of products to fetch (default 10).
 *
 * **For QA Engineers:**
 *   - Carousel scrolls horizontally with snap-to-card behavior.
 *   - Dot indicators reflect the current visible page.
 *   - Auto-scroll pauses on hover and resumes on mouse leave.
 *   - Arrow buttons navigate left/right by one viewport width.
 *
 * **For End Users:**
 *   Swipe or use the arrows to browse featured products in a scrollable row.
 *
 * @module blocks/product-carousel
 */

"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useStore } from "@/contexts/store-context";
import type { PaginatedProducts, Product } from "@/lib/types";

/** Props for the {@link ProductCarousel} component. */
interface ProductCarouselProps {
  config: Record<string, unknown>;
}

/**
 * Render a horizontal product carousel with snap scrolling and navigation.
 *
 * @param props - Component props.
 * @param props.config - Block configuration from the store theme.
 * @returns A section with a scrollable product carousel.
 */
export function ProductCarousel({ config }: ProductCarouselProps) {
  const store = useStore();
  const count = typeof config.count === "number" ? config.count : 10;
  const showPrices = config.show_prices !== false;
  const autoScroll = config.auto_scroll === true;
  const interval = typeof config.interval === "number" ? config.interval : 4000;
  const title = (config.title as string) || "Trending Now";

  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

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
      if (!cancelled && data) setProducts(data.items);
      if (!cancelled) setLoading(false);
    }
    fetchProducts();
    return () => { cancelled = true; };
  }, [store, count]);

  /** Calculate the number of visible "pages" based on card width. */
  const totalPages = Math.max(1, Math.ceil(products.length / 4));

  /** Scroll the carousel by one viewport width in the given direction. */
  const scrollBy = useCallback((direction: "left" | "right") => {
    const el = scrollRef.current;
    if (!el) return;
    const scrollAmount = el.clientWidth;
    el.scrollBy({
      left: direction === "right" ? scrollAmount : -scrollAmount,
      behavior: "smooth",
    });
  }, []);

  /** Track scroll position to update dot indicators. */
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    function onScroll() {
      if (!el) return;
      const page = Math.round(el.scrollLeft / el.clientWidth);
      setActiveIndex(Math.min(page, totalPages - 1));
    }
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, [totalPages]);

  /** Auto-scroll timer. */
  useEffect(() => {
    if (!autoScroll || isPaused || products.length === 0) return;
    const timer = setInterval(() => scrollBy("right"), interval);
    return () => clearInterval(timer);
  }, [autoScroll, isPaused, interval, scrollBy, products.length]);

  if (!store) return null;

  return (
    <section className="mx-auto max-w-7xl px-6 py-16">
      <div className="flex items-center justify-between mb-8">
        <h2 className="font-heading text-3xl font-bold tracking-tight">{title}</h2>
        <div className="flex gap-2">
          <button
            onClick={() => scrollBy("left")}
            className="p-2 rounded-full border border-theme-border hover:bg-theme-surface transition-colors"
            aria-label="Scroll left"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
          </button>
          <button
            onClick={() => scrollBy("right")}
            className="p-2 rounded-full border border-theme-border hover:bg-theme-surface transition-colors"
            aria-label="Scroll right"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6"/></svg>
          </button>
        </div>
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="flex gap-4 overflow-hidden">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex-none w-[calc(25%-12px)] theme-card animate-pulse">
              <div className="aspect-square bg-theme-border" />
              <div className="p-4 space-y-2">
                <div className="h-4 bg-theme-border rounded w-3/4" />
                <div className="h-5 bg-theme-border rounded w-1/3" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Carousel */}
      {!loading && products.length > 0 && (
        <>
          <div
            ref={scrollRef}
            onMouseEnter={() => setIsPaused(true)}
            onMouseLeave={() => setIsPaused(false)}
            className="flex gap-4 overflow-x-auto snap-x snap-mandatory scrollbar-hide pb-2"
            style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
          >
            {products.map((product) => (
              <Link
                key={product.id}
                href={`/products/${product.slug}`}
                className="flex-none w-[calc(50%-8px)] sm:w-[calc(33.333%-11px)] lg:w-[calc(25%-12px)] snap-start group"
              >
                <div className="theme-card overflow-hidden">
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
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 text-theme-muted opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z" />
                        </svg>
                      </div>
                    )}
                  </div>
                  <div className="p-4">
                    <h3 className="font-medium text-sm line-clamp-2 mb-1">{product.title}</h3>
                    {showPrices && (
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
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* Dot indicators */}
          {totalPages > 1 && (
            <div className="flex justify-center gap-2 mt-4">
              {Array.from({ length: totalPages }).map((_, i) => (
                <button
                  key={i}
                  onClick={() => {
                    const el = scrollRef.current;
                    if (el) el.scrollTo({ left: i * el.clientWidth, behavior: "smooth" });
                  }}
                  className={`w-2 h-2 rounded-full transition-all duration-300 ${
                    i === activeIndex
                      ? "bg-theme-primary w-6"
                      : "bg-theme-border hover:bg-theme-muted"
                  }`}
                  aria-label={`Go to page ${i + 1}`}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* Empty state */}
      {!loading && products.length === 0 && (
        <div className="text-center py-12">
          <p className="text-theme-muted">No products available yet.</p>
        </div>
      )}
    </section>
  );
}
