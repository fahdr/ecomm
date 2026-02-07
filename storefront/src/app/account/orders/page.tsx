/**
 * Customer order history page.
 *
 * Displays a paginated list of the customer's orders with status badges.
 * Each order links to a detail view.
 *
 * **For Developers:**
 *   Client component fetching from the customer account orders API.
 *   Requires customer authentication (redirects to ``/login`` if not authed).
 *
 * **For QA Engineers:**
 *   - Empty state shows "No orders yet" with a link to shop.
 *   - Orders are listed in reverse chronological order.
 *   - Each row shows order ID snippet, status badge, date, items count, total.
 *   - Pagination controls appear when needed.
 *
 * **For End Users:**
 *   View your past orders and click any order to see its full details.
 */

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useCustomerAuth } from "@/contexts/customer-auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import type { PaginatedOrders } from "@/lib/types";

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
 * Order history page component.
 *
 * @returns A paginated list of customer orders.
 */
export default function OrderHistoryPage() {
  const { customer, loading: authLoading } = useCustomerAuth();
  const store = useStore();
  const router = useRouter();

  const [orders, setOrders] = useState<PaginatedOrders | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !customer) {
      router.replace("/login");
    }
  }, [authLoading, customer, router]);

  useEffect(() => {
    if (!customer || !store) return;

    async function fetchOrders() {
      setLoading(true);
      const slug = encodeURIComponent(store!.slug);
      const result = await api.get<PaginatedOrders>(
        `/api/v1/public/stores/${slug}/account/orders?page=${page}&per_page=10`
      );
      if (result.data) {
        setOrders(result.data);
      }
      setLoading(false);
    }

    fetchOrders();
  }, [customer, store, page]);

  if (authLoading || loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-zinc-500 dark:text-zinc-400">Loading orders...</p>
      </div>
    );
  }

  return (
    <div className="py-12">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-4 mb-8">
          <Link
            href="/account"
            className="text-sm text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
          >
            Account
          </Link>
          <span className="text-zinc-300 dark:text-zinc-600">/</span>
          <h2 className="text-2xl font-bold tracking-tight">Orders</h2>
        </div>

        {!orders || orders.items.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-zinc-500 dark:text-zinc-400 mb-4">
              No orders yet.
            </p>
            <Link
              href="/products"
              className="text-sm font-medium text-zinc-900 dark:text-zinc-100 hover:underline"
            >
              Start shopping
            </Link>
          </div>
        ) : (
          <>
            <div className="space-y-3">
              {orders.items.map((order) => (
                <Link
                  key={order.id}
                  href={`/account/orders/${order.id}`}
                  className="block rounded-lg border border-zinc-200 dark:border-zinc-800 p-4 hover:bg-zinc-50 dark:hover:bg-zinc-900/50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-sm text-zinc-600 dark:text-zinc-400">
                          #{order.id.slice(0, 8)}
                        </span>
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColor(order.status)}`}
                        >
                          {order.status}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-500 dark:text-zinc-400">
                        {new Date(order.created_at).toLocaleDateString()} &middot;{" "}
                        {order.items.length} item{order.items.length !== 1 ? "s" : ""}
                      </p>
                    </div>
                    <p className="text-lg font-semibold">
                      ${Number(order.total).toFixed(2)}
                    </p>
                  </div>
                </Link>
              ))}
            </div>

            {orders.pages > 1 && (
              <div className="flex items-center justify-center gap-4 mt-8">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="rounded-lg border border-zinc-300 dark:border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-50 dark:hover:bg-zinc-800 disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="text-sm text-zinc-500">
                  Page {page} of {orders.pages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(orders!.pages, p + 1))}
                  disabled={page >= orders.pages}
                  className="rounded-lg border border-zinc-300 dark:border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-50 dark:hover:bg-zinc-800 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
