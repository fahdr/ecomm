/**
 * Admin Shell layout component for the Super Admin Dashboard.
 *
 * Provides the persistent sidebar navigation, top bar with admin
 * user info, and authentication gating. All authenticated pages
 * should be wrapped in this component.
 *
 * For Developers:
 *   Use `<AdminShell>` as the outermost wrapper in each page.
 *   It handles auth checks client-side, redirecting to /login
 *   if no token is present.
 *
 * For QA Engineers:
 *   - Verify that unauthenticated users are redirected to /login.
 *   - Verify that the sidebar highlights the current route.
 *   - Verify that the logout button clears the token and redirects.
 *
 * For Project Managers:
 *   This shell provides the consistent admin navigation experience.
 *   All admin pages share the same sidebar and top bar.
 *
 * For End Users:
 *   This component is exclusively for platform administrators.
 */

"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard,
  BrainCircuit,
  DollarSign,
  Server,
  LogOut,
  Shield,
  Menu,
  X,
} from "lucide-react";
import { adminApi } from "@/lib/api";

/**
 * Navigation item definition for the sidebar.
 *
 * @param label - Display text for the nav link.
 * @param href - The route path.
 * @param icon - Lucide icon component to render.
 */
interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}

/**
 * Sidebar navigation items.
 *
 * Each entry maps to a top-level admin page. The icon and label
 * are displayed in the sidebar, and the href determines the active state.
 */
const NAV_ITEMS: NavItem[] = [
  { label: "Overview", href: "/", icon: LayoutDashboard },
  { label: "Providers", href: "/providers", icon: BrainCircuit },
  { label: "Costs", href: "/costs", icon: DollarSign },
  { label: "Services", href: "/services", icon: Server },
];

/**
 * Props for the AdminShell component.
 *
 * @param children - The page content to render inside the shell.
 */
interface AdminShellProps {
  children: React.ReactNode;
}

/**
 * Admin Shell component.
 *
 * Renders the sidebar navigation and top bar. Redirects to /login
 * if the user is not authenticated. Supports mobile sidebar toggle.
 *
 * @param props - The component props.
 * @returns The shell layout wrapping the page content.
 */
export function AdminShell({ children }: AdminShellProps) {
  const pathname = usePathname();
  const [isReady, setIsReady] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  /**
   * Auth gate: Check for token on mount and redirect if missing.
   */
  useEffect(() => {
    if (!adminApi.isAuthenticated()) {
      window.location.href = "/login";
      return;
    }
    setIsReady(true);
  }, []);

  /**
   * Handle logout by clearing the token and redirecting.
   */
  const handleLogout = () => {
    adminApi.logout();
  };

  /* Show nothing until auth check completes to prevent flash. */
  if (!isReady) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="w-6 h-6 border-2 border-[var(--admin-primary)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      {/* ---- Mobile sidebar overlay ---- */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ---- Sidebar ---- */}
      <aside
        className={`admin-sidebar fixed lg:static inset-y-0 left-0 z-50 w-60 flex flex-col transition-transform duration-300 lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Brand */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-[var(--admin-border-subtle)]">
          <Shield size={22} className="text-[var(--admin-primary)]" />
          <span className="text-sm font-semibold tracking-wide text-[var(--admin-text-primary)]">
            Super Admin
          </span>
          {/* Close button on mobile */}
          <button
            onClick={() => setSidebarOpen(false)}
            className="ml-auto lg:hidden text-[var(--admin-text-muted)] hover:text-[var(--admin-text-primary)]"
            aria-label="Close sidebar"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`admin-nav-link ${isActive ? "active" : ""}`}
                onClick={() => setSidebarOpen(false)}
              >
                <item.icon size={18} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-3 py-4 border-t border-[var(--admin-border-subtle)]">
          <button
            onClick={handleLogout}
            className="admin-nav-link w-full text-[var(--admin-danger)] hover:bg-[oklch(0.63_0.22_25_/_0.08)]"
          >
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </aside>

      {/* ---- Main content area ---- */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="flex items-center gap-4 px-6 py-3 border-b border-[var(--admin-border-subtle)] bg-[var(--admin-bg-raised)]">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden text-[var(--admin-text-secondary)] hover:text-[var(--admin-text-primary)]"
            aria-label="Open sidebar"
          >
            <Menu size={20} />
          </button>

          <div className="flex-1" />

          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-[var(--admin-primary)] flex items-center justify-center">
              <span className="text-[11px] font-bold text-[var(--admin-bg-base)]">
                A
              </span>
            </div>
            <span className="text-xs text-[var(--admin-text-secondary)] hidden sm:inline">
              Admin
            </span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
