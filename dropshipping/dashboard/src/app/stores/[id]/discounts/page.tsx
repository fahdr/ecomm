/**
 * Discounts management page for a store.
 *
 * Lists all discount codes in a sortable table with status badges, usage
 * counts, and expiry dates. Provides a dialog form to create new percentage
 * or fixed-amount discounts with optional usage limits and expiry.
 *
 * **For End Users:**
 *   Create and manage discount codes for your store. Each code can be a
 *   percentage off or a fixed dollar amount. Set usage limits and expiry
 *   dates to control promotion lifecycles.
 *
 * **For QA Engineers:**
 *   - Discounts load from ``GET /api/v1/stores/{store_id}/discounts``.
 *   - Creating a discount calls ``POST /api/v1/stores/{store_id}/discounts``.
 *   - The "Create Discount" dialog validates required fields (code, type, value).
 *   - Expired discounts show a "expired" badge variant.
 *   - Active discounts with remaining uses show "active".
 *
 * **For Developers:**
 *   - Uses `useStore()` from the store context for the store ID.
 *   - Wrapped in `<PageTransition>` for consistent page entrance animations.
 *   - ``params`` is no longer unwrapped here; store ID comes from context.
 *
 * **For Project Managers:**
 *   Implements Feature 8 (Discounts) from the backlog. Covers create and list
 *   flows; edit/delete can be added in a follow-up iteration.
 */

"use client";

import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition } from "@/components/motion-wrappers";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

/** Shape of a discount returned by the backend API. */
interface Discount {
  id: string;
  code: string;
  discount_type: "percentage" | "fixed_amount";
  value: number;
  status: "active" | "expired" | "disabled";
  times_used: number;
  max_uses: number | null;
  minimum_order_amount: number | null;
  starts_at: string | null;
  expires_at: string | null;
  created_at: string;
}

/** Payload for creating a new discount. */
interface CreateDiscountPayload {
  code: string;
  discount_type: "percentage" | "fixed_amount";
  value: number;
  starts_at: string;
  max_uses?: number | null;
  minimum_order_amount?: number | null;
  expires_at?: string | null;
}

/**
 * Determine the badge variant based on discount status.
 * @param status - The current status of the discount.
 * @returns A badge variant string for the shadcn Badge component.
 */
function statusVariant(status: Discount["status"]): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "active":
      return "default";
    case "expired":
      return "secondary";
    case "disabled":
      return "outline";
    default:
      return "secondary";
  }
}

/**
 * Format a discount value for display.
 * @param type - Whether the discount is percentage or fixed.
 * @param value - The numeric value.
 * @returns A human-readable discount string (e.g. "25%" or "$10.00").
 */
function formatDiscountValue(type: Discount["discount_type"], value: number): string {
  return type === "percentage" ? `${value}%` : `$${Number(value).toFixed(2)}`;
}

/**
 * Discounts page component.
 *
 * Renders summary cards, a create-discount dialog, and a table of
 * all discount codes for the current store.
 *
 * @returns The discounts page wrapped in a PageTransition.
 */
export default function DiscountsPage() {
  const { store } = useStore();
  const storeId = store?.id ?? "";
  const { user, loading: authLoading } = useAuth();

  const [discounts, setDiscounts] = useState<Discount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create dialog state.
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Form fields.
  const [code, setCode] = useState("");
  const [discountType, setDiscountType] = useState<"percentage" | "fixed">("percentage");
  const [value, setValue] = useState("");
  const [usageLimit, setUsageLimit] = useState("");
  const [minimumOrder, setMinimumOrder] = useState("");
  const [expiresAt, setExpiresAt] = useState("");

  /**
   * Fetch all discounts for this store from the API.
   * Called on mount and after successful creation.
   */
  async function fetchDiscounts() {
    setLoading(true);
    const result = await api.get<{ items: Discount[]; total: number }>(
      `/api/v1/stores/${storeId}/discounts`
    );
    if (result.data) {
      setDiscounts(result.data.items ?? []);
      setError(null);
    } else {
      setError(result.error?.message || "Failed to load discounts");
    }
    setLoading(false);
  }

  useEffect(() => {
    if (authLoading || !user || !storeId) return;
    fetchDiscounts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storeId, user, authLoading]);

  /**
   * Reset the create form to its default empty state.
   */
  function resetForm() {
    setCode("");
    setDiscountType("percentage");
    setValue("");
    setUsageLimit("");
    setMinimumOrder("");
    setExpiresAt("");
    setCreateError(null);
  }

  /**
   * Handle submission of the create-discount form.
   * Validates input, sends POST to the API, and refreshes the list on success.
   * @param e - The form submission event.
   */
  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);

    const payload: CreateDiscountPayload = {
      code: code.trim().toUpperCase(),
      discount_type: discountType === "fixed" ? "fixed_amount" : "percentage",
      value: parseFloat(value),
      starts_at: new Date().toISOString(),
    };

    if (usageLimit) payload.max_uses = parseInt(usageLimit, 10);
    if (minimumOrder) payload.minimum_order_amount = parseFloat(minimumOrder);
    if (expiresAt) payload.expires_at = new Date(expiresAt).toISOString();

    const result = await api.post<Discount>(
      `/api/v1/stores/${storeId}/discounts`,
      payload
    );

    if (result.error) {
      setCreateError(result.error.message);
      setCreating(false);
      return;
    }

    setDialogOpen(false);
    resetForm();
    setCreating(false);
    fetchDiscounts();
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
          <p className="text-sm text-muted-foreground tracking-wide">Loading discounts...</p>
        </div>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Page heading with create button */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-heading font-bold">Discounts</h1>
          <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button>Create Discount</Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>Create Discount Code</DialogTitle>
                <DialogDescription>
                  Set up a new discount code for your customers. Codes are
                  automatically uppercased.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreate}>
                <div className="space-y-4 py-4">
                  {createError && (
                    <p className="text-sm text-destructive">{createError}</p>
                  )}
                  <div className="space-y-2">
                    <Label htmlFor="discount-code">Discount Code</Label>
                    <Input
                      id="discount-code"
                      placeholder="e.g. SUMMER25"
                      value={code}
                      onChange={(e) => setCode(e.target.value)}
                      required
                      className="font-mono uppercase tracking-wider"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="discount-type">Type</Label>
                      <Select
                        value={discountType}
                        onValueChange={(v) => setDiscountType(v as "percentage" | "fixed")}
                      >
                        <SelectTrigger id="discount-type">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="percentage">Percentage</SelectItem>
                          <SelectItem value="fixed">Fixed Amount</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="discount-value">
                        Value {discountType === "percentage" ? "(%)" : "($)"}
                      </Label>
                      <Input
                        id="discount-value"
                        type="number"
                        min="0"
                        step={discountType === "percentage" ? "1" : "0.01"}
                        max={discountType === "percentage" ? "100" : undefined}
                        placeholder={discountType === "percentage" ? "25" : "10.00"}
                        value={value}
                        onChange={(e) => setValue(e.target.value)}
                        required
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="usage-limit">Usage Limit</Label>
                      <Input
                        id="usage-limit"
                        type="number"
                        min="1"
                        placeholder="Unlimited"
                        value={usageLimit}
                        onChange={(e) => setUsageLimit(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="min-order">Min. Order ($)</Label>
                      <Input
                        id="min-order"
                        type="number"
                        min="0"
                        step="0.01"
                        placeholder="No minimum"
                        value={minimumOrder}
                        onChange={(e) => setMinimumOrder(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="expires-at">Expiry Date</Label>
                    <Input
                      id="expires-at"
                      type="datetime-local"
                      value={expiresAt}
                      onChange={(e) => setExpiresAt(e.target.value)}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" disabled={creating}>
                    {creating ? "Creating..." : "Create Discount"}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {error && (
          <Card className="border-destructive/50">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Summary cards */}
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Discounts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums">{discounts.length}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Active
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums text-emerald-600">
                {discounts.filter((d) => d.status === "active").length}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Redemptions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums">
                {discounts.reduce((sum, d) => sum + d.times_used, 0)}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Discounts table */}
        {discounts.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="text-5xl opacity-20">%</div>
            <h2 className="text-xl font-semibold">No discounts yet</h2>
            <p className="max-w-sm text-muted-foreground">
              Create your first discount code to start offering promotions to
              your customers.
            </p>
            <Button onClick={() => setDialogOpen(true)}>
              Create your first discount
            </Button>
          </div>
        ) : (
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-4">Code</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Value</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Uses</TableHead>
                    <TableHead>Min. Order</TableHead>
                    <TableHead>Expires</TableHead>
                    <TableHead className="pr-4">Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {discounts.map((discount) => (
                    <TableRow key={discount.id}>
                      <TableCell className="pl-4 font-mono font-semibold tracking-wider">
                        {discount.code}
                      </TableCell>
                      <TableCell className="capitalize">{discount.discount_type.replace("_", " ")}</TableCell>
                      <TableCell className="font-semibold">
                        {formatDiscountValue(discount.discount_type, discount.value)}
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusVariant(discount.status)}>
                          {discount.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="tabular-nums">
                        {discount.times_used}
                        {discount.max_uses ? ` / ${discount.max_uses}` : ""}
                      </TableCell>
                      <TableCell>
                        {discount.minimum_order_amount
                          ? `$${Number(discount.minimum_order_amount).toFixed(2)}`
                          : "\u2014"}
                      </TableCell>
                      <TableCell>
                        {discount.expires_at
                          ? new Date(discount.expires_at).toLocaleDateString()
                          : "\u2014"}
                      </TableCell>
                      <TableCell className="pr-4 text-muted-foreground">
                        {new Date(discount.created_at).toLocaleDateString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </main>
    </PageTransition>
  );
}
