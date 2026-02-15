/**
 * Theme toggle button for switching between light and dark modes.
 *
 * Uses next-themes to manage the theme state. Displays a Sun icon in dark mode
 * and a Moon icon in light mode, with a smooth rotation animation on toggle.
 *
 * **For Developers:**
 *   - Requires ThemeProvider from next-themes to be wrapping the app
 *   - Uses lucide-react icons (Sun, Moon)
 *   - Mounted state prevents hydration mismatch
 *
 * **For QA:**
 *   - Button should toggle between light/dark modes
 *   - Icon should animate smoothly on toggle
 *   - Theme should persist across page refreshes (stored in localStorage)
 */

"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Renders a toggle button that switches between light and dark themes.
 *
 * @param className - Optional additional CSS classes to apply.
 * @returns A button element with animated Sun/Moon icon.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <Button variant="ghost" size="icon" className={className} aria-label="Toggle theme">
        <span className="size-4" />
      </Button>
    );
  }

  const isDark = theme === "dark";

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className={className}
    >
      <Sun
        className="size-4 rotate-0 scale-100 transition-transform duration-300 dark:-rotate-90 dark:scale-0"
      />
      <Moon
        className="absolute size-4 rotate-90 scale-0 transition-transform duration-300 dark:rotate-0 dark:scale-100"
      />
    </Button>
  );
}
