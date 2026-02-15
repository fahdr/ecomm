/**
 * Navbar component for the master suite landing page.
 *
 * Sticky top bar with blur background, suite logo, navigation links,
 * and a primary CTA button.
 *
 * **For Developers:**
 *   - Uses `backdrop-filter: blur()` for the frosted glass effect.
 *   - Scroll links use hash anchors with `scroll-behavior: smooth` from CSS.
 *   - The mobile menu is a simple slide-down drawer toggled via state.
 *
 * **For QA Engineers:**
 *   - Verify sticky behavior when scrolling.
 *   - Test all anchor links navigate to the correct sections.
 *   - Test mobile menu open/close on small viewports.
 *
 * @returns The navbar JSX element.
 */
"use client";

import { useState } from "react";

/** Navigation link items for the top bar. */
const navLinks = [
  { label: "Products", href: "#products" },
  { label: "Pricing", href: "#pricing" },
  { label: "How It Works", href: "#how-it-works" },
];

export function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 border-b animate-fade-in-down"
      style={{
        borderColor: "var(--color-border)",
        background: "rgba(13, 17, 23, 0.85)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
      }}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <a href="#" className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-[var(--color-brand)] to-[var(--color-accent-violet)]">
            <svg
              className="h-5 w-5 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
          </div>
          <span className="text-lg font-bold tracking-tight" style={{ fontFamily: "var(--font-heading)" }}>
            DropShip{" "}
            <span style={{ color: "var(--color-brand)" }}>Suite</span>
          </span>
        </a>

        {/* Desktop links */}
        <div className="hidden items-center gap-8 md:flex">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm font-medium transition-colors hover:text-[var(--color-brand)]"
              style={{ color: "var(--color-text-muted)" }}
            >
              {link.label}
            </a>
          ))}
          <a
            href="#pricing"
            className="rounded-lg px-5 py-2.5 text-sm font-semibold text-white transition-all hover:scale-105 active:scale-95"
            style={{ backgroundColor: "var(--color-brand)" }}
          >
            Get Started
          </a>
        </div>

        {/* Mobile hamburger */}
        <button
          className="flex h-10 w-10 items-center justify-center rounded-lg md:hidden"
          style={{ color: "var(--color-text)" }}
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle menu"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            {mobileOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile menu drawer */}
      {mobileOpen && (
        <div
          className="border-t px-4 pb-4 pt-2 md:hidden"
          style={{ borderColor: "var(--color-border)", background: "rgba(13, 17, 23, 0.95)" }}
        >
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="block rounded-lg px-4 py-3 text-sm font-medium transition-colors hover:bg-[var(--color-surface-raised)]"
              style={{ color: "var(--color-text-muted)" }}
              onClick={() => setMobileOpen(false)}
            >
              {link.label}
            </a>
          ))}
          <a
            href="#pricing"
            className="mt-2 block rounded-lg px-4 py-3 text-center text-sm font-semibold text-white"
            style={{ backgroundColor: "var(--color-brand)" }}
            onClick={() => setMobileOpen(false)}
          >
            Get Started
          </a>
        </div>
      )}
    </nav>
  );
}
