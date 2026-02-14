/**
 * Light/dark mode toggle for the storefront.
 *
 * Uses ``next-themes`` to switch between light and dark themes.
 * Displays a sun icon in dark mode and a moon icon in light mode.
 *
 * **For Developers:**
 *   This is a client component. Uses ``useTheme()`` from ``next-themes``.
 *   Handles hydration mismatch by not rendering until mounted.
 *
 * @returns A toggle button for switching between light and dark mode.
 */
"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Sun, Moon } from "lucide-react";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return <div className="h-9 w-9" />;
  }

  return (
    <button
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      className="rounded-full p-2 text-theme-muted hover:text-theme-primary hover:bg-theme-surface transition-colors"
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
    >
      {theme === "dark" ? (
        <Sun className="h-5 w-5" />
      ) : (
        <Moon className="h-5 w-5" />
      )}
    </button>
  );
}
