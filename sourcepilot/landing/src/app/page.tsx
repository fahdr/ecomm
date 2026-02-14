/**
 * Main landing page for SourcePilot -- composes all sections into a single scroll experience.
 *
 * This is the homepage (`/`) that visitors see first. It assembles:
 * 1. Navbar (sticky, transparent -> glass on scroll)
 * 2. Hero section (full viewport, animated headline + supplier badges)
 * 3. Stats bar (4 key metrics: imports, success rate, platforms, speed)
 * 4. Features grid (6 cards in 3x2 layout)
 * 5. How it works (4-step process: Connect, Discover, Import, Sell)
 * 6. Pricing cards (Free / Starter / Pro / Enterprise)
 * 7. CTA section (final conversion push)
 * 8. Footer (links + social)
 *
 * **For Developers:**
 *   - This is a client component because it uses IntersectionObserver
 *     for scroll-triggered `.reveal` animations.
 *   - The `useScrollReveal` hook observes all elements with the `.reveal`
 *     class and adds `.is-visible` when they enter the viewport.
 *   - All section content is config-driven via `landing.config.ts`.
 *   - The page uses no external animation libraries -- CSS transitions only.
 *
 * **For QA Engineers:**
 *   - Verify all 8 sections render in the correct order.
 *   - Test scroll: elements should animate in as they become visible.
 *   - Test with `prefers-reduced-motion: reduce` -- all elements should
 *     be visible immediately with no animation.
 *   - Check that section anchors (#features, #pricing, etc.) work from
 *     both the navbar and direct URL access.
 *   - Verify the page is fully functional as a static export (no API calls).
 *
 * **For Project Managers:**
 *   - All customization happens in `landing.config.ts`.
 *   - The page is statically exported for CDN hosting.
 *
 * **For End Users:**
 *   - Scroll down to explore SourcePilot features, pricing, and more.
 *   - Use the navigation bar to jump directly to any section.
 *
 * @returns The complete SourcePilot landing page.
 */
"use client";

import { useEffect } from "react";
import { Navbar } from "@/components/navbar";
import { Hero } from "@/components/hero";
import { StatsBar } from "@/components/stats-bar";
import { Features } from "@/components/features";
import { HowItWorks } from "@/components/how-it-works";
import { PricingCards } from "@/components/pricing-cards";
import { CallToAction } from "@/components/cta";
import { Footer } from "@/components/footer";

/**
 * Custom hook that observes all `.reveal` elements and adds `.is-visible`
 * when they scroll into the viewport.
 *
 * Uses the IntersectionObserver API with a 15% visibility threshold,
 * meaning elements animate in when 15% of their area is visible.
 * Once revealed, elements stay visible (observer stops watching them).
 *
 * Respects `prefers-reduced-motion` by immediately making all elements
 * visible without animation when reduced motion is preferred.
 *
 * @example
 * ```tsx
 * function MyPage() {
 *   useScrollReveal();
 *   return <div className="reveal">I animate on scroll!</div>;
 * }
 * ```
 */
function useScrollReveal() {
  useEffect(() => {
    /**
     * If the user prefers reduced motion, skip the observer entirely
     * and show all elements immediately.
     */
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    if (prefersReducedMotion) {
      document.querySelectorAll(".reveal, .reveal-left, .reveal-right, .reveal-scale").forEach((el) => {
        el.classList.add("is-visible");
      });
      return;
    }

    /**
     * Create an IntersectionObserver that watches for elements entering
     * the viewport with at least 15% visibility.
     */
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            /* Once visible, stop watching to save resources */
            observer.unobserve(entry.target);
          }
        });
      },
      {
        threshold: 0.15,
        rootMargin: "0px 0px -50px 0px",
      }
    );

    /* Observe all reveal elements */
    const elements = document.querySelectorAll(
      ".reveal, .reveal-left, .reveal-right, .reveal-scale"
    );
    elements.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, []);
}

/**
 * Landing page root component.
 *
 * @returns The complete landing page with all sections.
 */
export default function LandingPage() {
  useScrollReveal();

  return (
    <main className="relative min-h-screen">
      <Navbar />
      <Hero />
      <StatsBar />
      <Features />
      <HowItWorks />
      <PricingCards />
      <CallToAction />
      <Footer />
    </main>
  );
}
