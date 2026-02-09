/**
 * Reviews Block -- a client-side section that fetches and displays recent
 * customer reviews for the store, along with an aggregate average rating.
 *
 * Unlike the per-product ``ProductReviews`` component, this block shows
 * reviews across all products in the store, giving homepage visitors
 * social proof and confidence to purchase.
 *
 * **For Developers:**
 *   This is a **client component** (``"use client"``).  It fetches reviews
 *   from the store-wide reviews endpoint (distinct from the per-product
 *   endpoint).  The store slug is obtained from the ``useStore()`` context
 *   hook.  The ``count`` config value controls how many reviews to display
 *   (default 6).
 *
 *   The star display uses inline SVG for zero runtime dependency.  The
 *   average rating is derived from the API response.
 *
 * **For QA Engineers:**
 *   - If the store context is null, the block renders nothing.
 *   - If the API returns no reviews, an empty state message is shown.
 *   - ``count`` defaults to 6.
 *   - Star ratings render as filled (amber) or outlined (muted) SVGs.
 *   - Average rating is displayed with one decimal place.
 *   - Customer names fall back to "Anonymous" if null.
 *   - Verified purchase badges are shown when applicable.
 *   - Review dates are formatted as "Mon DD, YYYY".
 *   - Loading state shows an animated spinner.
 *
 * **For Project Managers:**
 *   The reviews block provides social proof on the homepage.  Positive
 *   reviews build customer trust and can increase conversion rates.  The
 *   number of reviews shown is configurable through the theme editor.
 *
 * **For End Users:**
 *   Read what other customers have to say about their purchases.  Star
 *   ratings and written reviews help you make informed buying decisions.
 *
 * @module blocks/reviews-block
 */

"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useStore } from "@/contexts/store-context";
import type { PaginatedReviews, Review } from "@/lib/types";

/**
 * Props accepted by the {@link ReviewsBlock} component.
 */
interface ReviewsBlockProps {
  /**
   * Block configuration object.  Expected keys:
   * - ``count`` (number) -- Number of reviews to display (default 6).
   */
  config: Record<string, unknown>;
}

/**
 * Render a homepage reviews section with average rating and review cards.
 *
 * @param props - Component props.
 * @param props.config - Block configuration from the store theme.
 * @returns A section with an average rating header and review cards, a
 *          loading indicator, or an empty state.
 */
export function ReviewsBlock({ config }: ReviewsBlockProps) {
  const store = useStore();
  const count = typeof config.count === "number" ? config.count : 6;

  const [reviews, setReviews] = useState<Review[]>([]);
  const [averageRating, setAverageRating] = useState<number | null>(null);
  const [totalReviews, setTotalReviews] = useState(0);
  const [loading, setLoading] = useState(true);

  /**
   * Fetch store-wide reviews from the public API on mount.
   */
  useEffect(() => {
    if (!store) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function fetchReviews() {
      const { data } = await api.get<PaginatedReviews>(
        `/api/v1/public/stores/${encodeURIComponent(store!.slug)}/reviews?per_page=${count}`
      );
      if (!cancelled && data) {
        setReviews(data.items);
        setTotalReviews(data.total);
        setAverageRating(
          data.average_rating ? Number(data.average_rating) : null
        );
      }
      if (!cancelled) {
        setLoading(false);
      }
    }

    fetchReviews();
    return () => {
      cancelled = true;
    };
  }, [store, count]);

  // Don't render anything if no store context
  if (!store) return null;

  return (
    <section className="mx-auto max-w-7xl px-6 py-16">
      <h2 className="font-heading text-3xl font-bold tracking-tight mb-2 text-center">
        What Our Customers Say
      </h2>

      {/* Average rating header */}
      {averageRating !== null && totalReviews > 0 && (
        <div className="flex items-center justify-center gap-3 mb-10">
          <StarDisplay rating={averageRating} size="lg" />
          <span className="text-theme-muted text-sm">
            {averageRating.toFixed(1)} out of 5 ({totalReviews}{" "}
            review{totalReviews !== 1 ? "s" : ""})
          </span>
        </div>
      )}

      {/* Loading spinner */}
      {loading && (
        <div className="flex justify-center py-12">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-theme-border border-t-theme-primary" />
        </div>
      )}

      {/* Empty state */}
      {!loading && reviews.length === 0 && (
        <div className="text-center py-12">
          <p className="text-theme-muted">
            No reviews yet. Be the first to share your experience!
          </p>
        </div>
      )}

      {/* Review cards grid */}
      {!loading && reviews.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {reviews.map((review) => (
            <ReviewCard key={review.id} review={review} />
          ))}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/**
 * Star rating display.
 *
 * Renders five stars -- filled for the rated portion and outlined for the
 * remainder.
 *
 * @param props - Component props.
 * @param props.rating - Numeric rating (0--5).
 * @param props.size   - Visual size token: "sm" (16px) or "lg" (20px).
 * @returns A flex row of star SVGs.
 */
function StarDisplay({
  rating,
  size = "sm",
}: {
  rating: number;
  size?: "sm" | "lg";
}) {
  const sizeClass = size === "lg" ? "h-5 w-5" : "h-4 w-4";

  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => {
        const filled = star <= Math.round(rating);
        return (
          <svg
            key={star}
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill={filled ? "currentColor" : "none"}
            stroke="currentColor"
            strokeWidth={filled ? 0 : 1.5}
            className={`${sizeClass} ${
              filled
                ? "text-amber-500"
                : "text-theme-muted opacity-40"
            }`}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z"
            />
          </svg>
        );
      })}
    </div>
  );
}

/**
 * Single review card displaying reviewer info, star rating, and body text.
 *
 * @param props - Component props.
 * @param props.review - The review data to render.
 * @returns A theme-styled card with the review content.
 */
function ReviewCard({ review }: { review: Review }) {
  /**
   * Format the review creation date as "Mon DD, YYYY".
   */
  const formattedDate = new Date(review.created_at).toLocaleDateString(
    "en-US",
    { year: "numeric", month: "short", day: "numeric" }
  );

  return (
    <div className="theme-card p-5 flex flex-col">
      {/* Header: name, badge, date */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium text-sm">
              {review.customer_name || "Anonymous"}
            </span>
            {review.verified_purchase && (
              <span className="inline-flex items-center rounded-full bg-theme-primary/10 px-2 py-0.5 text-xs font-medium text-theme-primary">
                Verified
              </span>
            )}
          </div>
          <StarDisplay rating={review.rating} />
        </div>
        <span className="text-xs text-theme-muted shrink-0">
          {formattedDate}
        </span>
      </div>

      {/* Review title */}
      {review.title && (
        <h4 className="font-medium text-sm mb-1">{review.title}</h4>
      )}

      {/* Review body */}
      {review.body && (
        <p className="text-sm text-theme-muted leading-relaxed line-clamp-4 flex-1">
          {review.body}
        </p>
      )}
    </div>
  );
}
