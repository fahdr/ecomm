/**
 * Reviews moderation page for a store.
 *
 * Displays customer reviews in a filterable list with rating stars,
 * review text, product info, and moderation actions (approve/reject).
 * Store owners can filter by status to focus on pending reviews that
 * need attention.
 *
 * **For End Users:**
 *   Monitor what customers are saying about your products. Approve
 *   genuine reviews to display them on your storefront, or reject
 *   spam and inappropriate content.
 *
 * **For QA Engineers:**
 *   - Reviews load from ``GET /api/v1/stores/{store_id}/reviews``.
 *   - Approving calls ``PATCH /api/v1/stores/{store_id}/reviews/{id}``
 *     with ``{ status: "approved" }``.
 *   - Rejecting calls the same endpoint with ``{ status: "rejected" }``.
 *   - Filter by status: all, pending, approved, rejected.
 *   - Star ratings render as filled/empty characters (1-5 scale).
 *
 * **For Developers:**
 *   - ``renderStars()`` produces accessible text-based star ratings.
 *   - Moderation actions call ``handleModerate()`` which patches status.
 *   - The component refetches after each moderation action.
 *
 * **For Project Managers:**
 *   Implements Feature 12 (Reviews) from the backlog. Covers list and
 *   moderation flows; customer-facing review submission is on the
 *   storefront side.
 */

"use client";

import { useEffect, useState, use, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/** Shape of a review returned by the backend API. */
interface Review {
  id: string;
  product_id: string;
  product_title: string;
  customer_name: string;
  customer_email: string;
  rating: number;
  title: string | null;
  body: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
}

/**
 * Get the badge variant for a review status.
 * @param status - The review's moderation status.
 * @returns A badge variant string.
 */
function reviewStatusVariant(
  status: Review["status"]
): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "approved":
      return "default";
    case "pending":
      return "outline";
    case "rejected":
      return "destructive";
    default:
      return "secondary";
  }
}

/**
 * Render a star rating as text characters.
 * @param rating - The numeric rating (1-5).
 * @returns A string of filled and empty star characters.
 */
function renderStars(rating: number): string {
  const filled = "\u2605";
  const empty = "\u2606";
  return filled.repeat(rating) + empty.repeat(5 - rating);
}

/**
 * Get a color class for a star rating.
 * @param rating - The numeric rating (1-5).
 * @returns A Tailwind text color class.
 */
function ratingColor(rating: number): string {
  if (rating >= 4) return "text-amber-500";
  if (rating >= 3) return "text-amber-400";
  return "text-amber-300";
}

export default function ReviewsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: storeId } = use(params);
  const { user, loading: authLoading } = useAuth();

  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [moderating, setModerating] = useState<string | null>(null);

  /**
   * Fetch reviews for this store, optionally filtered by status.
   */
  const fetchReviews = useCallback(async () => {
    setLoading(true);
    let url = `/api/v1/stores/${storeId}/reviews`;
    if (statusFilter !== "all") {
      url += `?status=${statusFilter}`;
    }
    const result = await api.get<{ items: Review[]; total: number } | Review[]>(url);
    if (result.data) {
      // Backend returns PaginatedReviewResponse with items wrapper
      const raw = result.data as any;
      setReviews(Array.isArray(raw) ? raw : raw.items ?? []);
      setError(null);
    } else {
      setError(result.error?.message || "Failed to load reviews");
    }
    setLoading(false);
  }, [storeId, statusFilter]);

  useEffect(() => {
    if (authLoading || !user) return;
    fetchReviews();
  }, [storeId, user, authLoading, statusFilter, fetchReviews]);

  /**
   * Moderate a review by setting its status to approved or rejected.
   * @param reviewId - The ID of the review to moderate.
   * @param newStatus - The new status to apply.
   */
  async function handleModerate(
    reviewId: string,
    newStatus: "approved" | "rejected"
  ) {
    setModerating(reviewId);
    const result = await api.patch<Review>(
      `/api/v1/stores/${storeId}/reviews/${reviewId}`,
      { status: newStatus }
    );
    if (result.error) {
      setError(result.error.message);
    }
    setModerating(null);
    fetchReviews();
  }

  /** Compute summary statistics from the current review list. */
  const stats = {
    total: reviews.length,
    pending: reviews.filter((r) => r.status === "pending").length,
    approved: reviews.filter((r) => r.status === "approved").length,
    avgRating:
      reviews.length > 0
        ? (reviews.reduce((s, r) => s + r.rating, 0) / reviews.length).toFixed(1)
        : "\u2014",
  };

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
          <p className="text-sm text-muted-foreground tracking-wide">Loading reviews...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Breadcrumb header */}
      <header className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Link href="/stores" className="text-lg font-semibold hover:underline">
            Stores
          </Link>
          <span className="text-muted-foreground">/</span>
          <Link
            href={`/stores/${storeId}`}
            className="text-lg font-semibold hover:underline"
          >
            Store
          </Link>
          <span className="text-muted-foreground">/</span>
          <h1 className="text-lg font-semibold">Reviews</h1>
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="Filter status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Reviews</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
          </SelectContent>
        </Select>
      </header>

      <main className="mx-auto max-w-4xl p-6">
        {error && (
          <Card className="mb-6 border-destructive/50">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Summary cards */}
        <div className="mb-6 grid gap-4 sm:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Reviews
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums">{stats.total}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Pending Review
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums text-amber-600">
                {stats.pending}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Approved
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums text-emerald-600">
                {stats.approved}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Avg Rating
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums">{stats.avgRating}</p>
            </CardContent>
          </Card>
        </div>

        {/* Reviews list */}
        {reviews.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="text-4xl opacity-20">{renderStars(0)}</div>
            <h2 className="text-xl font-semibold">No reviews yet</h2>
            <p className="max-w-sm text-muted-foreground">
              {statusFilter !== "all"
                ? `No ${statusFilter} reviews found. Try a different filter.`
                : "Reviews will appear here once customers start rating your products."}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {reviews.map((review) => (
              <Card key={review.id} className="overflow-hidden">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <span
                          className={`text-lg tracking-wider ${ratingColor(review.rating)}`}
                          aria-label={`${review.rating} out of 5 stars`}
                        >
                          {renderStars(review.rating)}
                        </span>
                        <Badge variant={reviewStatusVariant(review.status)}>
                          {review.status}
                        </Badge>
                      </div>
                      {review.title && (
                        <CardTitle className="text-base">{review.title}</CardTitle>
                      )}
                      <CardDescription className="mt-1">
                        by <span className="font-medium text-foreground">{review.customer_name}</span>
                        {" on "}
                        <span className="font-medium text-foreground">{review.product_title}</span>
                        {" \u00B7 "}
                        {new Date(review.created_at).toLocaleDateString()}
                      </CardDescription>
                    </div>

                    {/* Moderation actions */}
                    {review.status === "pending" && (
                      <div className="flex gap-2 shrink-0">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={moderating === review.id}
                          onClick={() => handleModerate(review.id, "approved")}
                          className="text-emerald-700 border-emerald-300 hover:bg-emerald-50 hover:text-emerald-800"
                        >
                          {moderating === review.id ? "..." : "Approve"}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={moderating === review.id}
                          onClick={() => handleModerate(review.id, "rejected")}
                          className="text-red-700 border-red-300 hover:bg-red-50 hover:text-red-800"
                        >
                          {moderating === review.id ? "..." : "Reject"}
                        </Button>
                      </div>
                    )}
                    {review.status !== "pending" && (
                      <div className="flex gap-2 shrink-0">
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={moderating === review.id}
                          onClick={() =>
                            handleModerate(
                              review.id,
                              review.status === "approved" ? "rejected" : "approved"
                            )
                          }
                        >
                          {review.status === "approved" ? "Reject" : "Approve"}
                        </Button>
                      </div>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {review.body}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
