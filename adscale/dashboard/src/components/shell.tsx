/**
 * Dashboard shell layout — the authenticated page wrapper.
 *
 * Combines the Sidebar and TopBar into a full dashboard layout with
 * the main content area. Includes authentication gating: if no token
 * is found, the user is redirected to /login.
 *
 * **For Developers:**
 *   - Wrap all authenticated page content in `<Shell>...</Shell>`.
 *   - The shell handles the flex layout (sidebar | main content area).
 *   - Auth check runs on mount; there is a brief loading state while checking.
 *   - The main content area has overflow-y-auto for scrollable content.
 *   - Import: `import { Shell } from "@/components/shell"`
 *
 * **For QA Engineers:**
 *   - Verify unauthenticated users are redirected to /login.
 *   - Check that the sidebar and top bar render correctly alongside content.
 *   - Test that content scrolls independently of the sidebar.
 *   - Verify layout on various screen sizes (responsive design).
 *
 * **For End Users:**
 *   - The sidebar provides navigation to all sections of the dashboard.
 *   - If your session expires, you will be redirected to the login page.
 */

"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import { TopBar } from "@/components/top-bar";
import { isAuthenticated } from "@/lib/auth";
import { Skeleton } from "@/components/ui/skeleton";

/** Props for the Shell component. */
interface ShellProps {
  /** The page content to render in the main area. */
  children: React.ReactNode;
}

/**
 * Authenticated dashboard shell with sidebar and top bar.
 *
 * Performs a client-side auth check on mount. Shows a loading skeleton
 * while checking, redirects to /login if unauthenticated, or renders
 * the full shell layout if authenticated.
 *
 * @param props - ShellProps containing children.
 * @returns The dashboard layout or a loading/redirect state.
 *
 * @example
 * export default function BillingPage() {
 *   return (
 *     <Shell>
 *       <div className="p-6">Billing content here</div>
 *     </Shell>
 *   );
 * }
 */
export function Shell({ children }: ShellProps) {
  const router = useRouter();
  const [ready, setReady] = React.useState(false);

  React.useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
    } else {
      setReady(true);
    }
  }, [router]);

  /* Show loading skeleton while checking authentication */
  if (!ready) {
    return (
      <div className="flex h-screen bg-background">
        {/* Sidebar skeleton */}
        <div className="w-64 border-r bg-card p-4 space-y-4">
          <Skeleton className="h-8 w-32" />
          <div className="space-y-2 mt-8">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-9 w-full rounded-lg" />
            ))}
          </div>
        </div>
        {/* Main area skeleton */}
        <div className="flex-1 p-6 space-y-4">
          <Skeleton className="h-8 w-48" />
          <div className="grid grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-32 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Sidebar — fixed left */}
      <Sidebar />

      {/* Main content area — flexible, scrollable */}
      <div className="flex flex-col flex-1 min-w-0">
        <TopBar />
        <main className="flex-1 overflow-y-auto bg-dot-pattern">
          {children}
        </main>
      </div>
    </div>
  );
}
