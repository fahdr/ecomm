/**
 * Refunds management page for a store.
 *
 * Displays all refund requests in a table with status badges, amounts,
 * reasons, and action buttons to process pending refunds. Provides
 * summary statistics and filtering by refund status.
 *
 * **For End Users:**
 *   View and process refund requests from your customers. Approve
 *   legitimate refunds to issue them through your payment processor,
 *   or deny invalid requests with a reason.
 *
 * **For QA Engineers:**
 *   - Refunds load from ``GET /api/v1/stores/{store_id}/refunds``.
 *   - Processing a refund calls ``POST /api/v1/stores/{store_id}/refunds/{id}/process``
 *     with ``{ action: "approve" | "deny" }``.
 *   - Status badges: pending (outline), approved (default), denied (destructive),
 *     processed (secondary).
 *   - The filter dropdown resets the displayed list by status.
 *
 * **For Developers:**
 *   - Uses ``useStore()`` from store context for the store ID.
 *   - Wrapped in ``PageTransition`` for consistent entrance animation.
 *   - ``handleProcess()`` handles both approve and deny actions.
 *   - Refetches the list after every moderation action.
 *
 * **For Project Managers:**
 *   Implements Feature 14 (Refunds) from the backlog. Covers the list
 *   and approve/deny workflows; automatic Stripe refund processing
 *   integration is a follow-up task.
 */

"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition } from "@/components/motion-wrappers";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

/**
 * Shape of a refund returned by the backend API.
 *
 * The backend ``RefundResponse`` returns ``order_id`` (not ``order_number``)
 * and ``customer_email`` (not ``customer_name``). Monetary ``amount`` may
 * arrive as a Decimal string (e.g. ``"49.99"``).
 */
interface Refund {
  id: string;
  store_id: string;
  order_id: string;
  customer_email: string;
  reason: string;
  reason_details: string | null;
  amount: number | string;
  status: "pending" | "approved" | "rejected" | "processing" | "completed";
  stripe_refund_id: string | null;
  admin_notes: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * Get the badge variant for a refund status.
 * @param status - The refund's current status.
 * @returns A badge variant string.
 */
function refundStatusVariant(
  status: Refund["status"]
): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "approved":
    case "completed":
      return "default";
    case "processing":
      return "secondary";
    case "rejected":
      return "destructive";
    case "pending":
      return "outline";
    default:
      return "secondary";
  }
}

/**
 * Format a number or Decimal string as USD currency with decimals.
 * @param value - The numeric value (may be a Decimal string from the backend).
 * @returns Formatted currency string.
 */
function formatAmount(value: number | string): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(Number(value));
}

/**
 * RefundsPage is the main page component for managing store refunds.
 *
 * Fetches refunds from the API with optional status filtering, displays
 * summary statistics, and provides approve/deny actions with a deny
 * dialog for admin notes. Uses the store context for the store ID and
 * PageTransition for entrance animation.
 *
 * @returns The rendered refunds management page.
 */
export default function RefundsPage() {
  const { store } = useStore();
  const storeId = store!.id;
  const { user, loading: authLoading } = useAuth();

  const [refunds, setRefunds] = useState<Refund[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [processing, setProcessing] = useState<string | null>(null);

  // Deny dialog state.
  const [denyDialogOpen, setDenyDialogOpen] = useState(false);
  const [denyingRefund, setDenyingRefund] = useState<Refund | null>(null);
  const [denyNotes, setDenyNotes] = useState("");

  /**
   * Fetch all refunds for this store, optionally filtered by status.
   */
  const fetchRefunds = useCallback(async () => {
    setLoading(true);
    let url = `/api/v1/stores/${storeId}/refunds`;
    if (statusFilter !== "all") {
      url += `?status=${statusFilter}`;
    }
    const result = await api.get<{ items: Refund[]; total: number } | Refund[]>(url);
    if (result.data) {
      // Backend returns PaginatedRefundResponse with items wrapper
      const raw = result.data as any;
      setRefunds(Array.isArray(raw) ? raw : raw.items ?? []);
      setError(null);
    } else {
      setError(result.error?.message || "Failed to load refunds");
    }
    setLoading(false);
  }, [storeId, statusFilter]);

  useEffect(() => {
    if (authLoading || !user) return;
    fetchRefunds();
  }, [storeId, user, authLoading, statusFilter, fetchRefunds]);

  /**
   * Process a refund by approving it.
   * @param refundId - The ID of the refund to approve.
   */
  async function handleApprove(refundId: string) {
    setProcessing(refundId);
    const result = await api.post<Refund>(
      `/api/v1/stores/${storeId}/refunds/${refundId}/process`,
      { action: "approve" }
    );
    if (result.error) {
      setError(result.error.message);
    }
    setProcessing(null);
    fetchRefunds();
  }

  /**
   * Open the deny dialog for a specific refund.
   * @param refund - The refund to deny.
   */
  function openDenyDialog(refund: Refund) {
    setDenyingRefund(refund);
    setDenyNotes("");
    setDenyDialogOpen(true);
  }

  /**
   * Process a refund denial with optional admin notes.
   */
  async function handleDeny() {
    if (!denyingRefund) return;
    setProcessing(denyingRefund.id);
    const result = await api.post<Refund>(
      `/api/v1/stores/${storeId}/refunds/${denyingRefund.id}/process`,
      { action: "deny", admin_notes: denyNotes.trim() || null }
    );
    if (result.error) {
      setError(result.error.message);
    }
    setProcessing(null);
    setDenyDialogOpen(false);
    setDenyingRefund(null);
    setDenyNotes("");
    fetchRefunds();
  }

  /** Compute summary stats from current refund data. */
  const stats = {
    total: refunds.length,
    pending: refunds.filter((r) => r.status === "pending").length,
    totalAmount: refunds.reduce((sum, r) => sum + Number(r.amount), 0),
    approvedAmount: refunds
      .filter((r) => r.status === "approved" || r.status === "completed")
      .reduce((sum, r) => sum + Number(r.amount), 0),
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
          <p className="text-sm text-muted-foreground tracking-wide">Loading refunds...</p>
        </div>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Page heading and filter */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold font-heading">Refunds</h1>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Filter status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Refunds</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="denied">Denied</SelectItem>
              <SelectItem value="processed">Processed</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {error && (
          <Card className="border-destructive/50">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Summary cards */}
        <div className="grid gap-4 sm:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Requests
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums">{stats.total}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Pending
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
                Total Requested
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums">
                {formatAmount(stats.totalAmount)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Approved / Processed
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums text-red-600">
                {formatAmount(stats.approvedAmount)}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Refunds table */}
        {refunds.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
              <span className="text-2xl text-muted-foreground">R</span>
            </div>
            <h2 className="text-xl font-semibold font-heading">No refunds</h2>
            <p className="max-w-sm text-muted-foreground">
              {statusFilter !== "all"
                ? `No ${statusFilter} refunds found. Try a different filter.`
                : "Refund requests from customers will appear here."}
            </p>
          </div>
        ) : (
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-4">Order</TableHead>
                    <TableHead>Customer</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Reason</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Requested</TableHead>
                    <TableHead className="pr-4">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {refunds.map((refund) => (
                    <TableRow key={refund.id}>
                      <TableCell className="pl-4">
                        <Link
                          href={`/stores/${storeId}/orders/${refund.order_id}`}
                          className="font-mono font-semibold text-sm hover:underline"
                        >
                          #{refund.order_id.slice(0, 8)}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <p className="text-sm">
                          {refund.customer_email}
                        </p>
                      </TableCell>
                      <TableCell className="font-semibold tabular-nums">
                        {formatAmount(refund.amount)}
                      </TableCell>
                      <TableCell>
                        <p className="max-w-[200px] truncate text-sm text-muted-foreground">
                          {refund.reason}
                        </p>
                      </TableCell>
                      <TableCell>
                        <Badge variant={refundStatusVariant(refund.status)}>
                          {refund.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(refund.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="pr-4">
                        {refund.status === "pending" ? (
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={processing === refund.id}
                              onClick={() => handleApprove(refund.id)}
                              className="text-emerald-700 border-emerald-300 hover:bg-emerald-50 hover:text-emerald-800"
                            >
                              {processing === refund.id ? "..." : "Approve"}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={processing === refund.id}
                              onClick={() => openDenyDialog(refund)}
                              className="text-red-700 border-red-300 hover:bg-red-50 hover:text-red-800"
                            >
                              Deny
                            </Button>
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            {refund.updated_at
                              ? new Date(refund.updated_at).toLocaleDateString()
                              : "\u2014"}
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

        {/* Deny Refund Dialog */}
        <Dialog open={denyDialogOpen} onOpenChange={setDenyDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Deny Refund</DialogTitle>
              <DialogDescription>
                Deny the refund request for order #{denyingRefund?.order_id.slice(0, 8)}{" "}
                ({denyingRefund ? formatAmount(denyingRefund.amount) : ""}). You
                can optionally provide a reason for the customer.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="deny-notes">Admin Notes (optional)</Label>
                <Textarea
                  id="deny-notes"
                  placeholder="Reason for denying this refund..."
                  value={denyNotes}
                  onChange={(e) => setDenyNotes(e.target.value)}
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDenyDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                disabled={processing === denyingRefund?.id}
                onClick={handleDeny}
              >
                {processing === denyingRefund?.id ? "Denying..." : "Deny Refund"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </main>
    </PageTransition>
  );
}
