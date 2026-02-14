/**
 * Store-scoped layout that wraps all pages under /stores/[id]/.
 *
 * Fetches the store data once and provides it to all child pages via
 * StoreProvider context. Renders the DashboardShell with sidebar
 * navigation specific to the current store.
 *
 * **For Developers:**
 *   - This is a Next.js layout — it wraps all pages under /stores/[id]/
 *   - Store data is fetched once here and shared via StoreProvider
 *   - Child pages access store data via useStore() hook
 *   - The DashboardShell renders the sidebar and main content area
 *
 * **For QA:**
 *   - Store should load once when entering a store context
 *   - Navigating between sub-pages should NOT refetch store data
 *   - If the store is not found, a "Store not found" message is shown
 *   - Loading state shows a skeleton while store data is being fetched
 *
 * **For End Users:**
 *   This layout provides the sidebar navigation for managing your store.
 *   Use the sidebar to switch between Products, Orders, Analytics, etc.
 */

"use client";

import { useEffect, useState, useCallback, use } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { StoreProvider, type StoreData } from "@/contexts/store-context";
import { DashboardShell } from "@/components/dashboard-shell";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export default function StoreLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { user, loading: authLoading } = useAuth();
  const [store, setStore] = useState<StoreData | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  /**
   * Fetch store data from the API.
   * Called on mount and when refreshStore is triggered.
   */
  const fetchStore = useCallback(async () => {
    const result = await api.get<StoreData>(`/api/v1/stores/${id}`);
    if (result.error) {
      setNotFound(true);
      setLoading(false);
      return;
    }
    setStore(result.data!);
    setLoading(false);
  }, [id]);

  useEffect(() => {
    if (authLoading || !user) return;
    fetchStore();
  }, [user, authLoading, fetchStore]);

  // Auth still loading
  if (authLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-dot-pattern">
        <div className="size-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  // Store loading
  if (loading && !notFound) {
    return (
      <div className="flex h-screen items-center justify-center bg-dot-pattern">
        <div className="size-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  // Store not found
  if (notFound) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-dot-pattern">
        <h2 className="font-heading text-xl font-semibold">Store not found</h2>
        <p className="text-muted-foreground">
          This store doesn&apos;t exist or you don&apos;t have access to it.
        </p>
        <Link href="/stores">
          <Button variant="outline">Back to stores</Button>
        </Link>
      </div>
    );
  }

  return (
    <StoreProvider store={store} refreshStore={fetchStore}>
      <DashboardShell>{children}</DashboardShell>
    </StoreProvider>
  );
}
