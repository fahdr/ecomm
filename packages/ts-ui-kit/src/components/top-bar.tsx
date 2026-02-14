/**
 * Top bar component for the dashboard shell.
 *
 * Displays the current page title (derived from navigation config),
 * the authenticated user's email, and a logout button.
 *
 * **For Developers:**
 *   - Page title is computed from pathname + navigation items passed as props.
 *   - User email and logout are provided by the auth manager.
 *   - Import: `import { TopBar } from "@ecomm/ui-kit"`
 *
 * **For QA Engineers:**
 *   - Verify the page title updates when navigating between pages.
 *   - Check that the correct email is displayed after login.
 *   - Test logout button clears the session and redirects.
 *
 * **For End Users:**
 *   - The top bar shows which page you are viewing.
 *   - Click "Log out" to end your session.
 */

"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { LogOut } from "lucide-react";
import { Button } from "./ui/button";
import type { NavItem } from "../types";
import type { AuthManager } from "../lib/auth";

/** Props for the TopBar component. */
export interface TopBarProps {
  /** Navigation items used to derive the page title. */
  navigation: NavItem[];
  /** Auth manager for getUserEmail and logout. */
  auth: AuthManager;
}

/**
 * Derive a human-readable page title from the current pathname.
 *
 * @param pathname - The current route pathname.
 * @param navigation - Navigation items to match against.
 * @returns A formatted title string.
 */
function getPageTitle(pathname: string, navigation: NavItem[]): string {
  if (pathname === "/") return "Dashboard";

  const navItem = navigation.find(
    (item) => item.href !== "/" && pathname.startsWith(item.href)
  );
  if (navItem) return navItem.label;

  const segment = pathname.split("/").filter(Boolean)[0] || "Dashboard";
  return segment
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * Top bar component rendered above the main content area.
 *
 * @param props - TopBarProps with navigation and auth manager.
 * @returns The top bar JSX with page title, user email, and logout.
 *
 * @example
 * <TopBar navigation={config.navigation} auth={authManager} />
 */
export function TopBar({ navigation, auth }: TopBarProps) {
  const pathname = usePathname();
  const [email, setEmail] = React.useState<string | null>(null);
  const title = getPageTitle(pathname, navigation);

  React.useEffect(() => {
    setEmail(auth.getUserEmail());
  }, [auth]);

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
          onClick={auth.logout}
          className="text-muted-foreground hover:text-destructive"
        >
          <LogOut className="size-4" />
          <span className="hidden sm:inline">Log out</span>
        </Button>
      </div>
    </header>
  );
}
