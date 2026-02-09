/**
 * Notifications page.
 *
 * Displays a chronological list of notifications for the authenticated user
 * with read/unread visual states and a "mark as read" action.
 *
 * **For End Users:**
 *   View all your notifications in one place. Unread notifications are
 *   highlighted. Click "Mark as read" to dismiss individual notifications,
 *   or use "Mark all as read" for bulk dismissal.
 *
 * **For Developers:**
 *   - Fetches notifications via `GET /api/v1/notifications`.
 *   - Marks individual notifications read via
 *     `POST /api/v1/notifications/{id}/read` (PATCH would also work).
 *   - Marks all as read via `POST /api/v1/notifications/read-all`.
 *   - This page is NOT store-scoped; it lives at `/notifications`.
 *   - Uses `bg-dot-pattern` background for visual consistency with the overhaul.
 *   - Header uses backdrop blur and `font-heading` for titles.
 *   - Main content wrapped in `PageTransition` for entrance animation.
 *   - ThemeToggle is present in the header for dark/light mode switching.
 *   - Loading state uses Skeleton placeholders instead of text spinners.
 *
 * **For QA Engineers:**
 *   - Verify that unread notifications have a distinct visual style.
 *   - Verify that marking one notification as read updates it immediately.
 *   - Verify that "Mark all as read" updates all notifications.
 *   - Verify that the empty state displays when there are zero notifications.
 *
 * **For Project Managers:**
 *   This page corresponds to Feature 25 (Notifications) in the backlog.
 *   Notifications are user-scoped, not store-scoped.
 */

"use client";

import { useEffect, useState } from "react";
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
import { Skeleton } from "@/components/ui/skeleton";
import { PageTransition } from "@/components/motion-wrappers";
import { ThemeToggle } from "@/components/theme-toggle";

/** Shape of a notification returned by the API. */
interface Notification {
  id: string;
  title: string;
  message: string;
  type: "info" | "warning" | "error" | "success";
  is_read: boolean;
  created_at: string;
  link: string | null;
}

/**
 * Skeleton loading state for the notifications page.
 *
 * Renders placeholder shapes that approximate the notifications page layout
 * while data is being fetched.
 *
 * @returns Skeleton placeholders matching the notifications page structure.
 */
function NotificationsSkeleton() {
  return (
    <div className="min-h-screen bg-dot-pattern">
      <header className="flex items-center justify-between border-b bg-background/80 backdrop-blur-sm px-6 py-4">
        <div className="flex items-center gap-4">
          <Skeleton className="h-6 w-24" />
          <Skeleton className="h-6 w-4" />
          <Skeleton className="h-6 w-32" />
        </div>
        <Skeleton className="h-8 w-32 rounded-md" />
      </header>
      <main className="mx-auto max-w-3xl p-6">
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-2">
                    <Skeleton className="h-4 w-40" />
                    <Skeleton className="h-5 w-12 rounded-full" />
                  </div>
                  <Skeleton className="h-3 w-28" />
                </div>
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-full mb-1" />
                <Skeleton className="h-4 w-3/4 mb-3" />
                <div className="flex items-center gap-3">
                  <Skeleton className="h-8 w-24 rounded-md" />
                  <Skeleton className="h-8 w-24 rounded-md" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </main>
    </div>
  );
}

/**
 * NotificationsPage renders the user's notification feed with
 * read/unread management.
 *
 * Fetches notifications from the API, displays them in a list with
 * visual distinction for unread items, and provides mark-as-read actions.
 *
 * @returns The rendered notifications page with header and notification list.
 */
export default function NotificationsPage() {
  const { user, loading: authLoading } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [markingAll, setMarkingAll] = useState(false);

  /**
   * Fetch all notifications for the current user from the API.
   * Updates the notifications state or sets an error message on failure.
   */
  async function fetchNotifications() {
    setLoading(true);
    const result = await api.get<{ items: Notification[] }>("/api/v1/notifications");
    if (result.error) {
      setError(result.error.message);
    } else {
      setNotifications(result.data?.items ?? []);
    }
    setLoading(false);
  }

  useEffect(() => {
    if (authLoading || !user) return;
    fetchNotifications();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, authLoading]);

  /**
   * Mark a single notification as read.
   * Optimistically updates the local state on success.
   *
   * @param notifId - The ID of the notification to mark as read.
   */
  async function handleMarkRead(notifId: string) {
    const result = await api.post(`/api/v1/notifications/${notifId}/read`, {});
    if (!result.error) {
      setNotifications((prev) =>
        prev.map((n) => (n.id === notifId ? { ...n, is_read: true } : n))
      );
    }
  }

  /**
   * Mark all notifications as read in a single bulk operation.
   * Optimistically updates all items in local state on success.
   */
  async function handleMarkAllRead() {
    setMarkingAll(true);
    const result = await api.post("/api/v1/notifications/read-all", {});
    if (!result.error) {
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, is_read: true }))
      );
    }
    setMarkingAll(false);
  }

  /**
   * Map notification type to a Badge variant for visual categorisation.
   *
   * @param type - The notification type string.
   * @returns The appropriate Badge variant.
   */
  function typeVariant(
    type: Notification["type"]
  ): "default" | "secondary" | "outline" | "destructive" {
    switch (type) {
      case "success":
        return "default";
      case "info":
        return "secondary";
      case "warning":
        return "outline";
      case "error":
        return "destructive";
      default:
        return "secondary";
    }
  }

  /** Count of unread notifications. */
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  /* Show skeleton while data is loading. */
  if (authLoading || loading) {
    return <NotificationsSkeleton />;
  }

  return (
    <div className="min-h-screen bg-dot-pattern">
      <header className="flex items-center justify-between border-b bg-background/80 backdrop-blur-sm px-6 py-4">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-lg font-heading font-semibold hover:underline">
            Dashboard
          </Link>
          <span className="text-muted-foreground">/</span>
          <h1 className="text-lg font-heading font-semibold">Notifications</h1>
          {unreadCount > 0 && (
            <Badge variant="secondary">{unreadCount} unread</Badge>
          )}
        </div>
        <div className="flex items-center gap-4">
          <ThemeToggle />
          {unreadCount > 0 && (
            <Button
              variant="outline"
              onClick={handleMarkAllRead}
              disabled={markingAll}
            >
              {markingAll ? "Marking..." : "Mark all as read"}
            </Button>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-3xl p-6">
        <PageTransition>
          {error && (
            <Card className="mb-6 border-destructive/50">
              <CardContent className="pt-6">
                <p className="text-sm text-destructive">{error}</p>
              </CardContent>
            </Card>
          )}

          {notifications.length === 0 ? (
            <div className="flex flex-col items-center gap-4 py-16 text-center">
              <div className="text-5xl opacity-20">&#128276;</div>
              <h2 className="text-xl font-heading font-semibold">No notifications</h2>
              <p className="text-muted-foreground max-w-sm">
                You are all caught up. Notifications about orders, team activity,
                and system events will appear here.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {notifications.map((notif) => (
                <Card
                  key={notif.id}
                  className={
                    notif.is_read
                      ? "opacity-70"
                      : "border-l-4 border-l-primary shadow-sm"
                  }
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-sm font-medium">
                          {notif.title}
                        </CardTitle>
                        <Badge variant={typeVariant(notif.type)}>
                          {notif.type}
                        </Badge>
                      </div>
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {new Date(notif.created_at).toLocaleString()}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="mb-3">
                      {notif.message}
                    </CardDescription>
                    <div className="flex items-center gap-3">
                      {notif.link && (
                        <Link href={notif.link}>
                          <Button variant="outline" size="sm">
                            View Details
                          </Button>
                        </Link>
                      )}
                      {!notif.is_read && (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleMarkRead(notif.id)}
                        >
                          Mark as read
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </PageTransition>
      </main>
    </div>
  );
}
