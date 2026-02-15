/**
 * Product reviews component for the storefront.
 *
 * Displays approved reviews for a product with star ratings and a
 * submission form for new reviews. Reviews are fetched client-side
 * from the public API.
 *
 * **For Developers:**
 *   This is a client component (``"use client"``). It manages its own
 *   state for review loading, pagination, and the submission form.
 *   Reviews are fetched on mount and when the page changes.
 *
 * **For QA Engineers:**
 *   - Only approved reviews are displayed.
 *   - Average rating is shown if reviews exist.
 *   - Star rating distribution is shown visually.
 *   - The review form validates all required fields.
 *   - After submitting, a success message appears.
 *   - Pagination appears when more than 5 reviews exist.
 *
 * **For End Users:**
 *   Read reviews from other customers to help with your purchase
 *   decision. Submit your own review by filling out the form.
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { PaginatedReviews, Review, SubmitReviewPayload } from "@/lib/types";

/**
 * Props for the ProductReviews component.
 */
interface ProductReviewsProps {
  /** The store's URL slug. */
  storeSlug: string;
  /** The product's URL slug. */
  productSlug: string;
}

/**
 * Product reviews section with list, ratings summary, and submission form.
 *
 * @param props - Store and product slugs for API calls.
 * @returns The reviews section with rating summary, review list, and form.
 */
export function ProductReviews({ storeSlug, productSlug }: ProductReviewsProps) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [averageRating, setAverageRating] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const perPage = 5;

  /**
   * Fetch reviews from the public API.
   *
   * @param fetchPage - The page number to fetch.
   */
  const fetchReviews = useCallback(
    async (fetchPage: number) => {
      setLoading(true);
      const { data } = await api.get<PaginatedReviews>(
        `/api/v1/public/stores/${encodeURIComponent(storeSlug)}/products/${encodeURIComponent(productSlug)}/reviews?page=${fetchPage}&per_page=${perPage}`
      );
      if (data) {
        setReviews(data.items);
        setTotal(data.total);
        setTotalPages(data.pages);
        setAverageRating(data.average_rating ? Number(data.average_rating) : null);
      }
      setLoading(false);
    },
    [storeSlug, productSlug]
  );

  /* Fetch reviews on mount. */
  useEffect(() => {
    fetchReviews(1);
  }, [fetchReviews]);

  /** Handle page navigation. */
  function goToPage(newPage: number) {
    setPage(newPage);
    fetchReviews(newPage);
  }

  return (
    <section className="mt-16 border-t border-zinc-200 dark:border-zinc-800 pt-12">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h3 className="text-2xl font-bold tracking-tight">Customer Reviews</h3>
          {averageRating !== null && total > 0 && (
            <div className="mt-2 flex items-center gap-3">
              <StarDisplay rating={averageRating} size="lg" />
              <span className="text-sm text-zinc-500 dark:text-zinc-400">
                {averageRating.toFixed(1)} out of 5 ({total} review{total !== 1 ? "s" : ""})
              </span>
            </div>
          )}
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-lg border border-zinc-300 dark:border-zinc-700 px-4 py-2 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-colors"
        >
          {showForm ? "Cancel" : "Write a Review"}
        </button>
      </div>

      {/* Review submission form */}
      {showForm && (
        <ReviewForm
          storeSlug={storeSlug}
          productSlug={productSlug}
          onSubmitted={() => {
            setShowForm(false);
            fetchReviews(1);
            setPage(1);
          }}
        />
      )}

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-300 dark:border-zinc-600 border-t-zinc-900 dark:border-t-zinc-100" />
        </div>
      )}

      {/* Review list */}
      {!loading && reviews.length === 0 && (
        <div className="text-center py-8">
          <p className="text-zinc-500 dark:text-zinc-400">
            No reviews yet. Be the first to share your experience!
          </p>
        </div>
      )}

      {!loading && reviews.length > 0 && (
        <div className="space-y-6">
          {reviews.map((review) => (
            <ReviewCard key={review.id} review={review} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <div className="mt-8 flex items-center justify-center gap-4">
          <button
            onClick={() => goToPage(page - 1)}
            disabled={page <= 1}
            className="px-3 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-800 text-sm hover:bg-zinc-50 dark:hover:bg-zinc-900 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            &larr; Prev
          </button>
          <span className="text-sm text-zinc-500 dark:text-zinc-400">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => goToPage(page + 1)}
            disabled={page >= totalPages}
            className="px-3 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-800 text-sm hover:bg-zinc-50 dark:hover:bg-zinc-900 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Next &rarr;
          </button>
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/**
 * Star rating display component.
 *
 * Renders filled and empty stars to represent a rating value.
 *
 * @param props - Component props.
 * @param props.rating - The rating value (0-5).
 * @param props.size - Visual size: "sm" or "lg".
 * @returns A row of star SVGs.
 */
function StarDisplay({ rating, size = "sm" }: { rating: number; size?: "sm" | "lg" }) {
  const starSize = size === "lg" ? "h-5 w-5" : "h-4 w-4";

  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <svg
          key={star}
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill={star <= Math.round(rating) ? "currentColor" : "none"}
          stroke="currentColor"
          strokeWidth={star <= Math.round(rating) ? 0 : 1.5}
          className={`${starSize} ${
            star <= Math.round(rating)
              ? "text-amber-500"
              : "text-zinc-300 dark:text-zinc-600"
          }`}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z"
          />
        </svg>
      ))}
    </div>
  );
}

/**
 * Interactive star rating input for the review form.
 *
 * @param props - Component props.
 * @param props.value - Currently selected rating (0 = none).
 * @param props.onChange - Callback when a star is clicked.
 * @returns A row of clickable star buttons.
 */
function StarInput({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const [hovered, setHovered] = useState(0);

  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onMouseEnter={() => setHovered(star)}
          onMouseLeave={() => setHovered(0)}
          onClick={() => onChange(star)}
          className="transition-transform hover:scale-110"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill={star <= (hovered || value) ? "currentColor" : "none"}
            stroke="currentColor"
            strokeWidth={star <= (hovered || value) ? 0 : 1.5}
            className={`h-7 w-7 ${
              star <= (hovered || value)
                ? "text-amber-500"
                : "text-zinc-300 dark:text-zinc-600"
            }`}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z"
            />
          </svg>
        </button>
      ))}
    </div>
  );
}

/**
 * Single review card display.
 *
 * @param props - Component props.
 * @param props.review - The review data to display.
 * @returns A card with reviewer info, rating, and review text.
 */
function ReviewCard({ review }: { review: Review }) {
  const date = new Date(review.created_at);
  const formattedDate = date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });

  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 p-5">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium text-sm">
              {review.customer_name || "Anonymous"}
            </span>
            {review.verified_purchase && (
              <span className="inline-flex items-center rounded-full bg-emerald-50 dark:bg-emerald-900/30 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:text-emerald-400">
                Verified Purchase
              </span>
            )}
          </div>
          <StarDisplay rating={review.rating} />
        </div>
        <span className="text-xs text-zinc-400 dark:text-zinc-500 shrink-0">
          {formattedDate}
        </span>
      </div>

      {review.title && (
        <h4 className="font-medium text-sm mb-1">{review.title}</h4>
      )}
      {review.body && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
          {review.body}
        </p>
      )}
    </div>
  );
}

/**
 * Review submission form.
 *
 * @param props - Component props.
 * @param props.storeSlug - The store's URL slug.
 * @param props.productSlug - The product's URL slug.
 * @param props.onSubmitted - Callback after successful submission.
 * @returns A form with name, email, rating, title, and body fields.
 */
function ReviewForm({
  storeSlug,
  productSlug,
  onSubmitted,
}: {
  storeSlug: string;
  productSlug: string;
  onSubmitted: () => void;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [rating, setRating] = useState(0);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  /** Validate and submit the review. */
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    /* Client-side validation. */
    if (!name.trim()) {
      setError("Please enter your name.");
      return;
    }
    if (!email.trim() || !email.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }
    if (rating === 0) {
      setError("Please select a star rating.");
      return;
    }

    setSubmitting(true);

    const payload: SubmitReviewPayload = {
      customer_email: email.trim(),
      customer_name: name.trim(),
      rating,
      title: title.trim(),
      body: body.trim(),
    };

    const { error: apiError } = await api.post<Review>(
      `/api/v1/public/stores/${encodeURIComponent(storeSlug)}/products/${encodeURIComponent(productSlug)}/reviews`,
      payload
    );

    if (apiError) {
      setError(apiError.message || "Failed to submit review. Please try again.");
      setSubmitting(false);
      return;
    }

    setSuccess(true);
    setSubmitting(false);
    setTimeout(() => {
      onSubmitted();
    }, 2000);
  }

  if (success) {
    return (
      <div className="mb-8 rounded-lg border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/20 p-6 text-center">
        <p className="font-medium text-emerald-700 dark:text-emerald-400">
          Thank you for your review!
        </p>
        <p className="mt-1 text-sm text-emerald-600 dark:text-emerald-500">
          Your review has been submitted and is pending approval.
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-8 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6"
    >
      <h4 className="text-lg font-medium mb-4">Write a Review</h4>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1">
            Name *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
            className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
          />
        </div>

        {/* Email */}
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1">
            Email *
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
          />
        </div>
      </div>

      {/* Rating */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1">
          Rating *
        </label>
        <StarInput value={rating} onChange={setRating} />
      </div>

      {/* Title */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1">
          Review Title
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Summarize your experience"
          className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
        />
      </div>

      {/* Body */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1">
          Review
        </label>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Tell others about your experience with this product..."
          rows={4}
          className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400 resize-none"
        />
      </div>

      {/* Error */}
      {error && <p className="text-sm text-red-500 mb-4">{error}</p>}

      {/* Submit */}
      <button
        type="submit"
        disabled={submitting}
        className="rounded-lg bg-zinc-900 dark:bg-zinc-100 px-6 py-2.5 text-sm font-medium text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {submitting ? "Submitting..." : "Submit Review"}
      </button>
    </form>
  );
}
