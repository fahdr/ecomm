/**
 * Sticky navigation bar for the landing page.
 *
 * **Behavior:**
 * - Starts transparent, transitions to a frosted glass background on scroll.
 * - Logo + product name on the left.
 * - Navigation links (Features, Pricing, Docs) centered.
 * - Login + Get Started CTA buttons on the right.
 * - Mobile: hamburger menu that expands to a full-width dropdown.
 *
 * **For Developers:**
 *   - Scroll detection uses a `useEffect` with `scroll` event listener.
 *   - No external dependencies — all state managed via React hooks.
 *   - Mobile menu uses CSS transitions for open/close animation.
 *   - All content is config-driven from `landing.config.ts`.
 *
 * **For QA Engineers:**
 *   - Test scroll behavior: navbar should become opaque after ~50px scroll.
 *   - Test mobile menu: hamburger toggle, link clicks close menu.
 *   - Verify all nav links scroll to the correct sections.
 *   - Test keyboard navigation (Tab, Enter, Escape).
 *
 * **For End Users:**
 *   - Click the logo to scroll to the top.
 *   - Use the nav links to jump to page sections.
 *   - On mobile, tap the hamburger icon to access navigation.
 */
"use client";

import { useState, useEffect, useCallback } from "react";
import { landingConfig } from "@/landing.config";

/**
 * Renders the sticky navigation bar.
 *
 * @returns The navbar JSX element.
 */
export function Navbar() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  /**
   * Handles scroll events to toggle the navbar background.
   * Applies the frosted glass effect after scrolling 50px.
   */
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50);
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  /**
   * Closes the mobile menu and smoothly scrolls to the target section.
   *
   * @param sectionId - The HTML id of the section to scroll to.
   */
  const scrollToSection = useCallback(
    (sectionId: string) => {
      setIsMobileMenuOpen(false);
      const element = document.getElementById(sectionId);
      if (element) {
        element.scrollIntoView({ behavior: "smooth" });
      }
    },
    []
  );

  /** Navigation link definitions. */
  const navLinks = [
    { label: "Features", sectionId: "features" },
    { label: "How It Works", sectionId: "how-it-works" },
    { label: "Pricing", sectionId: "pricing" },
  ];

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled
          ? "glass shadow-lg shadow-black/10"
          : "bg-transparent"
      }`}
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between sm:h-20">
          {/* ── Logo + Product Name ── */}
          <button
            onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
            className="flex items-center gap-2.5 transition-opacity hover:opacity-80"
            aria-label={`${landingConfig.name} — scroll to top`}
          >
            {/* Abstract logo mark */}
            <div
              className="flex h-9 w-9 items-center justify-center rounded-lg"
              style={{ background: `var(--landing-primary-hex)` }}
            >
              <span className="text-lg font-bold text-white">
                {landingConfig.name.charAt(0)}
              </span>
            </div>
            <span className="text-lg font-bold tracking-tight font-heading"
              style={{ color: "var(--landing-text)" }}
            >
              {landingConfig.name}
            </span>
          </button>

          {/* ── Desktop Navigation Links ── */}
          <div className="hidden items-center gap-8 md:flex">
            {navLinks.map((link) => (
              <button
                key={link.sectionId}
                onClick={() => scrollToSection(link.sectionId)}
                className="text-sm font-medium transition-colors hover:opacity-100"
                style={{ color: "var(--landing-text-muted)" }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.color = "var(--landing-text)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.color = "var(--landing-text-muted)")
                }
              >
                {link.label}
              </button>
            ))}
          </div>

          {/* ── Desktop CTA Buttons ── */}
          <div className="hidden items-center gap-3 md:flex">
            <a
              href={landingConfig.dashboardUrl}
              className="rounded-lg px-4 py-2 text-sm font-medium transition-colors"
              style={{ color: "var(--landing-text-muted)" }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.color = "var(--landing-text)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.color = "var(--landing-text-muted)")
              }
            >
              Log in
            </a>
            <a
              href={landingConfig.dashboardUrl}
              className="rounded-lg px-5 py-2.5 text-sm font-semibold text-white transition-all hover:scale-105 active:scale-95"
              style={{ backgroundColor: "var(--landing-primary-hex)" }}
            >
              {landingConfig.hero.cta}
            </a>
          </div>

          {/* ── Mobile Hamburger Button ── */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="flex h-10 w-10 items-center justify-center rounded-lg transition-colors md:hidden"
            style={{ color: "var(--landing-text)" }}
            aria-label={isMobileMenuOpen ? "Close menu" : "Open menu"}
            aria-expanded={isMobileMenuOpen}
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              {isMobileMenuOpen ? (
                <>
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </>
              ) : (
                <>
                  <line x1="4" y1="8" x2="20" y2="8" />
                  <line x1="4" y1="16" x2="20" y2="16" />
                </>
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* ── Mobile Menu Dropdown ── */}
      <div
        className={`overflow-hidden transition-all duration-300 md:hidden ${
          isMobileMenuOpen
            ? "max-h-80 border-t opacity-100"
            : "max-h-0 opacity-0"
        }`}
        style={{
          borderColor: "var(--landing-border)",
          background: "var(--landing-bg-hex)",
        }}
      >
        <div className="space-y-1 px-4 py-4">
          {navLinks.map((link) => (
            <button
              key={link.sectionId}
              onClick={() => scrollToSection(link.sectionId)}
              className="block w-full rounded-lg px-4 py-3 text-left text-sm font-medium transition-colors"
              style={{ color: "var(--landing-text-muted)" }}
            >
              {link.label}
            </button>
          ))}
          <div className="border-t pt-3" style={{ borderColor: "var(--landing-border)" }}>
            <a
              href={landingConfig.dashboardUrl}
              className="block w-full rounded-lg px-4 py-3 text-center text-sm font-semibold text-white"
              style={{ backgroundColor: "var(--landing-primary-hex)" }}
            >
              {landingConfig.hero.cta}
            </a>
          </div>
        </div>
      </div>
    </nav>
  );
}
