/**
 * Webhooks management page.
 *
 * Lists all webhook endpoints configured for a store and provides a dialog
 * to register new webhook subscriptions. Each webhook specifies a URL,
 * a set of subscribed events, and an active/inactive status.
 *
 * **For End Users:**
 *   Connect external services to your store by creating webhook endpoints.
 *   Your server will receive real-time HTTP POST notifications when
 *   subscribed events occur (e.g., order.created, product.updated).
 *
 * **For Developers:**
 *   - Fetches webhooks via `GET /api/v1/stores/{store_id}/webhooks`.
 *   - Creates new webhooks via `POST /api/v1/stores/{store_id}/webhooks`.
 *   - Events are submitted as a comma-separated string, parsed to an array.
 *
 * **For QA Engineers:**
 *   - Verify the webhook list refreshes after creating a new endpoint.
 *   - Verify that the URL field validates as a proper URL.
 *   - Verify that at least one event must be specified.
 *   - Verify that the secret field is optional.
 *   - Verify empty state is shown when no webhooks are registered.
 *
 * **For Project Managers:**
 *   This page corresponds to Feature 23 (API/Webhooks) in the backlog.
 *   Webhooks enable third-party integrations and event-driven workflows.
 */

"use client";

import { FormEvent, useEffect, useState, use } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

/** Shape of a webhook returned by the API. */
interface Webhook {
  id: string;
  url: string;
  events: string[];
  secret: string | null;
  is_active: boolean;
  created_at: string;
  last_triggered_at: string | null;
}

/** Available webhook event types for subscription. */
const AVAILABLE_EVENTS = [
  "order.created",
  "order.updated",
  "order.cancelled",
  "order.fulfilled",
  "product.created",
  "product.updated",
  "product.deleted",
  "customer.created",
  "customer.updated",
  "refund.created",
  "subscription.created",
  "subscription.cancelled",
];

/**
 * WebhooksPage renders the webhook listing and registration dialog.
 *
 * @param params - Route parameters containing the store ID.
 * @returns The rendered webhooks management page.
 */
export default function WebhooksPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { user, loading: authLoading } = useAuth();
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* Create form state */
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formUrl, setFormUrl] = useState("");
  const [formEvents, setFormEvents] = useState("");
  const [formSecret, setFormSecret] = useState("");
  const [formActive, setFormActive] = useState(true);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  /**
   * Fetch all webhooks for this store.
   */
  async function fetchWebhooks() {
    setLoading(true);
    const result = await api.get<{ items: Webhook[] }>(
      `/api/v1/stores/${id}/webhooks`
    );
    if (result.error) {
      setError(result.error.message);
    } else {
      setWebhooks(result.data?.items ?? []);
    }
    setLoading(false);
  }

  useEffect(() => {
    if (authLoading || !user) return;
    fetchWebhooks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, user, authLoading]);

  /**
   * Handle the create-webhook form submission.
   * Parses the events field from comma-separated text into an array.
   *
   * @param e - The form submission event.
   */
  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);

    const eventsList = formEvents
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    if (eventsList.length === 0) {
      setCreateError("At least one event must be specified.");
      setCreating(false);
      return;
    }

    const result = await api.post<Webhook>(
      `/api/v1/stores/${id}/webhooks`,
      {
        url: formUrl,
        events: eventsList,
        secret: formSecret || null,
        is_active: formActive,
      }
    );

    if (result.error) {
      setCreateError(result.error.message);
      setCreating(false);
      return;
    }

    setFormUrl("");
    setFormEvents("");
    setFormSecret("");
    setFormActive(true);
    setDialogOpen(false);
    setCreating(false);
    fetchWebhooks();
  }

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading webhooks...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Link href="/stores" className="text-lg font-semibold hover:underline">
            Stores
          </Link>
          <span className="text-muted-foreground">/</span>
          <Link
            href={`/stores/${id}`}
            className="text-lg font-semibold hover:underline"
          >
            Store
          </Link>
          <span className="text-muted-foreground">/</span>
          <h1 className="text-lg font-semibold">Webhooks</h1>
        </div>

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>Register Webhook</Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>Register Webhook</DialogTitle>
              <DialogDescription>
                Specify a URL and the events your endpoint should receive.
                We will send an HTTP POST to your URL each time a subscribed
                event occurs.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              {createError && (
                <p className="text-sm text-destructive">{createError}</p>
              )}
              <div className="space-y-2">
                <Label htmlFor="wh-url">Endpoint URL</Label>
                <Input
                  id="wh-url"
                  type="url"
                  placeholder="https://example.com/webhook"
                  value={formUrl}
                  onChange={(e) => setFormUrl(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="wh-events">Events</Label>
                <Input
                  id="wh-events"
                  placeholder="order.created, product.updated"
                  value={formEvents}
                  onChange={(e) => setFormEvents(e.target.value)}
                  required
                />
                <p className="text-xs text-muted-foreground">
                  Comma-separated. Available:{" "}
                  {AVAILABLE_EVENTS.join(", ")}
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="wh-secret">
                  Signing Secret{" "}
                  <span className="text-muted-foreground font-normal">
                    (optional)
                  </span>
                </Label>
                <Input
                  id="wh-secret"
                  type="password"
                  placeholder="whsec_..."
                  value={formSecret}
                  onChange={(e) => setFormSecret(e.target.value)}
                />
              </div>
              <div className="flex items-center gap-3">
                <Switch
                  id="wh-active"
                  checked={formActive}
                  onCheckedChange={setFormActive}
                />
                <Label htmlFor="wh-active">Active</Label>
              </div>
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={creating}>
                  {creating ? "Registering..." : "Register Webhook"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </header>

      <main className="p-6">
        {error && (
          <Card className="mb-6 border-destructive/50">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {webhooks.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="text-5xl opacity-20">&lt;/&gt;</div>
            <h2 className="text-xl font-semibold">No webhooks registered</h2>
            <p className="text-muted-foreground max-w-sm">
              Register your first webhook endpoint to receive real-time
              event notifications from your store.
            </p>
            <Button onClick={() => setDialogOpen(true)}>
              Register your first webhook
            </Button>
          </div>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Webhook Endpoints</CardTitle>
              <CardDescription>
                {webhooks.length} endpoint{webhooks.length !== 1 ? "s" : ""}{" "}
                registered
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>URL</TableHead>
                    <TableHead>Events</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last Triggered</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {webhooks.map((wh) => (
                    <TableRow key={wh.id}>
                      <TableCell>
                        <code className="rounded bg-muted px-1.5 py-0.5 text-xs font-mono break-all">
                          {wh.url}
                        </code>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {wh.events.map((evt) => (
                            <Badge key={evt} variant="outline" className="text-xs">
                              {evt}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={wh.is_active ? "default" : "secondary"}
                        >
                          {wh.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {wh.last_triggered_at
                          ? new Date(wh.last_triggered_at).toLocaleString()
                          : "Never"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
