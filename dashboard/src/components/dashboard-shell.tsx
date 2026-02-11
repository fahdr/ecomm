/**
 * Unified dashboard shell for all authenticated pages.
 *
 * Provides the main layout structure: a collapsible sidebar on the left,
 * a top bar with breadcrumbs and store switcher, and a scrollable main
 * content area. Used for both platform-level pages (home, stores, billing)
 * and store-scoped pages (/stores/[id]/*).
 *
 * **For Developers:**
 *   - Wraps ALL authenticated routes (not just store-scoped)
 *   - The sidebar auto-switches between platform and store mode
 *   - The top bar provides breadcrumbs and store switching
 *   - Main content has the dot-pattern background for visual depth
 *
 * **For QA:**
 *   - Every authenticated page should render inside this shell
 *   - Sidebar should collapse/expand independently of main content
 *   - Main content should scroll vertically when content overflows
 *   - Breadcrumbs in top bar should update on every navigation
 *   - Dot pattern should be visible on the background
 */

"use client";

import { Sidebar } from "@/components/sidebar";
import { TopBar } from "@/components/top-bar";
import { CommandPalette } from "@/components/command-palette";

/**
 * Renders the unified dashboard shell with sidebar, top bar, and content.
 *
 * @param children - The page content to render in the main area.
 * @returns The shell layout with sidebar, top bar, and scrollable content.
 */
export function DashboardShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto bg-dot-pattern">
          <div className="min-h-full">{children}</div>
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
