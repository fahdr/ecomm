/**
 * Customer order detail page.
 *
 * **For End Users:**
 *   View the full details of a past order including items, shipping
 *   address, and price breakdown.
 *
 * **For QA Engineers:**
 *   - Fetches order from ``GET /public/stores/{slug}/customers/me/orders/{id}``.
 *   - Shows items, shipping address, and financial breakdown.
 *   - 404 if the order doesn't belong to this customer.
 */

"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useCustomerAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";

interface OrderItem {
  id: string;
  product_title: string;
  variant_name: string | null;
  quantity: number;
  unit_price: number;
}

interface OrderDetail {
  id: string;
  status: string;
  total: number;
  subtotal: number | null;
  discount_code: string | null;
  discount_amount: number | null;
  tax_amount: number | null;
  gift_card_amount: number | null;
  currency: string;
  shipping_address: string | null;
  tracking_number: string | null;
  carrier: string | null;
  shipped_at: string | null;
  delivered_at: string | null;
  created_at: string;
  items: OrderItem[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function OrderDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { customer, loading: authLoading, getAuthHeaders } = useCustomerAuth();
  const store = useStore();
  const router = useRouter();
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !customer) {
      router.replace("/account/login");
    }
  }, [customer, authLoading, router]);

  useEffect(() => {
    if (!customer || !store) return;

    async function fetchOrder() {
      const res = await fetch(
        `${API_BASE}/api/v1/public/stores/${store!.slug}/customers/me/orders/${id}`,
        { headers: getAuthHeaders() }
      );
      if (res.ok) {
        setOrder(await res.json());
      }
      setLoading(false);
    }

    fetchOrder();
  }, [customer, store, id, getAuthHeaders]);

  if (authLoading || loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="size-6 animate-spin rounded-full border-2 border-theme-primary border-t-transparent" />
      </div>
    );
  }

  if (!order) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <p className="text-theme-muted mb-4">Order not found.</p>
        <Link
          href="/account/orders"
          className="text-theme-primary hover:underline text-sm"
        >
          Back to orders
        </Link>
      </div>
    );
  }

  let parsedAddress: Record<string, string> | null = null;
  try {
    if (order.shipping_address) {
      parsedAddress = JSON.parse(order.shipping_address);
    }
  } catch {
    // shipping_address might be plain text
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <Link
        href="/account/orders"
        className="text-sm text-theme-muted hover:text-theme-primary mb-4 inline-block"
      >
        &larr; Back to orders
      </Link>

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-heading font-bold">
          Order #{order.id.slice(0, 8)}
        </h1>
        <span className="inline-block rounded-full bg-theme-surface border border-theme px-3 py-1 text-sm font-medium">
          {order.status}
        </span>
      </div>

      <div className="text-sm text-theme-muted mb-6">
        Placed on {new Date(order.created_at).toLocaleDateString("en-US", {
          year: "numeric",
          month: "long",
          day: "numeric",
        })}
      </div>

      {/* Items */}
      <div className="rounded-xl border border-theme overflow-hidden mb-6">
        <div className="bg-theme-surface px-4 py-2 text-sm font-medium">
          Items
        </div>
        {order.items.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between px-4 py-3 border-t border-theme"
          >
            <div>
              <p className="font-medium text-sm">{item.product_title}</p>
              {item.variant_name && (
                <p className="text-xs text-theme-muted">{item.variant_name}</p>
              )}
              <p className="text-xs text-theme-muted">Qty: {item.quantity}</p>
            </div>
            <span className="text-sm font-medium">
              ${(Number(item.unit_price) * item.quantity).toFixed(2)}
            </span>
          </div>
        ))}
      </div>

      {/* Financial breakdown */}
      <div className="rounded-xl border border-theme p-4 mb-6 space-y-2">
        {order.subtotal != null && (
          <div className="flex justify-between text-sm">
            <span className="text-theme-muted">Subtotal</span>
            <span>${Number(order.subtotal).toFixed(2)}</span>
          </div>
        )}
        {order.discount_amount != null && Number(order.discount_amount) > 0 && (
          <div className="flex justify-between text-sm text-green-600">
            <span>Discount{order.discount_code ? ` (${order.discount_code})` : ""}</span>
            <span>-${Number(order.discount_amount).toFixed(2)}</span>
          </div>
        )}
        {order.tax_amount != null && Number(order.tax_amount) > 0 && (
          <div className="flex justify-between text-sm">
            <span className="text-theme-muted">Tax</span>
            <span>${Number(order.tax_amount).toFixed(2)}</span>
          </div>
        )}
        {order.gift_card_amount != null && Number(order.gift_card_amount) > 0 && (
          <div className="flex justify-between text-sm text-green-600">
            <span>Gift Card</span>
            <span>-${Number(order.gift_card_amount).toFixed(2)}</span>
          </div>
        )}
        <div className="flex justify-between font-medium pt-2 border-t border-theme">
          <span>Total</span>
          <span>${Number(order.total).toFixed(2)} {order.currency}</span>
        </div>
      </div>

      {/* Tracking Info */}
      {order.tracking_number && (
        <div className="rounded-xl border border-theme p-4 mb-6">
          <h3 className="text-sm font-medium mb-2">Shipment Tracking</h3>
          <div className="text-sm text-theme-muted space-y-1">
            <p>
              <span className="font-medium">Tracking Number:</span>{" "}
              {order.tracking_number}
            </p>
            {order.carrier && (
              <p>
                <span className="font-medium">Carrier:</span> {order.carrier}
              </p>
            )}
            {order.shipped_at && (
              <p>
                <span className="font-medium">Shipped:</span>{" "}
                {new Date(order.shipped_at).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </p>
            )}
            {order.delivered_at && (
              <p>
                <span className="font-medium">Delivered:</span>{" "}
                {new Date(order.delivered_at).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Shipping address */}
      {parsedAddress && (
        <div className="rounded-xl border border-theme p-4">
          <h3 className="text-sm font-medium mb-2">Shipping Address</h3>
          <div className="text-sm text-theme-muted space-y-0.5">
            <p>{parsedAddress.name}</p>
            <p>{parsedAddress.line1}</p>
            {parsedAddress.line2 && <p>{parsedAddress.line2}</p>}
            <p>
              {parsedAddress.city}
              {parsedAddress.state ? `, ${parsedAddress.state}` : ""}{" "}
              {parsedAddress.postal_code}
            </p>
            <p>{parsedAddress.country}</p>
          </div>
        </div>
      )}
    </div>
  );
}
