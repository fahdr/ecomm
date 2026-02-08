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
 *   - Template list is static — no API call needed.
 *   - Each template card shows the trigger event and preview.
 *
 * **For Developers:**
 *   Email templates live in ``backend/app/templates/email/``.
 *   The ``EmailService`` class in ``backend/app/services/email_service.py``
 *   handles rendering and sending. Future: add SMTP config form that
 *   persists to a store-level settings table.
 */

"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
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

export default function EmailSettingsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { user, loading: authLoading } = useAuth();
  const [store, setStore] = useState<Store | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (authLoading || !user) return;
    async function fetchStore() {
      const result = await api.get<Store>(`/api/v1/stores/${id}`);
      if (result.error) {
        setNotFound(true);
      } else {
        setStore(result.data!);
      }
      setLoading(false);
    }
    fetchStore();
  }, [id, user, authLoading]);

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <h2 className="text-xl font-semibold">Store not found</h2>
        <Link href="/stores">
          <Button variant="outline">Back to stores</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Link
            href="/stores"
            className="text-lg font-semibold hover:underline"
          >
            Stores
          </Link>
          <span className="text-muted-foreground">/</span>
          <Link
            href={`/stores/${id}`}
            className="text-lg font-semibold hover:underline"
          >
            {store?.name}
          </Link>
          <span className="text-muted-foreground">/</span>
          <h1 className="text-lg font-semibold">Email</h1>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-6 p-6">
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
            <CardTitle>Email Templates</CardTitle>
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
    </div>
  );
}
