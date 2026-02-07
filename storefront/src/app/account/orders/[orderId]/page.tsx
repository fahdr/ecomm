/**
 * Customer order detail page.
 *
 * Shows full details of a single order including line items, totals,
 * status, and timestamps.
 *
 * **For Developers:**
 *   Client component fetching a single order from the customer account API.
 *   Uses the ``orderId`` URL parameter from Next.js dynamic routing.
 *
 * **For QA Engineers:**
 *   - Shows order ID, status, date, and total.
 *   - Line items show product title, variant, quantity, unit price, line total.
 *   - 404 or not-found orders show an error message.
 *   - Back link returns to the order list.
 *
 * **For End Users:**
 *   View the full details of a specific order.
 */

"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useCustomerAuth } from "@/contexts/customer-auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import type { Order } from "@/lib/types";

/** Map order status to a color class. */
function statusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
    paid: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
    shipped: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
    delivered: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
    cancelled: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  };
  return colors[status] || "bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-300";
}

/**
 * Order detail page component.
 *
 * @param props - Page props containing the orderId parameter.
 * @returns The order detail view with items and summary.
 */
export default function OrderDetailPage({
  params,
}: {
  params: Promise<{ orderId: string }>;
}) {
  const { orderId } = use(params);
  const { customer, loading: authLoading } = useCustomerAuth();
  const store = useStore();
  const router = useRouter();

  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!authLoading && !customer) {
      router.replace("/login");
    }
  }, [authLoading, customer, router]);

  useEffect(() => {
    if (!customer || !store) return;

    async function fetchOrder() {
      setLoading(true);
      const slug = encodeURIComponent(store!.slug);
      const result = await api.get<Order>(
        `/api/v1/public/stores/${slug}/account/orders/${orderId}`
      );
      if (result.error) {
        setNotFound(true);
      } else if (result.data) {
        setOrder(result.data);
      }
      setLoading(false);
    }

    fetchOrder();
  }, [customer, store, orderId]);

  if (authLoading || loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-zinc-500 dark:text-zinc-400">Loading order...</p>
      </div>
    );
  }

  if (notFound || !order) {
    return (
      <div className="py-16 text-center">
        <p className="text-zinc-500 dark:text-zinc-400 mb-4">Order not found.</p>
        <Link
          href="/account/orders"
          className="text-sm font-medium text-zinc-900 dark:text-zinc-100 hover:underline"
        >
          Back to orders
        </Link>
      </div>
    );
  }

  return (
    <div className="py-12">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 mb-8 text-sm">
          <Link
            href="/account"
            className="text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
          >
            Account
          </Link>
          <span className="text-zinc-300 dark:text-zinc-600">/</span>
          <Link
            href="/account/orders"
            className="text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
          >
            Orders
          </Link>
          <span className="text-zinc-300 dark:text-zinc-600">/</span>
          <span className="font-mono text-zinc-700 dark:text-zinc-300">
            #{order.id.slice(0, 8)}
          </span>
        </div>

        {/* Order Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">
              Order #{order.id.slice(0, 8)}
            </h2>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
              Placed on {new Date(order.created_at).toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </p>
          </div>
          <span
            className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${statusColor(order.status)}`}
          >
            {order.status}
          </span>
        </div>

        {/* Line Items */}
        <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 divide-y divide-zinc-200 dark:divide-zinc-800">
          {order.items.map((item) => (
            <div key={item.id} className="flex items-center justify-between p-4">
              <div>
                <p className="font-medium">{item.product_title}</p>
                {item.variant_name && (
                  <p className="text-sm text-zinc-500 dark:text-zinc-400">
                    {item.variant_name}
                  </p>
                )}
                <p className="text-sm text-zinc-500 dark:text-zinc-400">
                  Qty: {item.quantity} &times; ${Number(item.unit_price).toFixed(2)}
                </p>
              </div>
              <p className="font-semibold">
                ${(item.quantity * Number(item.unit_price)).toFixed(2)}
              </p>
            </div>
          ))}
        </div>

        {/* Total */}
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-800">
          <span className="text-lg font-medium">Total</span>
          <span className="text-2xl font-bold">
            ${Number(order.total).toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
}
