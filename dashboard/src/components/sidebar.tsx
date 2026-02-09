/**
 * Collapsible sidebar navigation for the dashboard.
 *
 * Provides grouped navigation links for store-level features. Supports
 * collapsed mode (icon-only) and expanded mode (icon + text). The collapse
 * state is persisted in localStorage.
 *
 * **For Developers:**
 *   - Navigation items are grouped into sections: Commerce, Customers,
 *     Marketing, Operations, Settings
 *   - Uses lucide-react icons for each nav item
 *   - Active state is detected by comparing the current pathname
 *   - Collapse state stored in localStorage key "sidebar-collapsed"
 *
 * **For QA:**
 *   - Sidebar should collapse/expand on toggle button click
 *   - Collapsed state should persist across page refreshes
 *   - Active nav item should have teal left border and teal text
 *   - All links should navigate to correct store sub-pages
 *   - Theme toggle in footer should switch between light/dark
 *
 * **For End Users:**
 *   Use the sidebar to navigate between different sections of your store
 *   management dashboard. Click the collapse button to save screen space.
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Package,
  ShoppingCart,
  Tag,
  FolderTree,
  Gift,
  TrendingUp,
  Star,
  Users,
  RotateCcw,
  BarChart3,
  FlaskConical,
  Mail,
  Truck,
  Layers,
  Shield,
  Store,
  Receipt,
  Coins,
  Globe,
  Palette,
  UserPlus,
  Webhook,
  PanelLeftClose,
  PanelLeftOpen,
  ChevronDown,
  ChevronUp,
  LogOut,
  Bell,
  CreditCard,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/theme-toggle";
import { useStore } from "@/contexts/store-context";
import { useAuth } from "@/contexts/auth-context";

/** A single navigation item in the sidebar. */
interface NavItem {
  /** Display label for the nav item. */
  label: string;
  /** URL path (relative to /stores/[id]/). */
  href: string;
  /** Lucide icon component. */
  icon: React.ComponentType<{ className?: string }>;
}

/** A group of related navigation items. */
interface NavGroup {
  /** Section heading label. */
  title: string;
  /** Nav items in this section. */
  items: NavItem[];
}

/**
 * Returns the navigation groups for a given store ID.
 *
 * @param storeId - The current store's UUID.
 * @returns Array of navigation groups with items.
 */
function getNavGroups(storeId: string): NavGroup[] {
  const base = `/stores/${storeId}`;
  return [
    {
      title: "Commerce",
      items: [
        { label: "Products", href: `${base}/products`, icon: Package },
        { label: "Orders", href: `${base}/orders`, icon: ShoppingCart },
        { label: "Discounts", href: `${base}/discounts`, icon: Tag },
        { label: "Categories", href: `${base}/categories`, icon: FolderTree },
        { label: "Gift Cards", href: `${base}/gift-cards`, icon: Gift },
        { label: "Upsells", href: `${base}/upsells`, icon: TrendingUp },
      ],
    },
    {
      title: "Customers",
      items: [
        { label: "Reviews", href: `${base}/reviews`, icon: Star },
        { label: "Segments", href: `${base}/segments`, icon: Users },
        { label: "Refunds", href: `${base}/refunds`, icon: RotateCcw },
      ],
    },
    {
      title: "Marketing",
      items: [
        { label: "Analytics", href: `${base}/analytics`, icon: BarChart3 },
        { label: "A/B Tests", href: `${base}/ab-tests`, icon: FlaskConical },
        { label: "Email", href: `${base}/email`, icon: Mail },
      ],
    },
    {
      title: "Operations",
      items: [
        { label: "Suppliers", href: `${base}/suppliers`, icon: Truck },
        { label: "Bulk Ops", href: `${base}/bulk`, icon: Layers },
        { label: "Fraud", href: `${base}/fraud`, icon: Shield },
      ],
    },
    {
      title: "Settings",
      items: [
        { label: "Store", href: `${base}`, icon: Store },
        { label: "Tax", href: `${base}/tax`, icon: Receipt },
        { label: "Currency", href: `${base}/currency`, icon: Coins },
        { label: "Domain", href: `${base}/domain`, icon: Globe },
        { label: "Themes", href: `${base}/themes`, icon: Palette },
        { label: "Team", href: `${base}/team`, icon: UserPlus },
        { label: "Webhooks", href: `${base}/webhooks`, icon: Webhook },
      ],
    },
  ];
}

/**
 * Sidebar component with collapsible navigation groups.
 *
 * @returns The sidebar element with navigation links, theme toggle, and user actions.
 */
export function Sidebar() {
  const pathname = usePathname();
  const { store } = useStore();
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    Commerce: true,
    Customers: true,
    Marketing: true,
    Operations: true,
    Settings: true,
  });

  // Load collapsed state from localStorage on mount.
  useEffect(() => {
    const stored = localStorage.getItem("sidebar-collapsed");
    if (stored === "true") setCollapsed(true);
  }, []);

  /**
   * Toggle sidebar collapsed state and persist to localStorage.
   */
  function toggleCollapse() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem("sidebar-collapsed", String(next));
  }

  /**
   * Toggle a navigation group's expanded/collapsed state.
   *
   * @param title - The group title to toggle.
   */
  function toggleGroup(title: string) {
    setExpandedGroups((prev) => ({ ...prev, [title]: !prev[title] }));
  }

  /**
   * Check if a nav item is the currently active route.
   *
   * @param href - The nav item's href to check.
   * @returns True if the pathname matches the href.
   */
  function isActive(href: string): boolean {
    // Exact match for store settings page
    if (href === `/stores/${store?.id}`) {
      return pathname === href;
    }
    // Prefix match for sub-pages (e.g., /products matches /products/new)
    return pathname.startsWith(href);
  }

  const navGroups = store ? getNavGroups(store.id) : [];

  return (
    <aside
      className={cn(
        "flex h-screen flex-col border-r bg-sidebar text-sidebar-foreground transition-all duration-300",
        collapsed ? "w-16" : "w-60"
      )}
    >
      {/* Store Name / Logo area */}
      <div className="flex h-14 items-center border-b border-sidebar-border px-3">
        {!collapsed && store && (
          <Link
            href="/stores"
            className="flex items-center gap-2 truncate font-heading text-sm font-semibold hover:text-primary transition-colors"
          >
            <Store className="size-4 shrink-0 text-primary" />
            <span className="truncate">{store.name}</span>
          </Link>
        )}
        {collapsed && (
          <Link href="/stores" className="mx-auto">
            <Store className="size-4 text-primary" />
          </Link>
        )}
      </div>

      {/* Navigation Groups */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
        {navGroups.map((group) => (
          <div key={group.title} className="mb-1">
            {!collapsed && (
              <button
                onClick={() => toggleGroup(group.title)}
                className="flex w-full items-center justify-between px-2 py-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors"
              >
                {group.title}
                {expandedGroups[group.title] ? (
                  <ChevronUp className="size-3" />
                ) : (
                  <ChevronDown className="size-3" />
                )}
              </button>
            )}
            {(collapsed || expandedGroups[group.title]) && (
              <ul className="space-y-0.5">
                {group.items.map((item) => {
                  const active = isActive(item.href);
                  const Icon = item.icon;
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        title={collapsed ? item.label : undefined}
                        className={cn(
                          "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors",
                          active
                            ? "bg-sidebar-accent text-sidebar-primary font-medium border-l-2 border-sidebar-primary"
                            : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground border-l-2 border-transparent",
                          collapsed && "justify-center px-0"
                        )}
                      >
                        <Icon className={cn("size-4 shrink-0", active && "text-sidebar-primary")} />
                        {!collapsed && <span className="truncate">{item.label}</span>}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        ))}
      </nav>

      {/* Footer: Account links, theme toggle, collapse */}
      <div className="border-t border-sidebar-border px-2 py-2 space-y-0.5">
        {/* Account links */}
        <Link
          href="/notifications"
          className={cn(
            "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground transition-colors",
            collapsed && "justify-center px-0"
          )}
          title={collapsed ? "Notifications" : undefined}
        >
          <Bell className="size-4 shrink-0" />
          {!collapsed && <span>Notifications</span>}
        </Link>
        <Link
          href="/billing"
          className={cn(
            "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground transition-colors",
            collapsed && "justify-center px-0"
          )}
          title={collapsed ? "Billing" : undefined}
        >
          <CreditCard className="size-4 shrink-0" />
          {!collapsed && <span>Billing</span>}
        </Link>

        {/* Divider */}
        <div className="my-1 h-px bg-sidebar-border" />

        {/* Theme + Collapse row */}
        <div className={cn("flex items-center", collapsed ? "flex-col gap-1" : "justify-between px-1")}>
          <ThemeToggle className="size-8" />
          <button
            onClick={toggleCollapse}
            className="flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-sidebar-accent/50 hover:text-foreground transition-colors"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <PanelLeftOpen className="size-4" />
            ) : (
              <PanelLeftClose className="size-4" />
            )}
          </button>
        </div>

        {/* User info + logout */}
        {!collapsed && user && (
          <div className="flex items-center gap-2 px-2 py-1.5">
            <span className="flex-1 truncate text-xs text-muted-foreground">
              {user.email}
            </span>
            <button
              onClick={logout}
              className="text-muted-foreground hover:text-destructive transition-colors"
              aria-label="Log out"
              title="Log out"
            >
              <LogOut className="size-3.5" />
            </button>
          </div>
        )}
        {collapsed && (
          <button
            onClick={logout}
            className="flex w-full items-center justify-center rounded-md px-2.5 py-2 text-muted-foreground hover:text-destructive transition-colors"
            aria-label="Log out"
            title="Log out"
          >
            <LogOut className="size-4" />
          </button>
        )}
      </div>
    </aside>
  );
}
