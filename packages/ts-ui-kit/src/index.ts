/**
 * @ecomm/ui-kit — Shared UI components, hooks, and utilities.
 *
 * For Developers:
 *   This is the main entry point. Import components, utilities,
 *   and types from here or from specific sub-paths.
 *
 *   Example:
 *     import { Shell, Button, FadeIn, cn } from "@ecomm/ui-kit";
 *     import { ApiClient } from "@ecomm/ui-kit/lib/api";
 *     import { createAuthManager } from "@ecomm/ui-kit/lib/auth";
 */

// ── Types ──
export type { NavItem, PlanTier, ServiceConfig } from "./types";

// ── UI Primitives ──
export { Button, buttonVariants } from "./components/ui/button";
export type { ButtonProps } from "./components/ui/button";
export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "./components/ui/card";
export { Input } from "./components/ui/input";
export type { InputProps } from "./components/ui/input";
export { Skeleton } from "./components/ui/skeleton";
export { Badge, badgeVariants } from "./components/ui/badge";
export type { BadgeProps } from "./components/ui/badge";

// ── Motion Primitives ──
export { FadeIn, StaggerChildren, PageTransition, AnimatedCounter } from "./components/motion";

// ── Shell Components ──
export { Shell } from "./components/shell";
export type { ShellProps } from "./components/shell";
export { Sidebar } from "./components/sidebar";
export type { SidebarProps } from "./components/sidebar";
export { TopBar } from "./components/top-bar";
export type { TopBarProps } from "./components/top-bar";

// ── Lib ──
export { cn } from "./lib/utils";
export { ApiClient } from "./lib/api";
export type { ApiResponse } from "./lib/api";
export { createAuthManager } from "./lib/auth";
export type { AuthManager } from "./lib/auth";
