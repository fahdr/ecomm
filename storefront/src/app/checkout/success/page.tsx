/**
 * Order confirmation / checkout success page.
 *
 * Displayed after a customer completes payment via Stripe. Fetches the
 * full order details from the public API using the order_id from URL
 * params and displays a complete order breakdown.
 *
 * **For Developers:**
 *   Client component that reads order_id from URL search params.
 *   In mock Stripe mode the redirect URL contains the session ID which
 *   embeds the order_id (format: cs_test_mock_{order_id}).
 *
 * **For QA Engineers:**
 *   - Shows order number, status, items, shipping address, and totals.
 *   - Without a valid order_id, shows a generic thank-you message.
 *   - Handles loading and error states gracefully.
 *
 * **For End Users:**
 *   This page confirms your order was placed successfully. You'll see
 *   your complete order details including items, shipping address,
 *   and payment breakdown.
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import type { OrderDetail } from "@/lib/types";

/**
 * Checkout success page client component.
 *
 * @returns An order confirmation page with full order details.
 */
export default function CheckoutSuccessPage() {
  const searchParams = useSearchParams();
  const store = useStore();
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    async function fetchOrder() {
      if (!store) {
        setLoading(false);
        return;
      }

      // Try to get order_id from params — or extract from mock session_id
      let orderId = searchParams.get("order_id");
      if (!orderId) {
        const sessionId = searchParams.get("session_id");
        if (sessionId?.startsWith("cs_test_mock_")) {
          orderId = sessionId.replace("cs_test_mock_", "");
        }
      }

      if (!orderId) {
        setLoading(false);
        return;
      }

      const { data } = await api.get<OrderDetail>(
        `/api/v1/public/stores/${encodeURIComponent(store.slug)}/orders/${orderId}`
      );

      if (data) {
        setOrder(data);
      } else {
        setError(true);
      }
      setLoading(false);
    }

    fetchOrder();
  }, [store, searchParams]);

  // Loading state
  if (loading) {
    return (
      <div className="py-16">
        <div className="mx-auto max-w-2xl px-4 text-center">
          <div className="mx-auto mb-6 h-16 w-16 rounded-full bg-zinc-100 dark:bg-zinc-800 animate-pulse" />
          <div className="h-8 w-48 mx-auto bg-zinc-100 dark:bg-zinc-800 rounded animate-pulse mb-4" />
          <div className="h-4 w-64 mx-auto bg-zinc-100 dark:bg-zinc-800 rounded animate-pulse" />
        </div>
      </div>
    );
  }

  // No order found — show generic success
  if (!order) {
    return (
      <div className="py-16">
        <div className="mx-auto max-w-2xl px-4 text-center">
          <SuccessIcon />
          <h1 className="text-3xl font-heading font-bold tracking-tight mb-4">
            {error ? "Order Not Found" : "Thank You!"}
          </h1>
          <p className="text-theme-muted mb-8">
            {error
              ? "We couldn't load your order details, but your payment was processed successfully."
              : "Your order has been placed successfully."}
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/"
              className="inline-flex items-center rounded-lg bg-theme-primary px-6 py-3 text-sm font-medium text-white hover:opacity-90 transition-opacity"
            >
              Continue Shopping
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Full order detail
  return (
    <div className="py-12">
      <div className="mx-auto max-w-3xl px-4 sm:px-6">
        {/* Header */}
        <div className="text-center mb-10">
          <SuccessIcon />
          <h1 className="text-3xl font-heading font-bold tracking-tight mb-2">
            Order Confirmed!
          </h1>
          <p className="text-theme-muted">
            We&apos;ve sent a confirmation to{" "}
            <span className="font-medium text-theme-text">
              {order.customer_email}
            </span>
          </p>
        </div>

        {/* Order details card */}
        <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 overflow-hidden">
          {/* Order header */}
          <div className="bg-zinc-50 dark:bg-zinc-900/50 px-6 py-4 flex flex-wrap items-center justify-between gap-3 border-b border-zinc-200 dark:border-zinc-800">
            <div>
              <p className="text-sm text-theme-muted">Order Number</p>
              <p className="font-mono font-bold text-lg">
                {order.order_number}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-theme-muted">Status</p>
              <span className="inline-flex items-center rounded-full bg-amber-100 dark:bg-amber-900/30 px-3 py-0.5 text-xs font-medium text-amber-800 dark:text-amber-300 capitalize">
                {order.status}
              </span>
            </div>
          </div>

          {/* Items */}
          <div className="px-6 py-5">
            <h3 className="text-sm font-semibold text-theme-muted uppercase tracking-wider mb-4">
              Items
            </h3>
            <div className="space-y-3">
              {order.items.map((item) => (
                <div key={item.id} className="flex items-center gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm">{item.product_title}</p>
                    {item.variant_name && (
                      <p className="text-xs text-theme-muted">
                        {item.variant_name}
                      </p>
                    )}
                  </div>
                  <p className="text-sm text-theme-muted shrink-0">
                    {item.quantity} &times; ${Number(item.unit_price).toFixed(2)}
                  </p>
                  <p className="text-sm font-medium w-20 text-right shrink-0">
                    ${Number(item.total_price).toFixed(2)}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Financial breakdown */}
          <div className="px-6 py-4 border-t border-zinc-200 dark:border-zinc-800 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-theme-muted">Subtotal</span>
              <span>${Number(order.subtotal).toFixed(2)}</span>
            </div>
            {Number(order.discount_amount) > 0 && (
              <div className="flex justify-between text-emerald-600 dark:text-emerald-400">
                <span>
                  Discount{order.discount_code && ` (${order.discount_code})`}
                </span>
                <span>&minus;${Number(order.discount_amount).toFixed(2)}</span>
              </div>
            )}
            {Number(order.tax_amount) > 0 && (
              <div className="flex justify-between">
                <span className="text-theme-muted">Tax</span>
                <span>${Number(order.tax_amount).toFixed(2)}</span>
              </div>
            )}
            {Number(order.gift_card_amount) > 0 && (
              <div className="flex justify-between text-emerald-600 dark:text-emerald-400">
                <span>Gift Card</span>
                <span>
                  &minus;${Number(order.gift_card_amount).toFixed(2)}
                </span>
              </div>
            )}
            <div className="flex justify-between border-t border-zinc-200 dark:border-zinc-700 pt-2 text-base font-bold">
              <span>Total</span>
              <span>
                ${Number(order.total).toFixed(2)} {order.currency}
              </span>
            </div>
          </div>

          {/* Shipping address */}
          {order.shipping_address && (
            <div className="px-6 py-4 border-t border-zinc-200 dark:border-zinc-800">
              <h3 className="text-sm font-semibold text-theme-muted uppercase tracking-wider mb-2">
                Shipping To
              </h3>
              <address className="text-sm not-italic leading-relaxed">
                <p className="font-medium">{order.shipping_address.name}</p>
                <p>{order.shipping_address.line1}</p>
                {order.shipping_address.line2 && (
                  <p>{order.shipping_address.line2}</p>
                )}
                <p>
                  {order.shipping_address.city}
                  {order.shipping_address.state &&
                    `, ${order.shipping_address.state}`}{" "}
                  {order.shipping_address.postal_code}
                </p>
                <p>{order.shipping_address.country}</p>
                {order.shipping_address.phone && (
                  <p className="mt-1 text-theme-muted">
                    {order.shipping_address.phone}
                  </p>
                )}
              </address>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/"
            className="inline-flex items-center rounded-lg bg-theme-primary px-6 py-3 text-sm font-medium text-white hover:opacity-90 transition-opacity"
          >
            Continue Shopping
          </Link>
          <Link
            href="/products"
            className="inline-flex items-center rounded-lg border border-zinc-300 dark:border-zinc-700 px-6 py-3 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-colors"
          >
            Browse Products
          </Link>
        </div>
      </div>
    </div>
  );
}

/**
 * Animated success checkmark icon.
 * @returns A green circle with a check icon.
 */
function SuccessIcon() {
  return (
    <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/30">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={2}
        stroke="currentColor"
        className="h-8 w-8 text-emerald-600 dark:text-emerald-400"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M4.5 12.75l6 6 9-13.5"
        />
      </svg>
    </div>
  );
}
