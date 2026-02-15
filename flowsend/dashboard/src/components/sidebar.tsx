/**
 * Config-driven sidebar navigation component.
 *
 * Reads navigation entries from `serviceConfig.navigation` and renders
 * them as links with lucide-react icons. Supports collapsing (persisted
 * in localStorage), active route highlighting, and a theme toggle.
 *
 * **For Developers:**
 *   - Navigation items are defined in service.config.ts — no code changes needed.
 *   - Icon names are resolved dynamically from the lucide-react icon library.
 *   - Collapsed state is persisted in localStorage under `{slug}_sidebar_collapsed`.
 *   - Active state is determined by comparing pathname to href.
 *   - The theme toggle at the bottom switches between light/dark mode by toggling
 *     the `dark` class on the <html> element.
 *
 * **For QA Engineers:**
 *   - Verify all nav items link to valid pages.
 *   - Test collapsed/expanded toggle persists across page reloads.
 *   - Check active state highlighting matches the current route.
 *   - Verify theme toggle switches between light and dark modes.
 *   - Test keyboard navigation through sidebar links.
 *
 * **For End Users:**
 *   - Click the collapse button to save screen space.
 *   - The current page is highlighted in the sidebar.
 *   - Use the theme toggle at the bottom to switch between light and dark mode.
 */

"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Key,
  CreditCard,
  Settings,
  ChevronLeft,
  ChevronRight,
  Sun,
  Moon,
  Megaphone,
  BarChart3,
  Users,
  Mail,
  Search,
  Globe,
  Bot,
  Zap,
  Shield,
  Database,
  FileText,
  MessageSquare,
  MessageSquareText,
  GitBranch,
  LayoutTemplate,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { serviceConfig } from "@/service.config";

/**
 * Map of icon name strings to lucide-react icon components.
 * Add new icons here when adding navigation items to service.config.ts.
 */
const iconMap: Record<string, LucideIcon> = {
  LayoutDashboard,
  Key,
  CreditCard,
  Settings,
  Megaphone,
  BarChart3,
  Users,
  Mail,
  Search,
  Globe,
  Bot,
  Zap,
  Shield,
  Database,
  FileText,
  MessageSquare,
  MessageSquareText,
  GitBranch,
  LayoutTemplate,
};

/** localStorage key for persisting sidebar collapsed state. */
const COLLAPSED_KEY = `${serviceConfig.slug}_sidebar_collapsed`;

/** localStorage key for persisting theme preference. */
const THEME_KEY = `${serviceConfig.slug}_theme`;

/**
 * Sidebar navigation component.
 *
 * Renders the service logo/name, navigation links with icons,
 * and a theme toggle at the bottom. Collapsible with state persistence.
 *
 * @returns The sidebar JSX element.
 */
export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = React.useState(false);
  const [isDark, setIsDark] = React.useState(false);

  /* Initialize collapsed state and theme from localStorage on mount */
  React.useEffect(() => {
    const savedCollapsed = localStorage.getItem(COLLAPSED_KEY);
    if (savedCollapsed === "true") setCollapsed(true);

    const savedTheme = localStorage.getItem(THEME_KEY);
    if (savedTheme === "dark") {
      setIsDark(true);
      document.documentElement.classList.add("dark");
    } else if (savedTheme === "light") {
      setIsDark(false);
      document.documentElement.classList.remove("dark");
    } else {
      /* Default to system preference */
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      setIsDark(prefersDark);
      if (prefersDark) document.documentElement.classList.add("dark");
    }
  }, []);

  /**
   * Toggle sidebar collapsed state and persist to localStorage.
   */
  function toggleCollapsed() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem(COLLAPSED_KEY, String(next));
  }

  /**
   * Toggle between light and dark theme.
   * Updates the `dark` class on <html> and persists the preference.
   */
  function toggleTheme() {
    const next = !isDark;
    setIsDark(next);
    localStorage.setItem(THEME_KEY, next ? "dark" : "light");
    if (next) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }

  /**
   * Check if a navigation href matches the current route.
   * Uses longest-prefix matching to handle nested routes correctly:
   * e.g. when on /sms/templates, /sms/templates is active but /sms is not.
   *
   * @param href - The navigation item's href.
   * @returns True if the route is active.
   */
  function isActive(href: string): boolean {
    if (href === "/") return pathname === "/";
    if (!pathname.startsWith(href)) return false;
    /* Check if a more specific sibling nav item matches the current pathname */
    const moreSpecific = serviceConfig.navigation.some(
      (item) =>
        item.href !== href &&
        item.href.startsWith(href) &&
        pathname.startsWith(item.href)
    );
    return !moreSpecific;
  }

  return (
    <aside
      className={cn(
        "flex flex-col h-screen border-r bg-card transition-all duration-300 ease-in-out",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* ── Service Logo & Name ── */}
      <div className="flex items-center gap-3 px-4 h-16 border-b shrink-0">
        {/* Logo circle using primary color */}
        <div
          className="size-8 rounded-lg bg-primary flex items-center justify-center shrink-0"
          aria-hidden="true"
        >
          <span className="text-primary-foreground font-bold text-sm font-heading">
            {serviceConfig.name.charAt(0)}
          </span>
        </div>
        {!collapsed && (
          <span className="font-heading font-bold text-lg truncate">
            {serviceConfig.name}
          </span>
        )}
      </div>

      {/* ── Navigation Links ── */}
      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
        {serviceConfig.navigation.map((item) => {
          const Icon = iconMap[item.icon] || LayoutDashboard;
          const active = isActive(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                collapsed && "justify-center px-0"
              )}
              title={collapsed ? item.label : undefined}
            >
              <Icon className="size-5 shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* ── Bottom Controls ── */}
      <div className="border-t px-2 py-3 space-y-1 shrink-0">
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className={cn(
            "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 w-full text-muted-foreground hover:bg-secondary hover:text-foreground",
            collapsed && "justify-center px-0"
          )}
          title={isDark ? "Switch to light mode" : "Switch to dark mode"}
          aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
        >
          {isDark ? (
            <Sun className="size-5 shrink-0" />
          ) : (
            <Moon className="size-5 shrink-0" />
          )}
          {!collapsed && <span>{isDark ? "Light Mode" : "Dark Mode"}</span>}
        </button>

        {/* Collapse Toggle */}
        <button
          onClick={toggleCollapsed}
          className={cn(
            "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 w-full text-muted-foreground hover:bg-secondary hover:text-foreground",
            collapsed && "justify-center px-0"
          )}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronRight className="size-5 shrink-0" />
          ) : (
            <ChevronLeft className="size-5 shrink-0" />
          )}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  );
}
