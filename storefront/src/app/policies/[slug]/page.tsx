/**
 * Dynamic policy page renderer.
 *
 * Serves shipping, returns, privacy, and terms policy pages from
 * built-in default content. Store owners can eventually customize
 * these, but defaults provide a working storefront out of the box.
 *
 * **For End Users:**
 *   Read our store policies for shipping, returns, privacy, and terms.
 *
 * **For QA Engineers:**
 *   - Valid slugs: ``shipping``, ``returns``, ``privacy``, ``terms``.
 *   - Invalid slugs show a "Policy not found" message.
 *   - Breadcrumb links: Home > Policies > {Title}.
 *
 * **For Developers:**
 *   Server component. Policy content is hardcoded as a record keyed
 *   by slug. Uses ``use()`` for the async params promise (Next.js 16).
 */

import Link from "next/link";
import type { Metadata } from "next";

/**
 * Policy content keyed by URL slug.
 */
const policies: Record<string, { title: string; sections: { heading: string; body: string }[] }> = {
  shipping: {
    title: "Shipping Policy",
    sections: [
      {
        heading: "Processing Time",
        body: "Orders are processed within 1\u20133 business days after payment confirmation. During peak periods, processing may take up to 5 business days.",
      },
      {
        heading: "Shipping Methods & Delivery",
        body: "We offer standard and express shipping options. Standard shipping typically takes 7\u201314 business days, while express shipping takes 3\u20137 business days. Delivery times vary by destination and carrier availability.",
      },
      {
        heading: "Tracking",
        body: "Once your order has shipped, you will receive a confirmation email with a tracking number. You can also view tracking information in your account under Order History.",
      },
      {
        heading: "International Shipping",
        body: "We ship to most countries worldwide. International orders may be subject to customs duties and taxes, which are the responsibility of the recipient. Delivery times for international orders vary by destination.",
      },
    ],
  },
  returns: {
    title: "Returns Policy",
    sections: [
      {
        heading: "Return Window",
        body: "You may request a return within 30 days of receiving your order. Items must be unused, in their original packaging, and in the same condition you received them.",
      },
      {
        heading: "How to Request a Return",
        body: "To initiate a return, contact our support team with your order number and reason for the return. We will provide return instructions and, if applicable, a return shipping label.",
      },
      {
        heading: "Refunds",
        body: "Once we receive and inspect your returned item, we will process your refund within 5\u201310 business days. Refunds are issued to the original payment method. Shipping costs are non-refundable unless the return is due to our error.",
      },
      {
        heading: "Exchanges",
        body: "If you received a defective or incorrect item, we will ship a replacement at no additional cost. Please contact us within 7 days of delivery for exchange requests.",
      },
    ],
  },
  privacy: {
    title: "Privacy Policy",
    sections: [
      {
        heading: "Information We Collect",
        body: "We collect information you provide directly, such as your name, email address, shipping address, and payment details when you place an order. We also collect browsing data and cookies to improve your shopping experience.",
      },
      {
        heading: "How We Use Your Information",
        body: "Your information is used to process orders, communicate about your purchases, improve our services, and send promotional content (with your consent). We never sell your personal data to third parties.",
      },
      {
        heading: "Data Security",
        body: "We implement industry-standard security measures including SSL encryption, secure payment processing, and regular security audits to protect your personal information.",
      },
      {
        heading: "Your Rights",
        body: "You have the right to access, correct, or delete your personal data at any time. You may also opt out of marketing communications. Contact us to exercise any of these rights.",
      },
    ],
  },
  terms: {
    title: "Terms & Conditions",
    sections: [
      {
        heading: "Agreement",
        body: "By accessing and using this store, you agree to be bound by these Terms and Conditions. If you do not agree with any part of these terms, please do not use our services.",
      },
      {
        heading: "Orders & Payment",
        body: "All orders are subject to availability and confirmation. Prices are displayed in the store's default currency and may be subject to change. Payment must be completed at the time of purchase through our accepted payment methods.",
      },
      {
        heading: "Intellectual Property",
        body: "All content on this store, including text, images, logos, and designs, is the property of the store owner and is protected by intellectual property laws. You may not reproduce or distribute any content without prior written permission.",
      },
      {
        heading: "Limitation of Liability",
        body: "We are not liable for any indirect, incidental, or consequential damages arising from your use of our services or products. Our total liability is limited to the amount you paid for the applicable order.",
      },
      {
        heading: "Changes to Terms",
        body: "We reserve the right to update these terms at any time. Changes take effect immediately upon posting. Continued use of the store after changes constitutes acceptance of the new terms.",
      },
    ],
  },
};

/**
 * Generate page metadata from the policy slug.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const policy = policies[slug];
  return {
    title: policy?.title ?? "Policy Not Found",
  };
}

/**
 * Generate static params for all known policy slugs.
 */
export function generateStaticParams() {
  return Object.keys(policies).map((slug) => ({ slug }));
}

/**
 * Policy page component.
 *
 * @param props - Page props with params promise.
 * @returns Rendered policy content or a not-found message.
 */
export default async function PolicyPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const policy = policies[slug];

  if (!policy) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <h1 className="text-2xl font-heading font-bold mb-4">Policy not found</h1>
        <p className="text-theme-muted mb-6">
          The policy page you&apos;re looking for doesn&apos;t exist.
        </p>
        <Link
          href="/"
          className="text-theme-primary hover:underline text-sm"
        >
          Return to home
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      {/* Breadcrumb */}
      <nav className="text-sm text-theme-muted mb-6">
        <Link href="/" className="hover:text-theme-primary transition-colors">
          Home
        </Link>
        <span className="mx-2">/</span>
        <span>{policy.title}</span>
      </nav>

      <h1 className="text-3xl font-heading font-bold tracking-tight mb-8">
        {policy.title}
      </h1>

      <div className="space-y-8">
        {policy.sections.map((section) => (
          <div key={section.heading}>
            <h2 className="text-lg font-heading font-semibold mb-2">
              {section.heading}
            </h2>
            <p className="text-theme-muted leading-relaxed">{section.body}</p>
          </div>
        ))}
      </div>

      <div className="mt-12 pt-6 border-t border-theme text-sm text-theme-muted">
        <p>
          Last updated: {new Date().toLocaleDateString("en-US", {
            year: "numeric",
            month: "long",
            day: "numeric",
          })}
        </p>
      </div>
    </div>
  );
}
