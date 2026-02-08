/**
 * Fraud Detection page.
 *
 * Displays all fraud checks for store orders, showing risk levels, risk
 * scores, flagged status, and the associated order. Provides a review
 * action to mark fraud checks as reviewed.
 *
 * **For End Users:**
 *   Monitor suspicious orders with automated risk scoring. Each order
 *   is assigned a risk level (low, medium, high, critical) and a numeric
 *   score. Review flagged orders to approve or reject them.
 *
 * **For Developers:**
 *   - Fetches fraud checks via `GET /api/v1/stores/{store_id}/fraud-checks`.
 *   - Reviews a check via `POST /api/v1/stores/{store_id}/fraud-checks/{id}/review`.
 *   - Risk levels: "low", "medium", "high", "critical".
 *
 * **For QA Engineers:**
 *   - Verify fraud checks display with correct risk level badges.
 *   - Verify that the review action changes the status to "reviewed".
 *   - Verify that the risk score displays as a numeric value.
 *   - Verify that flagged orders are visually distinguished.
 *   - Verify empty state when no fraud checks exist.
 *
 * **For Project Managers:**
 *   This page corresponds to Feature 28 (Fraud) in the backlog.
 *   Fraud detection protects store owners from fraudulent orders.
 */

"use client";

import { useEffect, useState, use } from "react";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

/** Shape of a fraud check returned by the API. */
interface FraudCheck {
  id: string;
  order_id: string;
  order_number: string;
  risk_level: "low" | "medium" | "high" | "critical";
  risk_score: number;
  is_flagged: boolean;
  status: "pending" | "reviewed" | "approved" | "rejected";
  reasons: string[];
  checked_at: string;
  reviewed_at: string | null;
}

/**
 * FraudDetectionPage renders the fraud check listing with review actions.
 *
 * @param params - Route parameters containing the store ID.
 * @returns The rendered fraud detection page.
 */
export default function FraudDetectionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { user, loading: authLoading } = useAuth();
  const [checks, setChecks] = useState<FraudCheck[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewingId, setReviewingId] = useState<string | null>(null);

  /**
   * Fetch all fraud checks for this store.
   */
  async function fetchChecks() {
    setLoading(true);
    const result = await api.get<{ items: FraudCheck[]; total: number }>(
      `/api/v1/stores/${id}/fraud-checks`
    );
    if (result.error) {
      setError(result.error.message);
    } else {
      setChecks(result.data?.items ?? []);
    }
    setLoading(false);
  }

  useEffect(() => {
    if (authLoading || !user) return;
    fetchChecks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, user, authLoading]);

  /**
   * Mark a fraud check as reviewed.
   *
   * @param checkId - The ID of the fraud check to review.
   * @param action - The review action ("approved" or "rejected").
   */
  async function handleReview(
    checkId: string,
    action: "approved" | "rejected"
  ) {
    setReviewingId(checkId);
    const result = await api.post<FraudCheck>(
      `/api/v1/stores/${id}/fraud-checks/${checkId}/review`,
      { action }
    );
    if (result.data) {
      setChecks((prev) =>
        prev.map((c) => (c.id === checkId ? result.data! : c))
      );
    }
    setReviewingId(null);
  }

  /**
   * Map risk level to a Badge variant for visual severity.
   *
   * @param level - The risk level string.
   * @returns The appropriate Badge variant.
   */
  function riskVariant(
    level: FraudCheck["risk_level"]
  ): "default" | "secondary" | "outline" | "destructive" {
    switch (level) {
      case "low":
        return "secondary";
      case "medium":
        return "outline";
      case "high":
        return "default";
      case "critical":
        return "destructive";
      default:
        return "outline";
    }
  }

  /**
   * Map check status to a Badge variant.
   *
   * @param status - The fraud check status.
   * @returns The appropriate Badge variant.
   */
  function statusVariant(
    status: FraudCheck["status"]
  ): "default" | "secondary" | "outline" | "destructive" {
    switch (status) {
      case "approved":
        return "default";
      case "reviewed":
        return "secondary";
      case "pending":
        return "outline";
      case "rejected":
        return "destructive";
      default:
        return "outline";
    }
  }

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading fraud checks...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Link href="/stores" className="text-lg font-semibold hover:underline">
            Stores
          </Link>
          <span className="text-muted-foreground">/</span>
          <Link
            href={`/stores/${id}`}
            className="text-lg font-semibold hover:underline"
          >
            Store
          </Link>
          <span className="text-muted-foreground">/</span>
          <h1 className="text-lg font-semibold">Fraud Detection</h1>
        </div>
      </header>

      <main className="p-6">
        {error && (
          <Card className="mb-6 border-destructive/50">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Summary stats */}
        {checks.length > 0 && (
          <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Card>
              <CardContent className="pt-6">
                <p className="text-2xl font-bold">{checks.length}</p>
                <p className="text-sm text-muted-foreground">Total Checks</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-2xl font-bold">
                  {checks.filter((c) => c.is_flagged).length}
                </p>
                <p className="text-sm text-muted-foreground">Flagged</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-2xl font-bold">
                  {checks.filter((c) => c.risk_level === "high" || c.risk_level === "critical").length}
                </p>
                <p className="text-sm text-muted-foreground">High Risk</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-2xl font-bold">
                  {checks.filter((c) => c.status === "pending").length}
                </p>
                <p className="text-sm text-muted-foreground">Pending Review</p>
              </CardContent>
            </Card>
          </div>
        )}

        {checks.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="text-5xl opacity-20">&#128737;</div>
            <h2 className="text-xl font-semibold">No fraud checks recorded</h2>
            <p className="text-muted-foreground max-w-sm">
              Fraud checks are generated automatically when orders are placed.
              Results will appear here once your store starts receiving orders.
            </p>
          </div>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Fraud Checks</CardTitle>
              <CardDescription>
                Review suspicious orders and take action.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Order</TableHead>
                    <TableHead>Risk Level</TableHead>
                    <TableHead>Score</TableHead>
                    <TableHead>Flagged</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Reasons</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {checks.map((check) => (
                    <TableRow
                      key={check.id}
                      className={check.is_flagged ? "bg-destructive/5" : ""}
                    >
                      <TableCell>
                        <Link
                          href={`/stores/${id}/orders/${check.order_id}`}
                          className="font-medium hover:underline"
                        >
                          #{check.order_number}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge variant={riskVariant(check.risk_level)}>
                          {check.risk_level}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono">
                        {check.risk_score}
                      </TableCell>
                      <TableCell>
                        {check.is_flagged ? (
                          <Badge variant="destructive">Flagged</Badge>
                        ) : (
                          <span className="text-muted-foreground">--</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusVariant(check.status)}>
                          {check.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {check.reasons.length > 0 ? (
                            check.reasons.map((reason, idx) => (
                              <Badge
                                key={idx}
                                variant="outline"
                                className="text-xs"
                              >
                                {reason}
                              </Badge>
                            ))
                          ) : (
                            <span className="text-muted-foreground">--</span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        {check.status === "pending" && (
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              onClick={() =>
                                handleReview(check.id, "approved")
                              }
                              disabled={reviewingId === check.id}
                            >
                              Approve
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() =>
                                handleReview(check.id, "rejected")
                              }
                              disabled={reviewingId === check.id}
                            >
                              Reject
                            </Button>
                          </div>
                        )}
                        {check.status !== "pending" && (
                          <span className="text-sm text-muted-foreground">
                            {check.reviewed_at
                              ? new Date(
                                  check.reviewed_at
                                ).toLocaleDateString()
                              : "--"}
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
