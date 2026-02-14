/**
 * Accounts page — manage connected social media accounts.
 *
 * Displays a list of all connected (and disconnected) social accounts,
 * with controls to connect new accounts and disconnect existing ones.
 * Each account card shows platform, name, connection status, and
 * connection date.
 *
 * **For Developers:**
 *   - Fetches from `GET /api/v1/accounts` on mount.
 *   - Connect uses `POST /api/v1/accounts` with platform and account_name.
 *   - Disconnect uses `DELETE /api/v1/accounts/{id}`.
 *   - The connect dialog uses a select for platform and text input for name.
 *   - Motion animations provide entrance effects for account cards.
 *
 * **For Project Managers:**
 *   - This is the gateway page for social media integration. Users must
 *     connect at least one account before they can create posts.
 *   - Shows plan-limit awareness (error message when limit is reached).
 *
 * **For QA Engineers:**
 *   - Verify loading skeletons show before data arrives.
 *   - Test connect flow for each platform (Instagram, Facebook, TikTok).
 *   - Test disconnect flow and verify the card updates to show disconnected.
 *   - Test with API server down — should show error state.
 *   - Verify empty state message for new users with no accounts.
 *
 * **For End Users:**
 *   - Connect your Instagram, Facebook, or TikTok account to start scheduling.
 *   - Disconnecting an account preserves your post history and analytics.
 */

"use client";

import * as React from "react";
import {
  Instagram,
  Facebook,
  Music2,
  Plus,
  Unplug,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Users,
} from "lucide-react";
import { Shell } from "@/components/shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { FadeIn, StaggerChildren, PageTransition } from "@/components/motion";
import { api } from "@/lib/api";
import { serviceConfig } from "@/service.config";

/** Shape of a social account returned by the API. */
interface SocialAccount {
  /** Unique identifier. */
  id: string;
  /** Social platform (instagram, facebook, tiktok). */
  platform: "instagram" | "facebook" | "tiktok";
  /** Display name of the account. */
  account_name: string;
  /** Platform-specific external ID. */
  account_id_external: string;
  /** Whether the account is currently connected. */
  is_connected: boolean;
  /** When the account was connected (ISO 8601). */
  connected_at: string | null;
  /** Record creation timestamp. */
  created_at: string;
}

/** Supported platforms for the connect dialog. */
const PLATFORMS = [
  { value: "instagram", label: "Instagram", icon: Instagram, color: "text-pink-500" },
  { value: "facebook", label: "Facebook", icon: Facebook, color: "text-blue-500" },
  { value: "tiktok", label: "TikTok", icon: Music2, color: "text-foreground" },
] as const;

/**
 * Get the icon component for a given platform.
 *
 * @param platform - The social platform identifier.
 * @returns The matching platform config object.
 */
function getPlatformConfig(platform: string) {
  return PLATFORMS.find((p) => p.value === platform) ?? PLATFORMS[0];
}

/**
 * Accounts page component.
 *
 * @returns The accounts management page wrapped in the Shell layout.
 */
export default function AccountsPage() {
  const [accounts, setAccounts] = React.useState<SocialAccount[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [connectOpen, setConnectOpen] = React.useState(false);
  const [selectedPlatform, setSelectedPlatform] = React.useState<string>("instagram");
  const [accountName, setAccountName] = React.useState("");
  const [connecting, setConnecting] = React.useState(false);
  const [disconnecting, setDisconnecting] = React.useState<string | null>(null);

  /**
   * Fetch all social accounts from the API.
   * Called on mount and after connect/disconnect operations.
   */
  const fetchAccounts = React.useCallback(async () => {
    const { data, error: apiError } = await api.get<SocialAccount[]>(
      "/api/v1/accounts"
    );
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setAccounts(data);
      setError(null);
    }
    setLoading(false);
  }, []);

  React.useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  /**
   * Connect a new social account via the API.
   * Called when the user submits the connect dialog form.
   */
  async function handleConnect() {
    if (!accountName.trim()) return;
    setConnecting(true);

    const { error: apiError } = await api.post<SocialAccount>(
      "/api/v1/accounts",
      {
        platform: selectedPlatform,
        account_name: accountName.trim(),
      }
    );

    if (apiError) {
      setError(apiError.message);
    } else {
      setAccountName("");
      setSelectedPlatform("instagram");
      setConnectOpen(false);
      await fetchAccounts();
    }
    setConnecting(false);
  }

  /**
   * Disconnect a social account via the API.
   *
   * @param accountId - The UUID of the account to disconnect.
   */
  async function handleDisconnect(accountId: string) {
    setDisconnecting(accountId);

    const { error: apiError } = await api.del<SocialAccount>(
      `/api/v1/accounts/${accountId}`
    );

    if (apiError) {
      setError(apiError.message);
    } else {
      await fetchAccounts();
    }
    setDisconnecting(null);
  }

  /** Count of currently connected accounts. */
  const connectedCount = accounts.filter((a) => a.is_connected).length;

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Page Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                Social Accounts
              </h2>
              <p className="text-muted-foreground mt-1">
                Connect and manage your social media profiles
              </p>
            </div>
            <Button onClick={() => setConnectOpen(true)}>
              <Plus className="size-4" />
              Connect Account
            </Button>
          </div>
        </FadeIn>

        {/* ── Summary Card ── */}
        <FadeIn delay={0.1}>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="flex items-center justify-center size-12 rounded-xl bg-primary/10">
                  <Users className="size-6 text-primary" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Connected Accounts</p>
                  <p className="text-2xl font-bold font-heading">
                    {loading ? "..." : connectedCount}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </FadeIn>

        {/* ── Error State ── */}
        {error && (
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-6">
                <p className="text-destructive text-sm">{error}</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => {
                    setError(null);
                    fetchAccounts();
                  }}
                >
                  <RefreshCw className="size-3.5" />
                  Retry
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* ── Loading State ── */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <Skeleton className="size-10 rounded-full" />
                    <div className="space-y-2">
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-3 w-20" />
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-24" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : accounts.length === 0 ? (
          /* ── Empty State ── */
          <FadeIn delay={0.2}>
            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <div className="flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
                    <Unplug className="size-7 text-muted-foreground" />
                  </div>
                  <h3 className="font-heading text-lg font-semibold mb-1">
                    No accounts connected
                  </h3>
                  <p className="text-muted-foreground text-sm max-w-sm mb-6">
                    Connect your Instagram, Facebook, or TikTok account to start
                    scheduling posts with {serviceConfig.name}.
                  </p>
                  <Button onClick={() => setConnectOpen(true)}>
                    <Plus className="size-4" />
                    Connect Your First Account
                  </Button>
                </div>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          /* ── Account Cards ── */
          <StaggerChildren
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            staggerDelay={0.08}
          >
            {accounts.map((account) => {
              const platform = getPlatformConfig(account.platform);
              const PlatformIcon = platform.icon;

              return (
                <Card key={account.id} className="relative overflow-hidden">
                  {/* Top accent border based on connection status */}
                  <div
                    className={`absolute top-0 left-0 right-0 h-1 ${
                      account.is_connected
                        ? "bg-emerald-500"
                        : "bg-muted-foreground/20"
                    }`}
                  />
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div
                          className={`flex items-center justify-center size-10 rounded-full bg-muted ${platform.color}`}
                        >
                          <PlatformIcon className="size-5" />
                        </div>
                        <div>
                          <CardTitle className="text-base">
                            {account.account_name}
                          </CardTitle>
                          <p className="text-xs text-muted-foreground capitalize">
                            {account.platform}
                          </p>
                        </div>
                      </div>
                      <Badge
                        variant={account.is_connected ? "success" : "secondary"}
                      >
                        {account.is_connected ? (
                          <>
                            <CheckCircle2 className="size-3 mr-1" />
                            Connected
                          </>
                        ) : (
                          <>
                            <XCircle className="size-3 mr-1" />
                            Disconnected
                          </>
                        )}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <p className="text-xs text-muted-foreground">
                        {account.connected_at
                          ? `Connected ${new Date(account.connected_at).toLocaleDateString()}`
                          : `Added ${new Date(account.created_at).toLocaleDateString()}`}
                      </p>
                      {account.is_connected && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive hover:bg-destructive/10"
                          disabled={disconnecting === account.id}
                          onClick={() => handleDisconnect(account.id)}
                        >
                          <Unplug className="size-3.5" />
                          {disconnecting === account.id
                            ? "Disconnecting..."
                            : "Disconnect"}
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </StaggerChildren>
        )}

        {/* ── Connect Account Dialog ── */}
        <Dialog open={connectOpen} onOpenChange={setConnectOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Connect Social Account</DialogTitle>
              <DialogDescription>
                Choose a platform and enter your account name to connect.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              {/* Platform selector */}
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Platform
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {PLATFORMS.map((p) => {
                    const Icon = p.icon;
                    const isSelected = selectedPlatform === p.value;
                    return (
                      <button
                        key={p.value}
                        type="button"
                        onClick={() => setSelectedPlatform(p.value)}
                        className={`flex flex-col items-center gap-1.5 p-3 rounded-lg border-2 transition-all duration-150 ${
                          isSelected
                            ? "border-primary bg-primary/5"
                            : "border-transparent bg-muted hover:bg-muted/80"
                        }`}
                      >
                        <Icon
                          className={`size-5 ${isSelected ? "text-primary" : p.color}`}
                        />
                        <span className="text-xs font-medium">{p.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Account name input */}
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Account Name
                </label>
                <Input
                  placeholder="@yourbrand"
                  value={accountName}
                  onChange={(e) => setAccountName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleConnect();
                  }}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  The display name for this social profile
                </p>
              </div>
            </div>

            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <Button
                onClick={handleConnect}
                disabled={connecting || !accountName.trim()}
              >
                {connecting ? "Connecting..." : "Connect Account"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
