/**
 * Conversation history viewer -- browse, filter, and inspect chat sessions.
 *
 * Displays a table of conversations across all chatbots with filtering
 * by chatbot, pagination, and a detail panel that shows the full message
 * thread when a conversation is selected.
 *
 * **For Developers:**
 *   - `GET /api/v1/conversations` -- list conversations (paginated, optional chatbot_id filter).
 *   - `GET /api/v1/conversations/:id` -- get conversation detail with messages.
 *   - `POST /api/v1/conversations/:id/end` -- end an active conversation.
 *   - `GET /api/v1/chatbots` -- fetch chatbot list for the filter dropdown.
 *   - Layout uses a split view: conversation list on the left, message thread on the right.
 *
 * **For Project Managers:**
 *   - This page is the primary tool for reviewing customer interactions.
 *   - It surfaces satisfaction scores and message counts for quality monitoring.
 *
 * **For QA Engineers:**
 *   - Verify the chatbot filter narrows results correctly.
 *   - Verify selecting a conversation shows the message thread.
 *   - Verify "End Conversation" button changes status from active to ended.
 *   - Test empty state when no conversations exist.
 *   - Test pagination with many conversations.
 *
 * **For End Users:**
 *   - Review past customer conversations to understand what people are asking.
 *   - Filter by chatbot to focus on a specific assistant.
 *   - Click a conversation to view the full message thread.
 */

"use client";

import * as React from "react";
import {
  MessageSquare,
  Bot,
  User,
  XCircle,
  Star,
  ChevronLeft,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { Shell } from "@/components/shell";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { FadeIn, PageTransition } from "@/components/motion";
import { api } from "@/lib/api";

/** Shape of a conversation in the list view. */
interface Conversation {
  id: string;
  chatbot_id: string;
  visitor_id: string;
  visitor_name: string | null;
  started_at: string;
  ended_at: string | null;
  message_count: number;
  satisfaction_score: number | null;
  status: string;
}

/** Shape of a single message within a conversation. */
interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

/** Shape of the conversation detail response (includes messages). */
interface ConversationDetail extends Conversation {
  messages: Message[];
}

/** Paginated response envelope. */
interface PaginatedConversations {
  items: Conversation[];
  total: number;
  page: number;
  page_size: number;
}

/** Shape of a chatbot (used for the filter dropdown). */
interface ChatbotOption {
  id: string;
  name: string;
}

/** Paginated chatbots response. */
interface PaginatedChatbots {
  items: ChatbotOption[];
  total: number;
  page: number;
  page_size: number;
}

/** Number of conversations per page. */
const PAGE_SIZE = 15;

/**
 * Conversation history viewer page component.
 *
 * @returns The conversations page wrapped in the Shell layout.
 */
export default function ConversationsPage() {
  /* List state */
  const [conversations, setConversations] = React.useState<Conversation[]>([]);
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  /* Chatbot filter */
  const [chatbots, setChatbots] = React.useState<ChatbotOption[]>([]);
  const [selectedChatbot, setSelectedChatbot] = React.useState<string>("");

  /* Detail panel state */
  const [selectedConv, setSelectedConv] =
    React.useState<ConversationDetail | null>(null);
  const [detailLoading, setDetailLoading] = React.useState(false);
  const [ending, setEnding] = React.useState(false);

  /**
   * Fetch chatbot options and initial conversation list on mount.
   */
  React.useEffect(() => {
    fetchChatbots();
  }, []);

  /**
   * Re-fetch conversations whenever page or chatbot filter changes.
   */
  React.useEffect(() => {
    fetchConversations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, selectedChatbot]);

  /**
   * Fetch the chatbot list for the filter dropdown.
   */
  async function fetchChatbots(): Promise<void> {
    const { data } =
      await api.get<PaginatedChatbots>("/api/v1/chatbots?page_size=100");
    if (data) {
      setChatbots(data.items);
    }
  }

  /**
   * Fetch conversations with current page and chatbot filter.
   */
  async function fetchConversations(): Promise<void> {
    setLoading(true);
    setError(null);

    let path = `/api/v1/conversations?page=${page}&page_size=${PAGE_SIZE}`;
    if (selectedChatbot) {
      path += `&chatbot_id=${selectedChatbot}`;
    }

    const { data, error: apiError } =
      await api.get<PaginatedConversations>(path);
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setConversations(data.items);
      setTotal(data.total);
    }
    setLoading(false);
  }

  /**
   * Fetch full conversation detail with messages.
   *
   * @param convId - The conversation UUID to fetch.
   */
  async function fetchDetail(convId: string): Promise<void> {
    setDetailLoading(true);
    const { data, error: apiError } =
      await api.get<ConversationDetail>(`/api/v1/conversations/${convId}`);
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setSelectedConv(data);
    }
    setDetailLoading(false);
  }

  /**
   * End an active conversation.
   *
   * @param convId - The conversation UUID to end.
   */
  async function handleEnd(convId: string): Promise<void> {
    setEnding(true);
    const { error: apiError } = await api.post<Conversation>(
      `/api/v1/conversations/${convId}/end`
    );
    if (apiError) {
      setError(apiError.message);
    } else {
      await fetchDetail(convId);
      fetchConversations();
    }
    setEnding(false);
  }

  /** Total number of pages based on total count and page size. */
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  /**
   * Format an ISO date string for compact display.
   *
   * @param dateStr - ISO date string.
   * @returns Short formatted date/time string.
   */
  function formatDate(dateStr: string): string {
    const d = new Date(dateStr);
    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  /**
   * Format a time string from an ISO date.
   *
   * @param dateStr - ISO date string.
   * @returns Formatted time string.
   */
  function formatTime(dateStr: string): string {
    return new Date(dateStr).toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  /**
   * Get the chatbot name by its ID.
   *
   * @param chatbotId - The chatbot UUID.
   * @returns The chatbot name or a truncated ID.
   */
  function getChatbotName(chatbotId: string): string {
    const bot = chatbots.find((b) => b.id === chatbotId);
    return bot?.name || chatbotId.slice(0, 8);
  }

  return (
    <Shell>
      <PageTransition className="p-6 space-y-6">
        {/* -- Page Header -- */}
        <FadeIn direction="down">
          <div>
            <h2 className="font-heading text-2xl font-bold tracking-tight">
              Conversations
            </h2>
            <p className="text-muted-foreground mt-1">
              Review chat sessions and customer interactions.
            </p>
          </div>
        </FadeIn>

        {/* -- Filter Bar -- */}
        <FadeIn delay={0.1}>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">Filter by:</span>
            <select
              value={selectedChatbot}
              onChange={(e) => {
                setSelectedChatbot(e.target.value);
                setPage(1);
                setSelectedConv(null);
              }}
              className="rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">All Chatbots</option>
              {chatbots.map((bot) => (
                <option key={bot.id} value={bot.id}>
                  {bot.name}
                </option>
              ))}
            </select>
            <span className="text-sm text-muted-foreground ml-auto">
              {total} conversation{total !== 1 ? "s" : ""}
            </span>
          </div>
        </FadeIn>

        {/* -- Error Banner -- */}
        {error && (
          <FadeIn>
            <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          </FadeIn>
        )}

        {/* -- Main Content -- */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 min-h-[500px]">
          {/* -- Conversation List (left column) -- */}
          <div className="lg:col-span-2 space-y-2">
            {loading ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Card key={i} className="py-3">
                    <CardContent className="flex items-center gap-3">
                      <Skeleton className="size-8 rounded-full" />
                      <div className="flex-1 space-y-1.5">
                        <Skeleton className="h-3.5 w-28" />
                        <Skeleton className="h-3 w-40" />
                      </div>
                      <Skeleton className="h-5 w-14" />
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : conversations.length === 0 ? (
              <FadeIn>
                <Card>
                  <CardContent className="py-12 text-center">
                    <div className="mx-auto size-12 rounded-full bg-muted flex items-center justify-center mb-3">
                      <MessageSquare className="size-6 text-muted-foreground" />
                    </div>
                    <h3 className="font-heading font-semibold">
                      No conversations yet
                    </h3>
                    <p className="text-muted-foreground text-sm mt-1 max-w-sm mx-auto">
                      Conversations will appear here once visitors start
                      chatting with your chatbots.
                    </p>
                  </CardContent>
                </Card>
              </FadeIn>
            ) : (
              <>
                {conversations.map((conv) => (
                  <button
                    key={conv.id}
                    type="button"
                    onClick={() => fetchDetail(conv.id)}
                    className={`w-full text-left rounded-xl border p-4 transition-colors ${
                      selectedConv?.id === conv.id
                        ? "border-primary bg-primary/5 shadow-sm"
                        : "border-border bg-card hover:border-primary/30 hover:bg-card/80"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium truncate">
                            {conv.visitor_name || conv.visitor_id}
                          </span>
                          <Badge
                            variant={
                              conv.status === "active"
                                ? "success"
                                : "secondary"
                            }
                            className="text-[10px] px-1.5"
                          >
                            {conv.status}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5 truncate">
                          {getChatbotName(conv.chatbot_id)}
                        </p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-xs text-muted-foreground">
                          {formatDate(conv.started_at)}
                        </p>
                        <div className="flex items-center gap-1.5 mt-1 justify-end">
                          <MessageSquare className="size-3 text-muted-foreground" />
                          <span className="text-xs text-muted-foreground">
                            {conv.message_count}
                          </span>
                          {conv.satisfaction_score !== null && (
                            <>
                              <Star className="size-3 text-amber-500 ml-1" />
                              <span className="text-xs text-muted-foreground">
                                {conv.satisfaction_score.toFixed(1)}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </button>
                ))}

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-center gap-2 pt-3">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => p - 1)}
                    >
                      <ChevronLeft className="size-4" />
                    </Button>
                    <span className="text-sm text-muted-foreground">
                      {page} / {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      <ChevronRight className="size-4" />
                    </Button>
                  </div>
                )}
              </>
            )}
          </div>

          {/* -- Detail Panel (right column) -- */}
          <div className="lg:col-span-3">
            {detailLoading ? (
              <Card className="h-full">
                <CardHeader>
                  <Skeleton className="h-5 w-40" />
                  <Skeleton className="h-3 w-56 mt-2" />
                </CardHeader>
                <CardContent className="space-y-4">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div
                      key={i}
                      className={`flex ${i % 2 === 0 ? "" : "justify-end"}`}
                    >
                      <Skeleton className="h-12 w-3/4 rounded-xl" />
                    </div>
                  ))}
                </CardContent>
              </Card>
            ) : selectedConv ? (
              <FadeIn>
                <Card className="h-full flex flex-col">
                  {/* Detail Header */}
                  <CardHeader className="border-b">
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-base">
                          {selectedConv.visitor_name ||
                            selectedConv.visitor_id}
                        </CardTitle>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          Started {formatDate(selectedConv.started_at)}
                          {selectedConv.ended_at &&
                            ` -- Ended ${formatDate(selectedConv.ended_at)}`}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {selectedConv.satisfaction_score !== null && (
                          <Badge variant="outline" className="gap-1">
                            <Star className="size-3 text-amber-500" />
                            {selectedConv.satisfaction_score.toFixed(1)}
                          </Badge>
                        )}
                        <Badge
                          variant={
                            selectedConv.status === "active"
                              ? "success"
                              : "secondary"
                          }
                        >
                          {selectedConv.status}
                        </Badge>
                        {selectedConv.status === "active" && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleEnd(selectedConv.id)}
                            disabled={ending}
                          >
                            {ending ? (
                              <Loader2 className="size-3.5 animate-spin" />
                            ) : (
                              <XCircle className="size-3.5" />
                            )}
                            End
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardHeader>

                  {/* Message Thread */}
                  <CardContent className="flex-1 overflow-y-auto py-4 space-y-3 max-h-[500px]">
                    {selectedConv.messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex gap-2.5 ${
                          msg.role === "assistant" ? "" : "flex-row-reverse"
                        }`}
                      >
                        {/* Avatar */}
                        <div
                          className={`size-7 rounded-full flex items-center justify-center shrink-0 ${
                            msg.role === "assistant"
                              ? "bg-primary/10"
                              : "bg-secondary"
                          }`}
                        >
                          {msg.role === "assistant" ? (
                            <Bot className="size-3.5 text-primary" />
                          ) : (
                            <User className="size-3.5 text-muted-foreground" />
                          )}
                        </div>

                        {/* Message Bubble */}
                        <div
                          className={`max-w-[80%] rounded-2xl px-3.5 py-2.5 text-sm ${
                            msg.role === "assistant"
                              ? "bg-muted text-foreground rounded-tl-sm"
                              : "bg-primary text-primary-foreground rounded-tr-sm"
                          }`}
                        >
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                          <p
                            className={`text-[10px] mt-1 ${
                              msg.role === "assistant"
                                ? "text-muted-foreground"
                                : "text-primary-foreground/70"
                            }`}
                          >
                            {formatTime(msg.created_at)}
                          </p>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </FadeIn>
            ) : (
              /* -- No Selection State -- */
              <Card className="h-full flex items-center justify-center">
                <CardContent className="text-center py-16">
                  <div className="mx-auto size-12 rounded-full bg-muted flex items-center justify-center mb-3">
                    <MessageSquare className="size-6 text-muted-foreground" />
                  </div>
                  <h3 className="font-heading font-semibold text-muted-foreground">
                    Select a conversation
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Choose a conversation from the list to view the message
                    thread.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </PageTransition>
    </Shell>
  );
}
