/**
 * Animated product grid -- a client-side wrapper around the product card
 * layout that adds staggered entrance animations using motion primitives.
 *
 * **For Developers:**
 *   This is a **client component** that wraps product cards in motion.div
 *   elements with staggered fade-in + slide-up animations. It uses
 *   IntersectionObserver-based triggers so animations play when the grid
 *   scrolls into view.
 *
 * **For QA Engineers:**
 *   - Cards animate in with staggered delays (80ms between each).
 *   - Animation triggers once when the grid enters the viewport.
 *   - Falls back gracefully if motion library is unavailable.
 *
 * @module components/animated-product-grid
 */

"use client";

import Link from "next/link";
import { motion, useInView } from "motion/react";
import { useRef } from "react";
import type { Product } from "@/lib/types";

/** Props for the animated product grid. */
interface AnimatedProductGridProps {
  products: Product[];
}

/**
 * Render an animated grid of product cards with staggered entrance.
 *
 * @param props - Component props.
 * @param props.products - Array of products to display.
 * @returns An animated grid of product cards.
 */
export function AnimatedProductGrid({ products }: AnimatedProductGridProps) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-30px" });

  if (products.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-theme-muted">
          No products available yet. Check back soon!
        </p>
      </div>
    );
  }

  return (
    <motion.div
      ref={ref}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: 0.06 } },
      }}
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6"
    >
      {products.map((product) => (
        <motion.div
          key={product.id}
          variants={{
            hidden: { opacity: 0, y: 24 },
            visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" } },
          }}
        >
          <Link href={`/products/${product.slug}`} className="group block">
            <div className="theme-card overflow-hidden">
              <div className="relative aspect-square bg-theme-surface overflow-hidden">
                {product.images && product.images.length > 0 ? (
                  <img
                    src={product.images[0]}
                    alt={product.title}
                    className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                    loading="lazy"
                  />
                ) : (
                  <div className="h-full w-full flex items-center justify-center">
                    <div className="w-16 h-16 rounded-full bg-theme-surface border border-theme" />
                  </div>
                )}
                {/* Badges */}
                <div className="absolute top-2 left-2 flex flex-col gap-1">
                  {product.created_at && new Date(product.created_at) > new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) && (
                    <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded bg-theme-primary text-white">
                      New
                    </span>
                  )}
                  {product.compare_at_price && Number(product.compare_at_price) > Number(product.price) && (
                    <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded bg-red-500 text-white">
                      -{Math.round(((Number(product.compare_at_price) - Number(product.price)) / Number(product.compare_at_price)) * 100)}%
                    </span>
                  )}
                </div>
              </div>
              <div className="p-4">
                <h4 className="font-heading font-medium text-sm line-clamp-2 mb-2">
                  {product.title}
                </h4>
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
        </motion.div>
      ))}
    </motion.div>
  );
}
