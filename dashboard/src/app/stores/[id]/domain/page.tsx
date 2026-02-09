/**
 * Domain Settings page.
 *
 * Manages the custom domain configuration for a store. Shows the current
 * domain (if set), allows setting a new domain, verifying DNS, and
 * removing the custom domain.
 *
 * **For End Users:**
 *   Connect your own domain to your storefront. Enter your domain, update
 *   your DNS records as instructed, then verify the connection. You can
 *   also remove a custom domain to revert to the default subdomain.
 *
 * **For Developers:**
 *   - Fetches domain info via `GET /api/v1/stores/{store_id}/domain`.
 *   - Sets a domain via `POST /api/v1/stores/{store_id}/domain`.
 *   - Removes a domain via `DELETE /api/v1/stores/{store_id}/domain`.
 *   - Verifies DNS via `POST /api/v1/stores/{store_id}/domain/verify`.
 *   - Uses `useStore()` context for store ID (provided by the layout).
 *   - Wrapped in `PageTransition` for consistent page-level animations.
 *
 * **For QA Engineers:**
 *   - Verify the page loads with "No custom domain" when none is set.
 *   - Verify that setting a domain transitions to the "pending" state.
 *   - Verify that the verify action updates the status to "verified".
 *   - Verify that removing a domain clears the display.
 *   - Verify the remove confirmation dialog works correctly.
 *
 * **For Project Managers:**
 *   This page corresponds to Feature 22 (Domains) in the backlog.
 *   Custom domains enhance brand presence for storefronts.
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
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";

/** Shape of the domain configuration returned by the API. */
interface DomainConfig {
  domain: string | null;
  status: "none" | "pending" | "verified" | "failed";
  dns_record_type: string | null;
  dns_record_value: string | null;
  verified_at: string | null;
}

/**
 * DomainSettingsPage renders the custom domain configuration interface.
 *
 * Retrieves the store ID from the StoreContext (provided by the parent layout)
 * and fetches the current domain configuration. Provides forms to set, verify,
 * and remove custom domains.
 *
 * @returns The rendered domain settings page.
 */
export default function DomainSettingsPage() {
  const { store: contextStore } = useStore();
  const id = contextStore!.id;
  const { user, loading: authLoading } = useAuth();
  const [domainConfig, setDomainConfig] = useState<DomainConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* Set domain form state */
  const [formDomain, setFormDomain] = useState("");
  const [setting, setSetting] = useState(false);
  const [domainError, setDomainError] = useState<string | null>(null);

  /* Verify state */
  const [verifying, setVerifying] = useState(false);

  /* Remove state */
  const [removeDialogOpen, setRemoveDialogOpen] = useState(false);
  const [removing, setRemoving] = useState(false);

  /**
   * Fetch the current domain configuration.
   */
  async function fetchDomain() {
    setLoading(true);
    const result = await api.get<DomainConfig>(
      `/api/v1/stores/${id}/domain`
    );
    if (result.error) {
      setError(result.error.message);
    } else {
      setDomainConfig(result.data ?? null);
    }
    setLoading(false);
  }

  useEffect(() => {
    if (authLoading || !user) return;
    fetchDomain();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, user, authLoading]);

  /**
   * Handle setting a custom domain.
   *
   * @param e - The form submission event.
   */
  async function handleSetDomain(e: FormEvent) {
    e.preventDefault();
    setSetting(true);
    setDomainError(null);

    const result = await api.post<DomainConfig>(
      `/api/v1/stores/${id}/domain`,
      { domain: formDomain }
    );

    if (result.error) {
      setDomainError(result.error.message);
      setSetting(false);
      return;
    }

    setDomainConfig(result.data);
    setFormDomain("");
    setSetting(false);
  }

  /**
   * Trigger DNS verification for the configured domain.
   */
  async function handleVerify() {
    setVerifying(true);
    const result = await api.post<DomainConfig>(
      `/api/v1/stores/${id}/domain/verify`,
      {}
    );
    if (result.data) {
      setDomainConfig(result.data);
    }
    setVerifying(false);
  }

  /**
   * Remove the custom domain from this store.
   */
  async function handleRemove() {
    setRemoving(true);
    const result = await api.delete<DomainConfig>(
      `/api/v1/stores/${id}/domain`
    );
    if (!result.error) {
      setDomainConfig({
        domain: null,
        status: "none",
        dns_record_type: null,
        dns_record_value: null,
        verified_at: null,
      });
    }
    setRemoving(false);
    setRemoveDialogOpen(false);
  }

  /**
   * Map domain status to a Badge variant.
   *
   * @param status - The domain status string.
   * @returns The appropriate Badge variant.
   */
  function statusVariant(
    status: DomainConfig["status"]
  ): "default" | "secondary" | "outline" | "destructive" {
    switch (status) {
      case "verified":
        return "default";
      case "pending":
        return "secondary";
      case "failed":
        return "destructive";
      default:
        return "outline";
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="text-muted-foreground">Loading domain settings...</p>
      </div>
    );
  }

  const hasDomain = domainConfig?.domain != null;

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        <h1 className="text-2xl font-bold font-heading">Domain</h1>

        {error && (
          <Card className="border-destructive/50">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Current Domain Display */}
        <Card>
          <CardHeader>
            <CardTitle>Custom Domain</CardTitle>
            <CardDescription>
              {hasDomain
                ? "Your store is using a custom domain."
                : "No custom domain configured. Your store uses the default subdomain."}
            </CardDescription>
          </CardHeader>
          {hasDomain && domainConfig && (
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                <code className="rounded bg-muted px-2 py-1 text-sm font-mono">
                  {domainConfig.domain}
                </code>
                <Badge variant={statusVariant(domainConfig.status)}>
                  {domainConfig.status}
                </Badge>
              </div>

              {/* DNS Instructions for pending domains */}
              {domainConfig.status === "pending" &&
                domainConfig.dns_record_type && (
                  <div className="rounded-md border bg-muted/30 p-4 space-y-2">
                    <p className="text-sm font-medium">DNS Configuration Required</p>
                    <p className="text-sm text-muted-foreground">
                      Add the following DNS record to your domain provider:
                    </p>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <span className="text-muted-foreground">Type:</span>
                      <code className="font-mono">
                        {domainConfig.dns_record_type}
                      </code>
                      <span className="text-muted-foreground">Value:</span>
                      <code className="font-mono break-all">
                        {domainConfig.dns_record_value}
                      </code>
                    </div>
                  </div>
                )}

              {domainConfig.verified_at && (
                <p className="text-sm text-muted-foreground">
                  Verified on{" "}
                  {new Date(domainConfig.verified_at).toLocaleDateString()}
                </p>
              )}

              <Separator />

              <div className="flex gap-3">
                {domainConfig.status !== "verified" && (
                  <Button onClick={handleVerify} disabled={verifying}>
                    {verifying ? "Verifying..." : "Verify DNS"}
                  </Button>
                )}

                <Dialog
                  open={removeDialogOpen}
                  onOpenChange={setRemoveDialogOpen}
                >
                  <DialogTrigger asChild>
                    <Button variant="destructive">Remove Domain</Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>
                        Remove &quot;{domainConfig.domain}&quot;?
                      </DialogTitle>
                      <DialogDescription>
                        Your store will revert to the default subdomain.
                        This action can be undone by re-adding the domain.
                      </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                      <Button
                        variant="outline"
                        onClick={() => setRemoveDialogOpen(false)}
                      >
                        Cancel
                      </Button>
                      <Button
                        variant="destructive"
                        onClick={handleRemove}
                        disabled={removing}
                      >
                        {removing ? "Removing..." : "Remove"}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            </CardContent>
          )}
        </Card>

        {/* Set Domain Form */}
        {!hasDomain && (
          <Card>
            <CardHeader>
              <CardTitle>Connect a Domain</CardTitle>
              <CardDescription>
                Enter your custom domain to connect it to your storefront.
                You will need to update your DNS records afterwards.
              </CardDescription>
            </CardHeader>
            <form onSubmit={handleSetDomain}>
              <CardContent className="space-y-4">
                {domainError && (
                  <p className="text-sm text-destructive">{domainError}</p>
                )}
                <div className="space-y-2">
                  <Label htmlFor="custom-domain">Domain</Label>
                  <Input
                    id="custom-domain"
                    placeholder="shop.example.com"
                    value={formDomain}
                    onChange={(e) => setFormDomain(e.target.value)}
                    required
                  />
                </div>
              </CardContent>
              <CardFooter className="flex justify-end">
                <Button type="submit" disabled={setting}>
                  {setting ? "Connecting..." : "Connect Domain"}
                </Button>
              </CardFooter>
            </form>
          </Card>
        )}
      </main>
    </PageTransition>
  );
}
