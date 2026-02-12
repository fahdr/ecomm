/**
 * Top bar component for the dashboard shell.
 *
 * Displays the current page title (derived from the route), the
 * authenticated user's email, and a logout button.
 *
 * **For Developers:**
 *   - Page title is computed from the pathname segments (e.g. "/billing" -> "Billing").
 *   - User email is read from localStorage via `getUserEmail()`.
 *   - Logout triggers token clearance and redirect to /login.
 *   - The component is fully responsive: email is hidden on small screens.
 *
 * **For QA Engineers:**
 *   - Verify the page title updates when navigating between pages.
 *   - Check that the correct email is displayed after login.
 *   - Test logout button clears the session and redirects.
 *   - Test on small viewports to ensure responsive layout.
 *
 * **For End Users:**
 *   - The top bar shows which page you are viewing.
 *   - Click your email to see account options.
 *   - Click "Log out" to end your session.
 */

"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getUserEmail, logout } from "@/lib/auth";
import { serviceConfig } from "@/service.config";

/**
 * Derive a human-readable page title from the current pathname.
 *
 * @param pathname - The current route pathname (e.g. "/api-keys").
 * @returns A formatted title string (e.g. "API Keys").
 */
function getPageTitle(pathname: string): string {
  if (pathname === "/") return "Dashboard";

  /* Find matching nav item label */
  const navItem = serviceConfig.navigation.find(
    (item) => item.href !== "/" && pathname.startsWith(item.href)
  );
  if (navItem) return navItem.label;

  /* Fallback: capitalize the first path segment */
  const segment = pathname.split("/").filter(Boolean)[0] || "Dashboard";
  return segment
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * Top bar component rendered above the main content area.
 *
 * @returns The top bar JSX with page title, user email, and logout.
 */
export function TopBar() {
  const pathname = usePathname();
  const [email, setEmail] = React.useState<string | null>(null);
  const title = getPageTitle(pathname);

  /* Read email from localStorage on mount */
  React.useEffect(() => {
    setEmail(getUserEmail());
  }, []);

  return (
    <header className="flex items-center justify-between h-16 px-6 border-b bg-card/80 backdrop-blur-sm shrink-0">
      {/* Page Title */}
      <h1 className="font-heading text-xl font-bold tracking-tight">
        {title}
      </h1>

      {/* User Controls */}
      <div className="flex items-center gap-4">
        {email && (
          <span className="text-sm text-muted-foreground hidden sm:inline-block truncate max-w-48">
            {email}
          </span>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={logout}
          className="text-muted-foreground hover:text-destructive"
        >
          <LogOut className="size-4" />
          <span className="hidden sm:inline">Log out</span>
        </Button>
      </div>
    </header>
  );
}
