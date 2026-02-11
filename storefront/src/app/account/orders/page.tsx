/**
 * Customer order history page.
 *
 * **For End Users:**
 *   View all your past orders with status, total, and item details.
 *
 * **For QA Engineers:**
 *   - Fetches orders from ``GET /public/stores/{slug}/customers/me/orders``.
 *   - Shows order date, status badge, total, and item count.
 *   - Click an order to see its detail page.
 *   - Empty state when no orders exist.
 */

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useCustomerAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";

interface OrderItem {
  id: string;
  product_title: string;
  quantity: number;
  unit_price: number;
}

interface Order {
  id: string;
  status: string;
  total: number;
  currency: string;
  created_at: string;
  items: OrderItem[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function OrdersPage() {
  const { customer, loading: authLoading, getAuthHeaders } = useCustomerAuth();
  const store = useStore();
  const router = useRouter();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !customer) {
      router.replace("/account/login");
    }
  }, [customer, authLoading, router]);

  useEffect(() => {
    if (!customer || !store) return;

    async function fetchOrders() {
      const res = await fetch(
        `${API_BASE}/api/v1/public/stores/${store!.slug}/customers/me/orders`,
        { headers: getAuthHeaders() }
      );
      if (res.ok) {
        setOrders(await res.json());
      }
      setLoading(false);
    }

    fetchOrders();
  }, [customer, store, getAuthHeaders]);

  if (authLoading || loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="size-6 animate-spin rounded-full border-2 border-theme-primary border-t-transparent" />
      </div>
    );
  }

  const statusColors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    paid: "bg-blue-100 text-blue-800",
    shipped: "bg-purple-100 text-purple-800",
    delivered: "bg-green-100 text-green-800",
    cancelled: "bg-red-100 text-red-800",
  };

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-heading font-bold">Your Orders</h1>
        <Link
          href="/account"
          className="text-sm text-theme-muted hover:text-theme-primary"
        >
          Back to Account
        </Link>
      </div>

      {orders.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-theme-muted mb-4">No orders yet.</p>
          <Link
            href="/products"
            className="inline-block rounded-lg bg-theme-primary px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            Start Shopping
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map((order) => (
            <Link key={order.id} href={`/account/orders/${order.id}`}>
              <div className="rounded-xl border border-theme bg-theme-surface p-4 transition-all hover:shadow-md hover:-translate-y-0.5">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-mono text-theme-muted">
                      #{order.id.slice(0, 8)}
                    </span>
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        statusColors[order.status] || "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {order.status}
                    </span>
                  </div>
                  <span className="text-sm font-medium">
                    ${Number(order.total).toFixed(2)} {order.currency}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm text-theme-muted">
                  <span>
                    {order.items.length} item{order.items.length !== 1 ? "s" : ""}
                  </span>
                  <span>{new Date(order.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
