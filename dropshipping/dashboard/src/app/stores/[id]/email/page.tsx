/**
 * Email settings page for a store.
 *
 * Displays transactional email configuration and previews of
 * the available email templates. In development mode, emails are
 * logged to the console instead of being sent via SMTP.
 *
 * **For End Users:**
 *   Review which automated emails your store sends to customers.
 *   Preview email templates for order confirmations, shipping
 *   updates, refund notices, gift cards, and team invitations.
 *
 * **For QA Engineers:**
 *   - The page is read-only in dev mode (no SMTP configured).
 *   - Template list is static -- no API call needed.
 *   - Each template card shows the trigger event and preview.
 *
 * **For Developers:**
 *   Email templates live in ``backend/app/templates/email/``.
 *   The ``EmailService`` class in ``backend/app/services/email_service.py``
 *   handles rendering and sending. Future: add SMTP config form that
 *   persists to a store-level settings table.
 *   Uses ``useStore()`` from store context for the store ID.
 *   Wrapped in ``PageTransition`` for consistent entrance animation.
 *
 * **For Project Managers:**
 *   Implements Feature 11 (Transactional Email) from the backlog.
 *   Covers template preview; SMTP configuration is a future iteration.
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition } from "@/components/motion-wrappers";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/** Template metadata for display. */
interface EmailTemplate {
  name: string;
  file: string;
  trigger: string;
  description: string;
  recipient: string;
}

/** Transactional email templates available in the platform. */
const TEMPLATES: EmailTemplate[] = [
  {
    name: "Order Confirmation",
    file: "order_confirmation.html",
    trigger: "When a customer completes checkout",
    description:
      "Sent to the customer with order details, item list, and total amount.",
    recipient: "Customer",
  },
  {
    name: "Order Shipped",
    file: "order_shipped.html",
    trigger: "When an order status changes to shipped",
    description:
      "Notifies the customer that their order is on the way, with optional tracking number.",
    recipient: "Customer",
  },
  {
    name: "Refund Notification",
    file: "refund_notification.html",
    trigger: "When a refund is processed",
    description:
      "Confirms the refund amount and reason to the customer.",
    recipient: "Customer",
  },
  {
    name: "Welcome Email",
    file: "welcome.html",
    trigger: "When a new customer account is created",
    description:
      "Welcomes the customer to your store with a personalized greeting.",
    recipient: "Customer",
  },
  {
    name: "Password Reset",
    file: "password_reset.html",
    trigger: "When a user requests a password reset",
    description:
      "Contains a secure reset link for the user to set a new password.",
    recipient: "User",
  },
  {
    name: "Gift Card Delivery",
    file: "gift_card.html",
    trigger: "When a gift card is created with a recipient email",
    description:
      "Delivers the gift card code and balance to the recipient.",
    recipient: "Gift Card Recipient",
  },
  {
    name: "Team Invitation",
    file: "team_invite.html",
    trigger: "When a team member is invited",
    description:
      "Invites a user to join your store's team with their assigned role.",
    recipient: "Invited Team Member",
  },
];

/** Store data shape. */
interface Store {
  id: string;
  name: string;
}

/**
 * EmailSettingsPage displays transactional email template configuration.
 *
 * Shows a dev-mode banner, summary stats, and a list of all email
 * templates with their triggers and recipients. Uses the store context
 * for the store ID and PageTransition for entrance animation.
 *
 * @returns The rendered email settings page.
 */
export default function EmailSettingsPage() {
  const { store: contextStore } = useStore();
  const storeId = contextStore!.id;
  const { user, loading: authLoading } = useAuth();
  const [store, setStore] = useState<Store | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (authLoading || !user) return;
    /** Fetch store details for validation. */
    async function fetchStore() {
      const result = await api.get<Store>(`/api/v1/stores/${storeId}`);
      if (result.error) {
        setNotFound(true);
      } else {
        setStore(result.data!);
      }
      setLoading(false);
    }
    fetchStore();
  }, [storeId, user, authLoading]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-16">
        <h2 className="text-xl font-semibold font-heading">Store not found</h2>
        <Link href="/stores">
          <Button variant="outline">Back to stores</Button>
        </Link>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Page heading */}
        <h1 className="text-2xl font-semibold font-heading">Email</h1>

        {/* Status banner */}
        <Card className="border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20">
          <CardContent className="flex items-center gap-3 pt-6">
            <Badge variant="outline" className="border-amber-500 text-amber-700 dark:text-amber-400">
              Dev Mode
            </Badge>
            <p className="text-sm text-muted-foreground">
              Transactional emails are logged to the console in development.
              Configure SMTP settings for production delivery.
            </p>
          </CardContent>
        </Card>

        {/* Summary */}
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Templates</CardDescription>
              <CardTitle className="text-2xl">{TEMPLATES.length}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Customer Emails</CardDescription>
              <CardTitle className="text-2xl">
                {TEMPLATES.filter((t) => t.recipient === "Customer").length}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Internal Emails</CardDescription>
              <CardTitle className="text-2xl">
                {
                  TEMPLATES.filter((t) => t.recipient !== "Customer").length
                }
              </CardTitle>
            </CardHeader>
          </Card>
        </div>

        {/* Template list */}
        <Card>
          <CardHeader>
            <CardTitle className="font-heading">Email Templates</CardTitle>
            <CardDescription>
              Automated emails sent to customers and team members when events
              occur in your store.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {TEMPLATES.map((template) => (
                <div
                  key={template.file}
                  className="flex items-start justify-between rounded-lg border p-4"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium">{template.name}</h3>
                      <Badge variant="secondary">{template.recipient}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {template.description}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      <span className="font-medium">Trigger:</span>{" "}
                      {template.trigger}
                    </p>
                  </div>
                  <Badge variant="outline" className="shrink-0 font-mono text-xs">
                    {template.file}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </main>
    </PageTransition>
  );
}
