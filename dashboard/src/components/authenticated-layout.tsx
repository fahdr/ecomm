/**
 * Authenticated layout wrapper that renders the unified DashboardShell
 * for all authenticated pages.
 *
 * Shows a loading spinner during auth check, redirects to login if
 * unauthenticated, and wraps children in DashboardShell when authenticated.
 *
 * **For Developers:**
 *   Used by top-level pages (/, /stores, /billing, /notifications, /pricing)
 *   to get the same sidebar + top bar shell that store-scoped pages have.
 *   Store-scoped pages get it via the stores/[id]/layout instead.
 *
 * **For QA:**
 *   - Unauthenticated users see a redirect to /login
 *   - Loading state shows a centered spinner
 *   - Authenticated users see the sidebar + top bar + content
 */

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { DashboardShell } from "@/components/dashboard-shell";

/**
 * Wraps children in the unified shell after verifying authentication.
 *
 * @param children - Page content to render inside the shell.
 * @returns Shell with content, loading spinner, or null (during redirect).
 */
export function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-dot-pattern">
        <div className="size-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!user) return null;

  return <DashboardShell>{children}</DashboardShell>;
}
