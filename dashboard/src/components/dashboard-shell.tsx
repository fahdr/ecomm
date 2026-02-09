/**
 * Dashboard shell component that wraps store-scoped pages.
 *
 * Provides the main layout structure: a collapsible sidebar on the left
 * and a scrollable main content area on the right with a top bar
 * containing breadcrumbs and user info.
 *
 * **For Developers:**
 *   - This component is used by the stores/[id]/layout.tsx
 *   - The sidebar and main content area are flex siblings
 *   - Main content has the dot-pattern background for visual depth
 *   - Breadcrumb items are passed as props from each page
 *
 * **For QA:**
 *   - Sidebar should collapse/expand independently of main content
 *   - Main content should scroll vertically when content overflows
 *   - Dot pattern should be visible on the background
 *   - Top bar should stick to the top of the content area
 */

"use client";

import { Sidebar } from "@/components/sidebar";

/**
 * Renders the dashboard shell with sidebar and main content area.
 *
 * @param children - The page content to render in the main area.
 * @returns The shell layout with sidebar and content.
 */
export function DashboardShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-dot-pattern">
        <div className="min-h-full">
          {children}
        </div>
      </main>
    </div>
  );
}
