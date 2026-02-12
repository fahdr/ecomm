/**
 * Master suite landing page — the main entry point.
 *
 * Assembles all sections: Navbar, Hero, Service Grid, How It Works,
 * Pricing, CTA, and Footer into a single scrollable page.
 *
 * **For Developers:**
 *   - Each section is a self-contained component with its own
 *     IntersectionObserver for scroll-reveal animations.
 *   - The page uses static export (no server-side rendering).
 *   - All content is driven by `suite.config.ts`.
 *
 * **For Project Managers:**
 *   - This is the main marketing page for the entire product suite.
 *   - It links to each individual service's landing page.
 *   - Pricing shows bundle options (individual pricing on service pages).
 *
 * **For QA Engineers:**
 *   - Verify all sections render in correct order.
 *   - Test scroll-to-section navigation from navbar links.
 *   - Check that all 8 service cards are present.
 *   - Test on mobile, tablet, and desktop viewports.
 *
 * **For End Users:**
 *   - This page gives you an overview of all available tools.
 *   - Scroll down to see each product, how it works, and pricing.
 *   - Click any product card to learn more about that specific tool.
 *
 * @returns The complete landing page JSX element.
 */
import { Navbar } from "@/components/navbar";
import { Hero } from "@/components/hero";
import { ServiceGrid } from "@/components/service-grid";
import { HowItWorks } from "@/components/how-it-works";
import { Pricing } from "@/components/pricing";
import { CTA } from "@/components/cta";
import { Footer } from "@/components/footer";

export default function HomePage() {
  return (
    <>
      <Navbar />
      <Hero />
      <ServiceGrid />
      <HowItWorks />
      <Pricing />
      <CTA />
      <Footer />
    </>
  );
}
