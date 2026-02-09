/**
 * Newsletter Signup block -- a client-side email subscription form for
 * the storefront homepage.
 *
 * Renders a heading, description, email input, and submit button.  On
 * successful submission a toast notification confirms the subscription.
 *
 * **For Developers:**
 *   This is a **client component** (``"use client"``).  It uses the
 *   ``sonner`` library for toast notifications.  The form is fully
 *   self-contained with local state; no external state management is
 *   needed.  Currently the form does not call a backend endpoint -- it
 *   simulates success after a short delay.  When the backend newsletter
 *   endpoint is implemented, replace the ``handleSubmit`` logic with an
 *   ``api.post`` call.
 *
 * **For QA Engineers:**
 *   - Empty email input prevents submission and shows validation.
 *   - Invalid email format prevents submission.
 *   - Successful submission shows a sonner toast with a success message.
 *   - The submit button is disabled while the form is submitting.
 *   - ``heading`` defaults to "Stay in the loop".
 *   - ``description`` defaults to a generic newsletter prompt.
 *   - After success the input is cleared.
 *
 * **For Project Managers:**
 *   The newsletter block lets store owners collect customer email addresses
 *   directly from the homepage.  This is a key growth tool -- store owners
 *   can later send promotions and updates to subscribers.
 *
 * **For End Users:**
 *   Enter your email to subscribe to the store's newsletter and receive
 *   updates about new products, sales, and exclusive offers.
 *
 * @module blocks/newsletter
 */

"use client";

import { useState } from "react";
import { toast } from "sonner";

/**
 * Props accepted by the {@link Newsletter} component.
 */
interface NewsletterProps {
  /**
   * Block configuration object.  Expected keys:
   * - ``heading``     (string) -- Section heading (default "Stay in the loop").
   * - ``description`` (string) -- Subtitle / description text.
   */
  config: Record<string, unknown>;
}

/**
 * Render a newsletter signup section with an email form.
 *
 * @param props - Component props.
 * @param props.config - Block configuration from the store theme.
 * @returns A section containing a heading, description, and email form.
 */
export function Newsletter({ config }: NewsletterProps) {
  const heading =
    (config.heading as string) || "Stay in the loop";
  const description =
    (config.description as string) ||
    "Subscribe to our newsletter for the latest products, deals, and updates delivered straight to your inbox.";

  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);

  /**
   * Validate the email and simulate a newsletter signup.
   *
   * @param e - The form submission event.
   */
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const trimmed = email.trim();

    // Basic client-side validation
    if (!trimmed || !trimmed.includes("@") || !trimmed.includes(".")) {
      toast.error("Please enter a valid email address.");
      return;
    }

    setSubmitting(true);

    // Simulate API call (replace with real endpoint when available)
    await new Promise((resolve) => setTimeout(resolve, 600));

    toast.success("You're subscribed! Thanks for signing up.");
    setEmail("");
    setSubmitting(false);
  }

  return (
    <section className="bg-theme-surface border-y border-theme">
      <div className="mx-auto max-w-2xl px-6 py-16 text-center">
        <h2 className="font-heading text-3xl font-bold tracking-tight mb-4">
          {heading}
        </h2>
        <p className="text-theme-muted text-base leading-relaxed mb-8">
          {description}
        </p>

        <form
          onSubmit={handleSubmit}
          className="flex flex-col sm:flex-row items-center gap-3 max-w-md mx-auto"
        >
          <label htmlFor="newsletter-email" className="sr-only">
            Email address
          </label>
          <input
            id="newsletter-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
            className="w-full flex-1 rounded-(--theme-radius) border border-theme bg-theme-surface px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary placeholder:text-theme-muted"
          />
          <button
            type="submit"
            disabled={submitting}
            className="btn-primary px-6 py-3 text-sm font-semibold whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Subscribing..." : "Subscribe"}
          </button>
        </form>
      </div>
    </section>
  );
}
