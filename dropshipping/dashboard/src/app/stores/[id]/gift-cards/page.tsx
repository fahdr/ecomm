/**
 * Gift Cards management page.
 *
 * Displays all gift cards for a store with their codes, remaining balances,
 * statuses, and associated customer emails. Provides a dialog to issue
 * new gift cards.
 *
 * **For End Users:**
 *   Issue digital gift cards to customers with customizable initial balances.
 *   Track which cards have been redeemed and their remaining value.
 *
 * **For Developers:**
 *   - Fetches gift cards via `GET /api/v1/stores/{store_id}/gift-cards`.
 *   - Creates new cards via `POST /api/v1/stores/{store_id}/gift-cards`.
 *   - Gift card codes are typically generated server-side.
 *   - Uses `useStore()` context for store ID (provided by the layout).
 *   - Wrapped in `PageTransition` for consistent page-level animations.
 *
 * **For QA Engineers:**
 *   - Verify gift card list refreshes after issuing a new card.
 *   - Verify that the initial balance field only accepts positive numbers.
 *   - Verify that the customer email field is optional.
 *   - Verify empty state displays correctly.
 *
 * **For Project Managers:**
 *   This page corresponds to Feature 20 (Gift Cards) in the backlog.
 */

"use client";

import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition } from "@/components/motion-wrappers";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
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

/** Shape of a gift card returned by the API. */
interface GiftCard {
  id: string;
  code: string;
  initial_balance: number;
  current_balance: number;
  status: "active" | "depleted" | "expired" | "disabled";
  customer_email: string | null;
  created_at: string;
  expires_at: string | null;
}

/**
 * GiftCardsPage renders the gift card listing and issuance dialog.
 *
 * Retrieves the store ID from the StoreContext (provided by the parent layout)
 * and fetches all gift cards for that store. Provides a dialog form to issue
 * new gift cards with an initial balance and optional customer email.
 *
 * @returns The rendered gift cards management page.
 */
export default function GiftCardsPage() {
  const { store: contextStore } = useStore();
  const id = contextStore!.id;
  const { user, loading: authLoading } = useAuth();
  const [giftCards, setGiftCards] = useState<GiftCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* Create form state */
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formBalance, setFormBalance] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  /**
   * Fetch all gift cards for this store.
   * Called on mount and after a successful creation.
   */
  async function fetchGiftCards() {
    setLoading(true);
    const result = await api.get<{ items: GiftCard[] }>(
      `/api/v1/stores/${id}/gift-cards`
    );
    if (result.error) {
      setError(result.error.message);
    } else {
      setGiftCards(result.data?.items ?? []);
    }
    setLoading(false);
  }

  useEffect(() => {
    if (authLoading || !user) return;
    fetchGiftCards();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, user, authLoading]);

  /**
   * Handle the issue-gift-card form submission.
   *
   * @param e - The form submission event.
   */
  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);

    const result = await api.post<GiftCard>(
      `/api/v1/stores/${id}/gift-cards`,
      {
        initial_balance: parseFloat(formBalance),
        customer_email: formEmail || null,
      }
    );

    if (result.error) {
      setCreateError(result.error.message);
      setCreating(false);
      return;
    }

    setFormBalance("");
    setFormEmail("");
    setDialogOpen(false);
    setCreating(false);
    fetchGiftCards();
  }

  /**
   * Map gift card status to a Badge variant for visual distinction.
   *
   * @param status - The gift card status string.
   * @returns The appropriate Badge variant.
   */
  function statusVariant(
    status: GiftCard["status"]
  ): "default" | "secondary" | "outline" | "destructive" {
    switch (status) {
      case "active":
        return "default";
      case "depleted":
        return "secondary";
      case "expired":
        return "outline";
      case "disabled":
        return "destructive";
      default:
        return "outline";
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="text-muted-foreground">Loading gift cards...</p>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Page heading and issue button */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold font-heading">Gift Cards</h1>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button>Issue Gift Card</Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>Issue Gift Card</DialogTitle>
                <DialogDescription>
                  Create a new gift card with an initial balance. The unique
                  code will be generated automatically.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreate} className="space-y-4">
                {createError && (
                  <p className="text-sm text-destructive">{createError}</p>
                )}
                <div className="space-y-2">
                  <Label htmlFor="gc-balance">Initial Balance ($)</Label>
                  <Input
                    id="gc-balance"
                    type="number"
                    step="0.01"
                    min="1"
                    placeholder="50.00"
                    value={formBalance}
                    onChange={(e) => setFormBalance(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="gc-email">
                    Customer Email{" "}
                    <span className="text-muted-foreground font-normal">
                      (optional)
                    </span>
                  </Label>
                  <Input
                    id="gc-email"
                    type="email"
                    placeholder="customer@example.com"
                    value={formEmail}
                    onChange={(e) => setFormEmail(e.target.value)}
                  />
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
                    {creating ? "Issuing..." : "Issue Card"}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {error && (
          <Card className="border-destructive/50">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {giftCards.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="text-5xl opacity-20">&#127873;</div>
            <h2 className="text-xl font-semibold font-heading">No gift cards issued</h2>
            <p className="text-muted-foreground max-w-sm">
              Issue your first gift card to offer flexible payment options
              to your customers.
            </p>
            <Button onClick={() => setDialogOpen(true)}>
              Issue your first gift card
            </Button>
          </div>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Gift Cards</CardTitle>
              <CardDescription>
                {giftCards.length} card{giftCards.length !== 1 ? "s" : ""} issued
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Code</TableHead>
                    <TableHead>Balance</TableHead>
                    <TableHead>Initial</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Customer</TableHead>
                    <TableHead>Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {giftCards.map((card) => (
                    <TableRow key={card.id}>
                      <TableCell>
                        <code className="rounded bg-muted px-1.5 py-0.5 text-xs font-mono">
                          {card.code}
                        </code>
                      </TableCell>
                      <TableCell className="font-medium">
                        ${Number(card.current_balance).toFixed(2)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        ${Number(card.initial_balance).toFixed(2)}
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusVariant(card.status)}>
                          {card.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {card.customer_email || "--"}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(card.created_at).toLocaleDateString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </main>
    </PageTransition>
  );
}
