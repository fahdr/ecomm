/**
 * Collapsible sidebar navigation for the dashboard.
 *
 * Supports two modes: **platform mode** (top-level pages like /, /stores,
 * /billing) and **store mode** (inside /stores/[id]/*). The mode is
 * determined automatically by the current pathname.
 *
 * **For Developers:**
 *   - Platform mode shows: Home, Stores, Billing, Pricing, Notifications
 *   - Store mode shows: 5 groups of store management links
 *   - Collapse state persisted in localStorage key "sidebar-collapsed"
 *   - Uses ``useStore()`` which returns null on platform-level pages
 *
 * **For QA:**
 *   - Sidebar should collapse/expand on toggle button click
 *   - Collapsed state should persist across page refreshes
 *   - Active nav item should have teal left border and teal text
 *   - Platform mode should appear on /, /stores, /billing, /notifications
 *   - Store mode should appear on /stores/[id]/* pages
 *   - Theme toggle in footer should switch between light/dark
 *
 * **For End Users:**
 *   Use the sidebar to navigate between different sections of the dashboard.
 *   Click the collapse button to save screen space.
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
  Bell,
  CreditCard,
  LayoutDashboard,
  DollarSign,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/theme-toggle";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";

/** A single navigation item in the sidebar. */
interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}

/** A group of related navigation items. */
interface NavGroup {
  title: string;
  items: NavItem[];
}

/**
 * Returns the store-mode navigation groups.
 *
 * @param storeId - The current store's UUID.
 * @returns Array of navigation groups for store management.
 */
function getStoreNavGroups(storeId: string): NavGroup[] {
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
 * Returns the platform-mode navigation items (flat list, no groups).
 *
 * @returns Array of navigation items for platform-level pages.
 */
function getPlatformNavItems(): NavItem[] {
  return [
    { label: "Home", href: "/", icon: LayoutDashboard },
    { label: "Stores", href: "/stores", icon: Store },
    { label: "Billing", href: "/billing", icon: CreditCard },
    { label: "Pricing", href: "/pricing", icon: DollarSign },
    { label: "Notifications", href: "/notifications", icon: Bell },
  ];
}

/**
 * Sidebar component with collapsible navigation.
 *
 * Automatically switches between platform mode and store mode based on
 * the current route. Platform mode shows top-level links. Store mode
 * shows grouped store management links.
 *
 * @returns The sidebar element.
 */
export function Sidebar() {
  const pathname = usePathname();
  const { store } = useStore();
  const [collapsed, setCollapsed] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    Commerce: true,
    Customers: true,
    Marketing: true,
    Operations: true,
    Settings: true,
  });
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [pendingOrderCount, setPendingOrderCount] = useState(0);

  // Determine sidebar mode from pathname
  const isStoreMode = store !== null && pathname.startsWith(`/stores/${store.id}`);

  useEffect(() => {
    const stored = localStorage.getItem("sidebar-collapsed");
    if (stored === "true") setCollapsed(true);
  }, []);

  // Fetch unread notification count.
  useEffect(() => {
    async function fetchUnread() {
      const res = await api.get<{ count: number }>("/api/v1/notifications/unread-count");
      if (res.data) setUnreadNotifications(res.data.count);
    }
    fetchUnread();
    const interval = setInterval(fetchUnread, 60_000);
    return () => clearInterval(interval);
  }, []);

  // Fetch pending order count for current store.
  useEffect(() => {
    if (!store?.id) {
      setPendingOrderCount(0);
      return;
    }
    async function fetchPending() {
      const res = await api.get<{ total: number } | { items: unknown[] }>(
        `/api/v1/stores/${store!.id}/orders?status=pending&per_page=1`
      );
      if (res.data && "total" in res.data) {
        setPendingOrderCount(res.data.total);
      }
    }
    fetchPending();
  }, [store?.id]);

  function toggleCollapse() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem("sidebar-collapsed", String(next));
  }

  function toggleGroup(title: string) {
    setExpandedGroups((prev) => ({ ...prev, [title]: !prev[title] }));
  }

  function isActive(href: string): boolean {
    if (href === "/" && pathname === "/") return true;
    if (href === "/" && pathname !== "/") return false;
    if (isStoreMode && store && href === `/stores/${store.id}`) {
      return pathname === href;
    }
    if (href !== "/") return pathname.startsWith(href);
    return false;
  }

  const storeNavGroups = isStoreMode && store ? getStoreNavGroups(store.id) : [];
  const platformNavItems = getPlatformNavItems().map((item) => {
    if (item.label === "Notifications" && unreadNotifications > 0) {
      return { ...item, badge: unreadNotifications };
    }
    return item;
  });

  // Inject pending order badge into store mode nav.
  if (pendingOrderCount > 0) {
    for (const group of storeNavGroups) {
      for (const item of group.items) {
        if (item.label === "Orders") {
          item.badge = pendingOrderCount;
        }
      }
    }
  }

  return (
    <aside
      className={cn(
        "flex h-screen flex-col border-r bg-sidebar text-sidebar-foreground transition-all duration-300 shrink-0",
        collapsed ? "w-14" : "w-56"
      )}
    >
      {/* Header */}
      <div className="flex h-12 items-center border-b border-sidebar-border px-3">
        {!collapsed && (
          <Link
            href={isStoreMode && store ? `/stores/${store.id}` : "/"}
            className="flex items-center gap-2 truncate font-heading text-sm font-semibold hover:text-primary transition-colors"
          >
            <Store className="size-4 shrink-0 text-primary" />
            <span className="truncate">
              {isStoreMode && store ? store.name : "Dashboard"}
            </span>
          </Link>
        )}
        {collapsed && (
          <Link
            href={isStoreMode && store ? `/stores/${store.id}` : "/"}
            className="mx-auto"
          >
            <Store className="size-4 text-primary" />
          </Link>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
        {isStoreMode ? (
          /* Store mode: grouped navigation */
          storeNavGroups.map((group) => (
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
                  {group.items.map((item) => (
                    <NavLink
                      key={item.href}
                      item={item}
                      active={isActive(item.href)}
                      collapsed={collapsed}
                    />
                  ))}
                </ul>
              )}
            </div>
          ))
        ) : (
          /* Platform mode: flat navigation */
          <ul className="space-y-0.5">
            {platformNavItems.map((item) => (
              <NavLink
                key={item.href}
                item={item}
                active={isActive(item.href)}
                collapsed={collapsed}
              />
            ))}
          </ul>
        )}
      </nav>

      {/* Footer */}
      <div className="border-t border-sidebar-border px-2 py-2">
        <div
          className={cn(
            "flex items-center",
            collapsed ? "flex-col gap-1" : "justify-between px-1"
          )}
        >
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
      </div>
    </aside>
  );
}

/**
 * Individual navigation link used in both platform and store modes.
 */
function NavLink({
  item,
  active,
  collapsed,
}: {
  item: NavItem;
  active: boolean;
  collapsed: boolean;
}) {
  const Icon = item.icon;
  return (
    <li>
      <Link
        href={item.href}
        title={collapsed ? item.label : undefined}
        className={cn(
          "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors relative",
          active
            ? "bg-sidebar-accent text-sidebar-primary font-medium border-l-2 border-sidebar-primary"
            : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground border-l-2 border-transparent",
          collapsed && "justify-center px-0"
        )}
      >
        <span className="relative shrink-0">
          <Icon
            className={cn("size-4", active && "text-sidebar-primary")}
          />
          {collapsed && item.badge && item.badge > 0 && (
            <span className="absolute -top-1.5 -right-1.5 flex size-3.5 items-center justify-center rounded-full bg-destructive text-[8px] font-bold text-destructive-foreground">
              {item.badge > 9 ? "9+" : item.badge}
            </span>
          )}
        </span>
        {!collapsed && <span className="truncate">{item.label}</span>}
        {!collapsed && item.badge && item.badge > 0 ? (
          <span className="ml-auto flex size-5 items-center justify-center rounded-full bg-destructive text-[10px] font-bold text-destructive-foreground">
            {item.badge > 99 ? "99+" : item.badge}
          </span>
        ) : null}
      </Link>
    </li>
  );
}
