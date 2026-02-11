/**
 * Order detail page for the dashboard.
 *
 * Displays full order information including customer details, items,
 * totals, and status. Store owners can update the order status.
 *
 * **For Developers:**
 *   This is a client component. Order data is fetched from the
 *   authenticated orders API. Status updates use PATCH. The store ID
 *   comes from `useStore()` context; the order ID from URL params.
 *
 * **For QA Engineers:**
 *   - Shows order ID, customer email, status, and timestamps.
 *   - Lists all order items with title, variant, quantity, and price.
 *   - Status can be updated via a dropdown.
 *   - "Order not found" state is shown for invalid order IDs.
 *
 * **For End Users:**
 *   View the details of a specific order. Update the status as you
 *   process and ship the order.
 *
 * **For Project Managers:**
 *   Part of the core order management flow. Allows viewing details
 *   and updating order status (pending -> paid -> shipped -> delivered).
 */

"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition } from "@/components/motion-wrappers";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
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

/** Order item data. */
interface OrderItem {
  id: string;
  product_title: string;
  variant_name: string | null;
  quantity: number;
  unit_price: string;
}

/** Full order data. */
interface Order {
  id: string;
  store_id: string;
  customer_email: string;
  status: string;
  total: string;
  subtotal: string | null;
  discount_code: string | null;
  discount_amount: string | null;
  tax_amount: string | null;
  gift_card_amount: string | null;
  currency: string;
  stripe_session_id: string | null;
  shipping_address: Record<string, string> | null;
  notes: string | null;
  tracking_number: string | null;
  carrier: string | null;
  shipped_at: string | null;
  delivered_at: string | null;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
}

/**
 * Map order status to badge variant for visual differentiation.
 * @param status - The order status string.
 * @returns A badge variant suitable for the shadcn Badge component.
 */
function statusBadge(status: string) {
  const map: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    pending: "outline",
    paid: "default",
    shipped: "secondary",
    delivered: "default",
    cancelled: "destructive",
  };
  return map[status] || "outline";
}

/**
 * Order detail page component.
 *
 * Renders full order information with items, totals, and a status
 * update dropdown.
 *
 * @param props - Page props containing the orderId parameter.
 * @returns The order detail page wrapped in a PageTransition.
 */
export default function OrderDetailPage({
  params,
}: {
  params: Promise<{ id: string; orderId: string }>;
}) {
  const { orderId } = use(params);
  const { store } = useStore();
  const storeId = store?.id ?? "";
  const { user, loading: authLoading } = useAuth();
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [updateSuccess, setUpdateSuccess] = useState(false);
  const [trackingNumber, setTrackingNumber] = useState("");
  const [carrier, setCarrier] = useState("");
  const [notes, setNotes] = useState("");
  const [notesSaving, setNotesSaving] = useState(false);
  const [notesSaved, setNotesSaved] = useState(false);

  useEffect(() => {
    if (authLoading || !user || !storeId) return;

    /**
     * Fetch the order record from the API.
     */
    async function fetchOrder() {
      const result = await api.get<Order>(
        `/api/v1/stores/${storeId}/orders/${orderId}`
      );
      if (result.error) {
        setNotFound(true);
      } else {
        setOrder(result.data);
        setNotes(result.data?.notes || "");
      }
      setLoading(false);
    }

    fetchOrder();
  }, [storeId, orderId, user, authLoading]);

  /**
   * Update the order status via PATCH request.
   *
   * @param newStatus - The new status string to set.
   */
  async function handleStatusUpdate(newStatus: string) {
    if (!order) return;
    setUpdating(true);
    setUpdateSuccess(false);

    const result = await api.patch<Order>(
      `/api/v1/stores/${storeId}/orders/${orderId}`,
      { status: newStatus }
    );

    if (result.data) {
      setOrder(result.data);
      setUpdateSuccess(true);
      setTimeout(() => setUpdateSuccess(false), 3000);
    }
    setUpdating(false);
  }

  /**
   * Mark the order as shipped with tracking information.
   */
  async function handleFulfill() {
    if (!order || !trackingNumber.trim()) return;
    setUpdating(true);
    setUpdateSuccess(false);

    const result = await api.post<Order>(
      `/api/v1/stores/${storeId}/orders/${orderId}/fulfill`,
      {
        tracking_number: trackingNumber.trim(),
        carrier: carrier.trim() || null,
      }
    );

    if (result.data) {
      setOrder(result.data);
      setUpdateSuccess(true);
      setTrackingNumber("");
      setCarrier("");
      setTimeout(() => setUpdateSuccess(false), 3000);
    }
    setUpdating(false);
  }

  /**
   * Mark the order as delivered.
   */
  async function handleDeliver() {
    if (!order) return;
    setUpdating(true);
    setUpdateSuccess(false);

    const result = await api.post<Order>(
      `/api/v1/stores/${storeId}/orders/${orderId}/deliver`,
      {}
    );

    if (result.data) {
      setOrder(result.data);
      setUpdateSuccess(true);
      setTimeout(() => setUpdateSuccess(false), 3000);
    }
    setUpdating(false);
  }

  /**
   * Save internal notes for the order (auto-save on blur).
   */
  async function handleSaveNotes() {
    if (!order) return;
    setNotesSaving(true);
    setNotesSaved(false);
    const result = await api.patch<Order>(
      `/api/v1/stores/${storeId}/orders/${orderId}`,
      { notes }
    );
    if (result.data) {
      setOrder(result.data);
      setNotesSaved(true);
      setTimeout(() => setNotesSaved(false), 2000);
    }
    setNotesSaving(false);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-muted-foreground">Loading order...</p>
      </div>
    );
  }

  if (notFound || !order) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20">
        <h2 className="text-xl font-semibold">Order not found</h2>
        <Link href={`/stores/${storeId}/orders`}>
          <Button variant="outline">Back to orders</Button>
        </Link>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Page heading */}
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-mono font-bold">
            {order.id.slice(0, 8)}...
          </h1>
          <Badge variant={statusBadge(order.status)}>{order.status}</Badge>
        </div>

        {/* Order Info */}
        <Card>
          <CardHeader>
            <CardTitle>Order Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Order ID</p>
                <p className="font-mono text-xs">{order.id}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Customer Email</p>
                <p>{order.customer_email}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Created</p>
                <p>{new Date(order.created_at).toLocaleString()}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Last Updated</p>
                <p>{new Date(order.updated_at).toLocaleString()}</p>
              </div>
              {order.stripe_session_id && (
                <div className="col-span-2">
                  <p className="text-muted-foreground">Stripe Session</p>
                  <p className="font-mono text-xs">{order.stripe_session_id}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Fulfillment */}
        <Card>
          <CardHeader>
            <CardTitle>Fulfillment</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {order.status === "paid" && (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Mark this order as shipped by entering the tracking information.
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label htmlFor="tracking">Tracking Number *</Label>
                    <Input
                      id="tracking"
                      value={trackingNumber}
                      onChange={(e) => setTrackingNumber(e.target.value)}
                      placeholder="e.g. 1Z999AA10123456784"
                    />
                  </div>
                  <div>
                    <Label htmlFor="carrier">Carrier</Label>
                    <Input
                      id="carrier"
                      value={carrier}
                      onChange={(e) => setCarrier(e.target.value)}
                      placeholder="e.g. USPS, FedEx, UPS"
                    />
                  </div>
                </div>
                <Button
                  onClick={handleFulfill}
                  disabled={updating || !trackingNumber.trim()}
                >
                  {updating ? "Shipping..." : "Mark as Shipped"}
                </Button>
              </div>
            )}

            {order.status === "shipped" && (
              <div className="space-y-3">
                <div className="rounded-lg border p-3 text-sm space-y-1">
                  <p>
                    <span className="text-muted-foreground">Tracking:</span>{" "}
                    <span className="font-mono">{order.tracking_number}</span>
                  </p>
                  {order.carrier && (
                    <p>
                      <span className="text-muted-foreground">Carrier:</span>{" "}
                      {order.carrier}
                    </p>
                  )}
                  {order.shipped_at && (
                    <p>
                      <span className="text-muted-foreground">Shipped:</span>{" "}
                      {new Date(order.shipped_at).toLocaleString()}
                    </p>
                  )}
                </div>
                <Button
                  onClick={handleDeliver}
                  disabled={updating}
                >
                  {updating ? "Updating..." : "Mark as Delivered"}
                </Button>
              </div>
            )}

            {order.status === "delivered" && (
              <div className="rounded-lg border border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950 p-3 text-sm space-y-1">
                <p className="font-medium text-green-700 dark:text-green-400">
                  Order Delivered
                </p>
                {order.tracking_number && (
                  <p>
                    <span className="text-muted-foreground">Tracking:</span>{" "}
                    <span className="font-mono">{order.tracking_number}</span>
                  </p>
                )}
                {order.carrier && (
                  <p>
                    <span className="text-muted-foreground">Carrier:</span>{" "}
                    {order.carrier}
                  </p>
                )}
                {order.shipped_at && (
                  <p>
                    <span className="text-muted-foreground">Shipped:</span>{" "}
                    {new Date(order.shipped_at).toLocaleString()}
                  </p>
                )}
                {order.delivered_at && (
                  <p>
                    <span className="text-muted-foreground">Delivered:</span>{" "}
                    {new Date(order.delivered_at).toLocaleString()}
                  </p>
                )}
              </div>
            )}

            {(order.status === "pending" || order.status === "cancelled") && (
              <p className="text-sm text-muted-foreground">
                {order.status === "pending"
                  ? "Awaiting payment confirmation before fulfillment."
                  : "This order has been cancelled."}
              </p>
            )}

            {updateSuccess && (
              <span className="text-sm text-green-600">Updated!</span>
            )}
          </CardContent>
        </Card>

        {/* Status Update */}
        <Card>
          <CardHeader>
            <CardTitle>Update Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <Select
                value={order.status}
                onValueChange={handleStatusUpdate}
                disabled={updating}
              >
                <SelectTrigger className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="paid">Paid</SelectItem>
                  <SelectItem value="shipped">Shipped</SelectItem>
                  <SelectItem value="delivered">Delivered</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
              {updating && (
                <span className="text-sm text-muted-foreground">Updating...</span>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Internal Notes */}
        <Card>
          <CardHeader>
            <CardTitle>Internal Notes</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              onBlur={handleSaveNotes}
              placeholder="Add internal notes about this order..."
              rows={3}
              className="resize-none"
            />
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {notesSaving && <span>Saving...</span>}
              {notesSaved && <span className="text-green-600">Saved</span>}
              {!notesSaving && !notesSaved && <span>Auto-saves on blur</span>}
            </div>
          </CardContent>
        </Card>

        {/* Shipping Address */}
        {order.shipping_address && (
          <Card>
            <CardHeader>
              <CardTitle>Shipping Address</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm space-y-0.5">
                {order.shipping_address.name && <p className="font-medium">{order.shipping_address.name}</p>}
                {order.shipping_address.line1 && <p>{order.shipping_address.line1}</p>}
                {order.shipping_address.line2 && <p>{order.shipping_address.line2}</p>}
                <p>
                  {order.shipping_address.city}
                  {order.shipping_address.state ? `, ${order.shipping_address.state}` : ""}{" "}
                  {order.shipping_address.postal_code}
                </p>
                {order.shipping_address.country && <p>{order.shipping_address.country}</p>}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Order Items */}
        <Card>
          <CardHeader>
            <CardTitle>Items ({order.items.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {order.items.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between rounded-lg border p-4"
                >
                  <div>
                    <p className="font-medium">{item.product_title}</p>
                    {item.variant_name && (
                      <p className="text-sm text-muted-foreground">
                        {item.variant_name}
                      </p>
                    )}
                  </div>
                  <div className="text-right text-sm">
                    <p>
                      {item.quantity} x ${Number(item.unit_price).toFixed(2)}
                    </p>
                    <p className="font-semibold">
                      ${(item.quantity * Number(item.unit_price)).toFixed(2)}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* Financial breakdown */}
            <div className="mt-4 border-t pt-4 space-y-2 text-sm">
              {order.subtotal != null && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Subtotal</span>
                  <span>${Number(order.subtotal).toFixed(2)}</span>
                </div>
              )}
              {order.discount_amount != null && Number(order.discount_amount) > 0 && (
                <div className="flex justify-between text-green-600">
                  <span>Discount{order.discount_code ? ` (${order.discount_code})` : ""}</span>
                  <span>-${Number(order.discount_amount).toFixed(2)}</span>
                </div>
              )}
              {order.tax_amount != null && Number(order.tax_amount) > 0 && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Tax</span>
                  <span>${Number(order.tax_amount).toFixed(2)}</span>
                </div>
              )}
              {order.gift_card_amount != null && Number(order.gift_card_amount) > 0 && (
                <div className="flex justify-between text-green-600">
                  <span>Gift Card</span>
                  <span>-${Number(order.gift_card_amount).toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between font-medium pt-2 border-t">
                <span>Total</span>
                <span className="text-lg">${Number(order.total).toFixed(2)} {order.currency}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>
    </PageTransition>
  );
}
