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
 * NotificationsPage renders the user's notification feed with
 * read/unread management.
 *
 * @returns The rendered notifications page.
 */
export default function NotificationsPage() {
  const { user, loading: authLoading } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [markingAll, setMarkingAll] = useState(false);

  /**
   * Fetch all notifications for the current user.
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

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading notifications...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-lg font-semibold hover:underline">
            Dashboard
          </Link>
          <span className="text-muted-foreground">/</span>
          <h1 className="text-lg font-semibold">Notifications</h1>
          {unreadCount > 0 && (
            <Badge variant="secondary">{unreadCount} unread</Badge>
          )}
        </div>
        {unreadCount > 0 && (
          <Button
            variant="outline"
            onClick={handleMarkAllRead}
            disabled={markingAll}
          >
            {markingAll ? "Marking..." : "Mark all as read"}
          </Button>
        )}
      </header>

      <main className="mx-auto max-w-3xl p-6">
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
            <h2 className="text-xl font-semibold">No notifications</h2>
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
      </main>
    </div>
  );
}
