/**
 * Posts page — manage, create, and schedule social media posts.
 *
 * Displays a filterable, paginated list of all posts with their status,
 * platform, content preview, and scheduling information. Includes a
 * create dialog for drafting new posts and inline scheduling controls.
 *
 * **For Developers:**
 *   - Fetches from `GET /api/v1/posts` with page, per_page, status, platform params.
 *   - Create uses `POST /api/v1/posts` with account_id, content, platform, media_urls, hashtags.
 *   - Delete uses `DELETE /api/v1/posts/{id}`.
 *   - Schedule uses `POST /api/v1/posts/{id}/schedule` with scheduled_for.
 *   - Accounts are fetched from `GET /api/v1/accounts` for the create dialog's target selector.
 *   - Motion animations provide entrance and stagger effects.
 *
 * **For Project Managers:**
 *   - This is the primary content management page. Users spend most time here
 *     creating, editing, and reviewing their social media content.
 *   - Status badges make it easy to see the post lifecycle at a glance.
 *
 * **For QA Engineers:**
 *   - Verify loading skeletons display during fetch.
 *   - Test create flow with all required fields.
 *   - Test status and platform filter dropdowns.
 *   - Test pagination controls.
 *   - Test delete flow with confirmation.
 *   - Test scheduling a draft post (status should change to "scheduled").
 *   - Verify error states render correctly.
 *
 * **For End Users:**
 *   - Create new posts with captions, hashtags, and media.
 *   - Schedule posts for optimal timing or save as drafts.
 *   - Filter by status or platform to find specific posts.
 *   - Delete drafts you no longer need.
 */

"use client";

import * as React from "react";
import {
  Plus,
  Trash2,
  Calendar,
  Clock,
  Instagram,
  Facebook,
  Music2,
  FileText,
  CheckCircle2,
  AlertCircle,
  Send,
  ChevronLeft,
  ChevronRight,
  Filter,
  RefreshCw,
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
import { FadeIn, StaggerChildren, PageTransition, AnimatedCounter } from "@/components/motion";
import { api } from "@/lib/api";

/** Shape of a social account for the target selector. */
interface SocialAccount {
  id: string;
  platform: string;
  account_name: string;
  is_connected: boolean;
}

/** Shape of a post returned by the API. */
interface Post {
  id: string;
  account_id: string;
  content: string;
  media_urls: string[];
  hashtags: string[];
  platform: string;
  status: "draft" | "scheduled" | "posted" | "failed";
  scheduled_for: string | null;
  posted_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

/** Paginated post list from the API. */
interface PostListResponse {
  items: Post[];
  total: number;
  page: number;
  per_page: number;
}

/** Status filter options with display labels and icons. */
const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "draft", label: "Draft" },
  { value: "scheduled", label: "Scheduled" },
  { value: "posted", label: "Posted" },
  { value: "failed", label: "Failed" },
] as const;

/** Platform filter options. */
const PLATFORM_OPTIONS = [
  { value: "", label: "All Platforms" },
  { value: "instagram", label: "Instagram" },
  { value: "facebook", label: "Facebook" },
  { value: "tiktok", label: "TikTok" },
] as const;

/**
 * Map post status to a badge variant and icon.
 *
 * @param status - The post lifecycle status.
 * @returns Object with badge variant and icon component.
 */
function getStatusDisplay(status: Post["status"]) {
  switch (status) {
    case "draft":
      return { variant: "secondary" as const, icon: FileText, label: "Draft" };
    case "scheduled":
      return { variant: "default" as const, icon: Clock, label: "Scheduled" };
    case "posted":
      return { variant: "success" as const, icon: CheckCircle2, label: "Posted" };
    case "failed":
      return { variant: "destructive" as const, icon: AlertCircle, label: "Failed" };
  }
}

/**
 * Get the icon component for a given platform.
 *
 * @param platform - The social platform identifier.
 * @returns The Lucide icon component for the platform.
 */
function getPlatformIcon(platform: string) {
  switch (platform) {
    case "instagram":
      return Instagram;
    case "facebook":
      return Facebook;
    case "tiktok":
      return Music2;
    default:
      return Send;
  }
}

/**
 * Posts page component.
 *
 * @returns The post management page wrapped in the Shell layout.
 */
export default function PostsPage() {
  /* ── State ── */
  const [posts, setPosts] = React.useState<Post[]>([]);
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [statusFilter, setStatusFilter] = React.useState("");
  const [platformFilter, setPlatformFilter] = React.useState("");
  const perPage = 10;

  /* Create dialog state */
  const [createOpen, setCreateOpen] = React.useState(false);
  const [accounts, setAccounts] = React.useState<SocialAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = React.useState("");
  const [content, setContent] = React.useState("");
  const [hashtags, setHashtags] = React.useState("");
  const [mediaUrl, setMediaUrl] = React.useState("");
  const [creating, setCreating] = React.useState(false);

  /* Schedule dialog state */
  const [scheduleOpen, setScheduleOpen] = React.useState(false);
  const [schedulePostId, setSchedulePostId] = React.useState<string | null>(null);
  const [scheduleTime, setScheduleTime] = React.useState("");
  const [scheduling, setScheduling] = React.useState(false);

  /**
   * Fetch posts from the API with current filters and pagination.
   */
  const fetchPosts = React.useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams({
      page: String(page),
      per_page: String(perPage),
    });
    if (statusFilter) params.set("status", statusFilter);
    if (platformFilter) params.set("platform", platformFilter);

    const { data, error: apiError } = await api.get<PostListResponse>(
      `/api/v1/posts?${params}`
    );
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setPosts(data.items);
      setTotal(data.total);
      setError(null);
    }
    setLoading(false);
  }, [page, statusFilter, platformFilter]);

  React.useEffect(() => {
    fetchPosts();
  }, [fetchPosts]);

  /**
   * Fetch connected accounts for the create dialog target selector.
   */
  async function fetchAccounts() {
    const { data } = await api.get<SocialAccount[]>("/api/v1/accounts");
    if (data) {
      const connected = data.filter((a) => a.is_connected);
      setAccounts(connected);
      if (connected.length > 0 && !selectedAccountId) {
        setSelectedAccountId(connected[0].id);
      }
    }
  }

  /**
   * Open the create dialog and load accounts.
   */
  function openCreateDialog() {
    fetchAccounts();
    setCreateOpen(true);
  }

  /**
   * Create a new post via the API.
   */
  async function handleCreate() {
    if (!content.trim() || !selectedAccountId) return;
    setCreating(true);

    const selectedAccount = accounts.find((a) => a.id === selectedAccountId);
    const platform = selectedAccount?.platform ?? "instagram";

    const hashtagList = hashtags
      .split(/[\s,#]+/)
      .map((t) => t.trim())
      .filter(Boolean);

    const mediaUrls = mediaUrl.trim() ? [mediaUrl.trim()] : [];

    const { error: apiError } = await api.post<Post>("/api/v1/posts", {
      account_id: selectedAccountId,
      content: content.trim(),
      platform,
      hashtags: hashtagList,
      media_urls: mediaUrls,
    });

    if (apiError) {
      setError(apiError.message);
    } else {
      setContent("");
      setHashtags("");
      setMediaUrl("");
      setCreateOpen(false);
      await fetchPosts();
    }
    setCreating(false);
  }

  /**
   * Delete a post via the API.
   *
   * @param postId - UUID of the post to delete.
   */
  async function handleDelete(postId: string) {
    const { error: apiError } = await api.del(`/api/v1/posts/${postId}`);
    if (apiError) {
      setError(apiError.message);
    } else {
      await fetchPosts();
    }
  }

  /**
   * Open the schedule dialog for a specific post.
   *
   * @param postId - UUID of the post to schedule.
   */
  function openScheduleDialog(postId: string) {
    setSchedulePostId(postId);
    setScheduleTime("");
    setScheduleOpen(true);
  }

  /**
   * Schedule a post via the API.
   */
  async function handleSchedule() {
    if (!schedulePostId || !scheduleTime) return;
    setScheduling(true);

    const { error: apiError } = await api.post<Post>(
      `/api/v1/posts/${schedulePostId}/schedule`,
      { scheduled_for: new Date(scheduleTime).toISOString() }
    );

    if (apiError) {
      setError(apiError.message);
    } else {
      setScheduleOpen(false);
      setSchedulePostId(null);
      await fetchPosts();
    }
    setScheduling(false);
  }

  /** Total number of pages based on total items and per_page. */
  const totalPages = Math.max(1, Math.ceil(total / perPage));

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Page Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                Posts
              </h2>
              <p className="text-muted-foreground mt-1">
                Create, schedule, and manage your social media content
              </p>
            </div>
            <Button onClick={openCreateDialog}>
              <Plus className="size-4" />
              New Post
            </Button>
          </div>
        </FadeIn>

        {/* ── Stats Row ── */}
        <FadeIn delay={0.1}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                  Total Posts
                </p>
                <AnimatedCounter
                  value={total}
                  className="text-2xl font-bold font-heading block mt-1"
                />
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                  Drafts
                </p>
                <AnimatedCounter
                  value={posts.filter((p) => p.status === "draft").length}
                  className="text-2xl font-bold font-heading block mt-1"
                />
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                  Scheduled
                </p>
                <AnimatedCounter
                  value={posts.filter((p) => p.status === "scheduled").length}
                  className="text-2xl font-bold font-heading block mt-1"
                />
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                  Published
                </p>
                <AnimatedCounter
                  value={posts.filter((p) => p.status === "posted").length}
                  className="text-2xl font-bold font-heading block mt-1"
                />
              </CardContent>
            </Card>
          </div>
        </FadeIn>

        {/* ── Filters ── */}
        <FadeIn delay={0.15}>
          <div className="flex flex-wrap items-center gap-3">
            <Filter className="size-4 text-muted-foreground" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="h-9 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <select
              value={platformFilter}
              onChange={(e) => {
                setPlatformFilter(e.target.value);
                setPage(1);
              }}
              className="h-9 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {PLATFORM_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
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
                    fetchPosts();
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
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="pt-6">
                  <div className="flex items-start gap-4">
                    <Skeleton className="size-10 rounded-lg shrink-0" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-4 w-3/4" />
                      <Skeleton className="h-3 w-1/2" />
                    </div>
                    <Skeleton className="h-6 w-20 rounded-full" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : posts.length === 0 ? (
          /* ── Empty State ── */
          <FadeIn delay={0.2}>
            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <div className="flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
                    <FileText className="size-7 text-muted-foreground" />
                  </div>
                  <h3 className="font-heading text-lg font-semibold mb-1">
                    No posts yet
                  </h3>
                  <p className="text-muted-foreground text-sm max-w-sm mb-6">
                    Create your first post to start building your social media presence.
                  </p>
                  <Button onClick={openCreateDialog}>
                    <Plus className="size-4" />
                    Create Your First Post
                  </Button>
                </div>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          /* ── Post List ── */
          <StaggerChildren className="space-y-3" staggerDelay={0.06}>
            {posts.map((post) => {
              const statusDisplay = getStatusDisplay(post.status);
              const StatusIcon = statusDisplay.icon;
              const PlatformIcon = getPlatformIcon(post.platform);

              return (
                <Card key={post.id} className="hover:shadow-md transition-shadow duration-200">
                  <CardContent className="pt-6">
                    <div className="flex items-start gap-4">
                      {/* Platform icon */}
                      <div className="flex items-center justify-center size-10 rounded-lg bg-muted shrink-0">
                        <PlatformIcon className="size-5 text-muted-foreground" />
                      </div>

                      {/* Content preview */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm line-clamp-2">{post.content}</p>
                        <div className="flex flex-wrap items-center gap-2 mt-2">
                          {post.hashtags.slice(0, 3).map((tag) => (
                            <span
                              key={tag}
                              className="text-xs text-primary font-medium"
                            >
                              #{tag}
                            </span>
                          ))}
                          {post.hashtags.length > 3 && (
                            <span className="text-xs text-muted-foreground">
                              +{post.hashtags.length - 3} more
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                          <span className="capitalize">{post.platform}</span>
                          <span>
                            Created {new Date(post.created_at).toLocaleDateString()}
                          </span>
                          {post.scheduled_for && (
                            <span className="flex items-center gap-1">
                              <Clock className="size-3" />
                              {new Date(post.scheduled_for).toLocaleString()}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Status and actions */}
                      <div className="flex items-center gap-2 shrink-0">
                        <Badge variant={statusDisplay.variant}>
                          <StatusIcon className="size-3 mr-1" />
                          {statusDisplay.label}
                        </Badge>
                        {post.status === "draft" && (
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Schedule"
                            onClick={() => openScheduleDialog(post.id)}
                          >
                            <Calendar className="size-4" />
                          </Button>
                        )}
                        {(post.status === "draft" || post.status === "scheduled") && (
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Delete"
                            className="text-destructive hover:text-destructive hover:bg-destructive/10"
                            onClick={() => handleDelete(post.id)}
                          >
                            <Trash2 className="size-4" />
                          </Button>
                        )}
                      </div>
                    </div>

                    {/* Error message for failed posts */}
                    {post.error_message && (
                      <div className="mt-3 p-2 rounded-md bg-destructive/10 text-destructive text-xs">
                        {post.error_message}
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </StaggerChildren>
        )}

        {/* ── Pagination ── */}
        {total > perPage && (
          <FadeIn delay={0.3}>
            <div className="flex items-center justify-between pt-2">
              <p className="text-sm text-muted-foreground">
                Showing {(page - 1) * perPage + 1}–
                {Math.min(page * perPage, total)} of {total} posts
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  <ChevronLeft className="size-4" />
                  Previous
                </Button>
                <span className="text-sm text-muted-foreground px-2">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                  <ChevronRight className="size-4" />
                </Button>
              </div>
            </div>
          </FadeIn>
        )}

        {/* ── Create Post Dialog ── */}
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Create New Post</DialogTitle>
              <DialogDescription>
                Write your content and select a target account.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              {/* Target account */}
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Target Account
                </label>
                {accounts.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No connected accounts. Connect one first in the Accounts page.
                  </p>
                ) : (
                  <select
                    value={selectedAccountId}
                    onChange={(e) => setSelectedAccountId(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {accounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.account_name} ({a.platform})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Content */}
              <div>
                <label className="text-sm font-medium mb-2 block">Content</label>
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Write your post caption..."
                  rows={4}
                  maxLength={5000}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                />
                <p className="text-xs text-muted-foreground mt-1 text-right">
                  {content.length}/5000
                </p>
              </div>

              {/* Hashtags */}
              <div>
                <label className="text-sm font-medium mb-2 block">Hashtags</label>
                <Input
                  value={hashtags}
                  onChange={(e) => setHashtags(e.target.value)}
                  placeholder="fashion streetwear newdrops"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Space or comma-separated, without # prefix
                </p>
              </div>

              {/* Media URL */}
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Media URL (optional)
                </label>
                <Input
                  value={mediaUrl}
                  onChange={(e) => setMediaUrl(e.target.value)}
                  placeholder="https://cdn.example.com/image.jpg"
                />
              </div>
            </div>

            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <Button
                onClick={handleCreate}
                disabled={creating || !content.trim() || !selectedAccountId}
              >
                {creating ? "Creating..." : "Create Draft"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── Schedule Dialog ── */}
        <Dialog open={scheduleOpen} onOpenChange={setScheduleOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Schedule Post</DialogTitle>
              <DialogDescription>
                Choose a date and time to publish this post.
              </DialogDescription>
            </DialogHeader>

            <div className="py-4">
              <label className="text-sm font-medium mb-2 block">
                Publish Date & Time
              </label>
              <Input
                type="datetime-local"
                value={scheduleTime}
                onChange={(e) => setScheduleTime(e.target.value)}
                min={new Date().toISOString().slice(0, 16)}
              />
            </div>

            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <Button
                onClick={handleSchedule}
                disabled={scheduling || !scheduleTime}
              >
                <Calendar className="size-4" />
                {scheduling ? "Scheduling..." : "Schedule"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
