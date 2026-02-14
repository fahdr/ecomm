/**
 * Product view tracker -- client component that tracks product views
 * in localStorage and renders the RecentlyViewed section.
 *
 * **For Developers:**
 *   Mount this at the bottom of the product detail page. It calls
 *   ``trackView()`` on mount and renders the ``RecentlyViewed`` component.
 *
 * @module components/product-view-tracker
 */

"use client";

import { useEffect } from "react";
import { trackView, RecentlyViewed } from "./recently-viewed";

/** Props for the view tracker. */
interface ProductViewTrackerProps {
  slug: string;
}

/**
 * Track a product view on mount and render recently viewed products.
 *
 * @param props - Component props.
 * @param props.slug - The current product slug.
 * @returns The RecentlyViewed component.
 */
export function ProductViewTracker({ slug }: ProductViewTrackerProps) {
  useEffect(() => {
    trackView(slug);
  }, [slug]);

  return <RecentlyViewed currentSlug={slug} />;
}
