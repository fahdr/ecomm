/**
 * Dedicated pricing page (`/pricing`).
 *
 * A standalone page for users who navigate directly to pricing. Includes:
 * 1. Full pricing cards with all tier details
 * 2. Feature comparison table
 * 3. FAQ section with common pricing questions
 * 4. CTA section at the bottom
 *
 * **For Developers:**
 *   - This page reuses the `PricingCards` component from the main page.
 *   - The FAQ section is hardcoded here but could be moved to config
 *     if different services need different FAQs.
 *   - Uses the same `useScrollReveal` pattern as the main page.
 *   - Navbar and Footer are included for standalone page navigation.
 *
 * **For QA Engineers:**
 *   - Verify this page is accessible at `/pricing` in the static export.
 *   - Check that the pricing cards match those on the main page.
 *   - Test FAQ accordion: clicking a question should toggle the answer.
 *   - Verify all CTA buttons link to the dashboard URL.
 *
 * **For Project Managers:**
 *   - FAQ content should be reviewed and updated per service launch.
 *   - The pricing page uses the same data source as the main page,
 *     so pricing changes only need to happen in one place.
 *
 * **For End Users:**
 *   - Compare all plan features in detail.
 *   - Read the FAQ for common questions about billing and plans.
 *
 * @returns The complete pricing page.
 */
"use client";

import { useEffect, useState, useCallback } from "react";
import { Navbar } from "@/components/navbar";
import { PricingCards } from "@/components/pricing-cards";
import { CallToAction } from "@/components/cta";
import { Footer } from "@/components/footer";
import { landingConfig } from "@/landing.config";

/**
 * Scroll reveal hook (duplicated from main page for static export independence).
 * In a production setup, extract this to a shared hooks file.
 */
function useScrollReveal() {
  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    if (prefersReducedMotion) {
      document.querySelectorAll(".reveal, .reveal-left, .reveal-right, .reveal-scale").forEach((el) => {
        el.classList.add("is-visible");
      });
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15, rootMargin: "0px 0px -50px 0px" }
    );

    const elements = document.querySelectorAll(
      ".reveal, .reveal-left, .reveal-right, .reveal-scale"
    );
    elements.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, []);
}

/** FAQ item definition. */
interface FaqItem {
  question: string;
  answer: string;
}

/** Common pricing FAQ entries. Update per service as needed. */
const faqItems: FaqItem[] = [
  {
    question: "Can I try before I buy?",
    answer:
      "Absolutely! Our Free plan gives you full access to core features with generous limits. No credit card required. When you are ready to upgrade, start a 14-day free trial of Pro with all premium features unlocked.",
  },
  {
    question: "What happens when my trial ends?",
    answer:
      "When your 14-day Pro trial ends, your account automatically downgrades to the Free plan. You won't lose any data, but premium features will be restricted until you subscribe.",
  },
  {
    question: "Can I change plans at any time?",
    answer:
      "Yes! You can upgrade, downgrade, or cancel your plan at any time. When upgrading, you'll be prorated for the remainder of your billing cycle. Downgrades take effect at the end of your current billing period.",
  },
  {
    question: "Do you offer annual billing?",
    answer:
      "Yes, annual billing is available at a 20% discount compared to monthly pricing. Contact our sales team or switch to annual billing in your account settings.",
  },
  {
    question: "What payment methods do you accept?",
    answer:
      "We accept all major credit cards (Visa, Mastercard, American Express), as well as PayPal and bank transfers for Enterprise plans. All payments are processed securely through Stripe.",
  },
  {
    question: "Is there a setup fee?",
    answer:
      "No. There are no setup fees, hidden charges, or long-term contracts. You pay only for the plan you choose, and you can cancel anytime.",
  },
];

/**
 * Collapsible FAQ item component.
 *
 * @param props.item - The FAQ item with question and answer.
 * @param props.isOpen - Whether the FAQ item is currently expanded.
 * @param props.onToggle - Callback to toggle the FAQ item.
 * @returns The FAQ item JSX element.
 */
function FaqAccordionItem({
  item,
  isOpen,
  onToggle,
}: {
  item: FaqItem;
  isOpen: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      className="border-b"
      style={{ borderColor: "var(--landing-border)" }}
    >
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between py-5 text-left transition-colors"
        aria-expanded={isOpen}
      >
        <span
          className="pr-4 text-base font-medium"
          style={{ color: "var(--landing-text)" }}
        >
          {item.question}
        </span>
        <svg
          className={`h-5 w-5 shrink-0 transition-transform duration-300 ${
            isOpen ? "rotate-180" : ""
          }`}
          style={{ color: "var(--landing-text-muted)" }}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      <div
        className={`overflow-hidden transition-all duration-300 ${
          isOpen ? "max-h-60 pb-5 opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        <p
          className="leading-relaxed"
          style={{ color: "var(--landing-text-muted)" }}
        >
          {item.answer}
        </p>
      </div>
    </div>
  );
}

/**
 * Dedicated pricing page component.
 *
 * @returns The complete pricing page with tiers, comparison, FAQ, and CTA.
 */
export default function PricingPage() {
  useScrollReveal();
  const [openFaqIndex, setOpenFaqIndex] = useState<number | null>(null);

  /**
   * Toggles a FAQ accordion item open/closed.
   *
   * @param index - The index of the FAQ item to toggle.
   */
  const toggleFaq = useCallback(
    (index: number) => {
      setOpenFaqIndex(openFaqIndex === index ? null : index);
    },
    [openFaqIndex]
  );

  return (
    <main className="relative min-h-screen">
      <Navbar />

      {/* ── Page Header ── */}
      <section className="relative pt-32 pb-16 sm:pt-40 sm:pb-20">
        {/* Background glow */}
        <div className="pointer-events-none absolute inset-0">
          <div
            className="absolute left-1/2 top-0 h-[400px] w-[600px] -translate-x-1/2 rounded-full opacity-10 blur-[120px]"
            style={{ background: "var(--landing-primary-hex)" }}
          />
        </div>

        <div className="relative z-10 mx-auto max-w-4xl px-4 text-center sm:px-6 lg:px-8">
          <h1
            className="mb-4 text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl font-heading"
            style={{ color: "var(--landing-text)" }}
          >
            Choose your{" "}
            <span className="gradient-text">plan</span>
          </h1>
          <p
            className="mx-auto max-w-2xl text-lg"
            style={{ color: "var(--landing-text-muted)" }}
          >
            Start free and scale as you grow. Every plan includes a 14-day trial
            of premium features.
          </p>
        </div>
      </section>

      {/* ── Pricing Cards ── */}
      <PricingCards />

      {/* ── Feature Comparison Table ── */}
      <section className="py-16 sm:py-24">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <div className="reveal mb-12 text-center">
            <h2
              className="mb-4 text-2xl font-bold tracking-tight sm:text-3xl font-heading"
              style={{ color: "var(--landing-text)" }}
            >
              Compare plans in detail
            </h2>
          </div>

          <div className="reveal overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderColor: "var(--landing-border)" }}>
                  <th
                    className="border-b py-4 text-left font-medium"
                    style={{
                      color: "var(--landing-text-muted)",
                      borderColor: "var(--landing-border)",
                    }}
                  >
                    Feature
                  </th>
                  {landingConfig.pricing.map((tier) => (
                    <th
                      key={tier.tier}
                      className="border-b py-4 text-center font-semibold"
                      style={{
                        color: tier.popular
                          ? "var(--landing-primary-hex)"
                          : "var(--landing-text)",
                        borderColor: "var(--landing-border)",
                      }}
                    >
                      {tier.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {/* Collect all unique features across tiers */}
                {(() => {
                  const allFeatures = new Set<string>();
                  landingConfig.pricing.forEach((tier) =>
                    tier.features.forEach((f) => allFeatures.add(f))
                  );
                  return Array.from(allFeatures).map((feature) => (
                    <tr key={feature}>
                      <td
                        className="border-b py-3"
                        style={{
                          color: "var(--landing-text-muted)",
                          borderColor: "var(--landing-border)",
                        }}
                      >
                        {feature}
                      </td>
                      {landingConfig.pricing.map((tier) => (
                        <td
                          key={`${tier.tier}-${feature}`}
                          className="border-b py-3 text-center"
                          style={{ borderColor: "var(--landing-border)" }}
                        >
                          {tier.features.includes(feature) ? (
                            <svg
                              className="mx-auto h-5 w-5"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2.5"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              style={{ color: "var(--landing-primary-hex)" }}
                            >
                              <polyline points="20 6 9 17 4 12" />
                            </svg>
                          ) : (
                            <span
                              style={{
                                color: "var(--landing-text-muted)",
                                opacity: 0.3,
                              }}
                            >
                              &mdash;
                            </span>
                          )}
                        </td>
                      ))}
                    </tr>
                  ));
                })()}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ── FAQ Section ── */}
      <section className="py-16 sm:py-24">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <div className="reveal mb-12 text-center">
            <h2
              className="mb-4 text-2xl font-bold tracking-tight sm:text-3xl font-heading"
              style={{ color: "var(--landing-text)" }}
            >
              Frequently asked questions
            </h2>
            <p
              className="text-base"
              style={{ color: "var(--landing-text-muted)" }}
            >
              Everything you need to know about {landingConfig.name} pricing.
            </p>
          </div>

          <div className="reveal">
            {faqItems.map((item, index) => (
              <FaqAccordionItem
                key={item.question}
                item={item}
                isOpen={openFaqIndex === index}
                onToggle={() => toggleFaq(index)}
              />
            ))}
          </div>
        </div>
      </section>

      {/* ── Bottom CTA ── */}
      <CallToAction />
      <Footer />
    </main>
  );
}
