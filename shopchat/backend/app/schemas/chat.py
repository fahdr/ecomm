"""
Pydantic schemas for chat-related request/response validation.

Defines the data structures for chatbots, knowledge base entries,
conversations, messages, and the public widget chat endpoint.

For Developers:
    All schemas use Pydantic v2 with strict validation. Use `model_config`
    with `from_attributes=True` for ORM-compatible response models.
    ChatRequest/ChatResponse are used by the public widget endpoint.

For QA Engineers:
    Test validation: invalid personality values should return 422,
    missing required fields should be rejected, and pagination
    should work correctly on list endpoints.

For Project Managers:
    These schemas define the API contract for all chat-related features.
    The widget schemas (ChatRequest, ChatResponse) define what external
    websites send/receive when using the embedded chat widget.

For End Users:
    These define the data format for creating chatbots, adding knowledge
    base entries, and interacting with the chat widget.
"""

import uuid
from datetime import datetime

from pydantic import AliasChoices, BaseModel, Field


# ── Chatbot Schemas ──────────────────────────────────────────────────


class ChatbotCreate(BaseModel):
    """
    Request schema for creating a new chatbot.

    Attributes:
        name: Human-readable chatbot name.
        personality: Chatbot personality style.
        welcome_message: Greeting shown when the widget opens.
        theme_config: Widget appearance settings (colors, position, size).
    """

    name: str = Field(..., min_length=1, max_length=255, description="Chatbot name")
    personality: str = Field(
        "friendly",
        description="Personality style: friendly, professional, casual, or helpful",
    )
    welcome_message: str = Field(
        "Hi there! How can I help you today?",
        max_length=1000,
        description="Welcome greeting shown to visitors",
    )
    theme_config: dict = Field(
        default_factory=lambda: {
            "primary_color": "#6366f1",
            "text_color": "#ffffff",
            "position": "bottom-right",
            "size": "medium",
        },
        description="Widget theme configuration (colors, position, size)",
    )


class ChatbotUpdate(BaseModel):
    """
    Request schema for updating an existing chatbot.

    All fields are optional — only provided fields are updated.

    Attributes:
        name: Updated chatbot name.
        personality: Updated personality style.
        welcome_message: Updated welcome greeting.
        theme_config: Updated widget appearance settings.
        is_active: Whether the chatbot is active.
    """

    name: str | None = Field(None, min_length=1, max_length=255)
    personality: str | None = None
    welcome_message: str | None = Field(None, max_length=1000)
    theme_config: dict | None = None
    is_active: bool | None = None


class ChatbotResponse(BaseModel):
    """
    Response schema for a chatbot.

    Attributes:
        id: Chatbot UUID.
        user_id: Owning user UUID.
        name: Chatbot name.
        personality: Personality style.
        welcome_message: Welcome greeting.
        theme_config: Widget theme configuration.
        is_active: Whether the chatbot is active.
        widget_key: Unique key for embedding the widget.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    personality: str
    welcome_message: str
    theme_config: dict
    is_active: bool
    widget_key: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Knowledge Base Schemas ───────────────────────────────────────────


class KnowledgeBaseCreate(BaseModel):
    """
    Request schema for creating a knowledge base entry.

    Attributes:
        chatbot_id: UUID of the chatbot this entry belongs to.
        source_type: Origin type of the content.
        title: Human-readable title.
        content: Full text content for AI context.
        metadata: Optional extra structured data.
    """

    chatbot_id: uuid.UUID = Field(..., description="Chatbot this entry belongs to")
    source_type: str = Field(
        "custom_text",
        description="Source type: product_catalog, policy_page, faq, custom_text, url",
    )
    title: str = Field(..., min_length=1, max_length=500, description="Entry title")
    content: str = Field(..., min_length=1, description="Full text content")
    metadata: dict | None = Field(None, description="Optional extra data")


class KnowledgeBaseUpdate(BaseModel):
    """
    Request schema for updating a knowledge base entry.

    Attributes:
        source_type: Updated source type.
        title: Updated title.
        content: Updated content.
        metadata: Updated metadata.
        is_active: Whether the entry is active.
    """

    source_type: str | None = None
    title: str | None = Field(None, min_length=1, max_length=500)
    content: str | None = Field(None, min_length=1)
    metadata: dict | None = None
    is_active: bool | None = None


class KnowledgeBaseResponse(BaseModel):
    """
    Response schema for a knowledge base entry.

    Attributes:
        id: Entry UUID.
        chatbot_id: Parent chatbot UUID.
        source_type: Content source type.
        title: Entry title.
        content: Full text content.
        metadata: Extra structured data.
        is_active: Whether the entry is active.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    chatbot_id: uuid.UUID
    source_type: str
    title: str
    content: str
    metadata: dict | None = Field(
        None, validation_alias=AliasChoices("extra_metadata", "metadata")
    )
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Conversation Schemas ─────────────────────────────────────────────


class ConversationResponse(BaseModel):
    """
    Response schema for a conversation.

    Attributes:
        id: Conversation UUID.
        chatbot_id: Parent chatbot UUID.
        visitor_id: Session-based visitor identifier.
        visitor_name: Optional visitor name.
        started_at: Conversation start time.
        ended_at: Conversation end time (None if active).
        message_count: Total messages in the conversation.
        satisfaction_score: Visitor satisfaction rating (1.0-5.0).
        status: Conversation lifecycle status.
    """

    id: uuid.UUID
    chatbot_id: uuid.UUID
    visitor_id: str
    visitor_name: str | None
    started_at: datetime
    ended_at: datetime | None
    message_count: int
    satisfaction_score: float | None
    status: str

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    """
    Response schema for a conversation with its messages.

    Attributes:
        id: Conversation UUID.
        chatbot_id: Parent chatbot UUID.
        visitor_id: Session-based visitor identifier.
        visitor_name: Optional visitor name.
        started_at: Conversation start time.
        ended_at: Conversation end time.
        message_count: Total messages.
        satisfaction_score: Satisfaction rating.
        status: Lifecycle status.
        messages: List of messages in the conversation.
    """

    id: uuid.UUID
    chatbot_id: uuid.UUID
    visitor_id: str
    visitor_name: str | None
    started_at: datetime
    ended_at: datetime | None
    message_count: int
    satisfaction_score: float | None
    status: str
    messages: list["MessageResponse"]

    model_config = {"from_attributes": True}


class SatisfactionRating(BaseModel):
    """
    Request schema for rating a conversation.

    Attributes:
        score: Satisfaction score from 1.0 to 5.0.
    """

    score: float = Field(..., ge=1.0, le=5.0, description="Satisfaction rating 1-5")


# ── Message Schemas ──────────────────────────────────────────────────


class MessageCreate(BaseModel):
    """
    Request schema for creating a message (internal use).

    Attributes:
        role: Message sender role ("user" or "assistant").
        content: Message text content.
        metadata: Optional extra data (product refs, links).
    """

    role: str = Field(..., description="Sender role: user or assistant")
    content: str = Field(..., min_length=1, description="Message content")
    metadata: dict | None = Field(None, description="Optional metadata")


class MessageResponse(BaseModel):
    """
    Response schema for a message.

    Attributes:
        id: Message UUID.
        conversation_id: Parent conversation UUID.
        role: Sender role.
        content: Message text content.
        metadata: Extra data (product refs, links).
        created_at: Message creation timestamp.
    """

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    metadata: dict | None = Field(
        None, validation_alias=AliasChoices("extra_metadata", "metadata")
    )
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Widget / Public Schemas ──────────────────────────────────────────


class WidgetConfig(BaseModel):
    """
    Public widget configuration returned for embed rendering.

    Attributes:
        chatbot_name: Display name of the chatbot.
        personality: Chatbot personality style.
        welcome_message: Greeting shown on widget open.
        theme_config: Visual theme settings.
        is_active: Whether the chatbot is currently accepting chats.
    """

    chatbot_name: str
    personality: str
    welcome_message: str
    theme_config: dict
    is_active: bool


class ChatRequest(BaseModel):
    """
    Public chat request from the embedded widget.

    Attributes:
        widget_key: The chatbot's unique widget key.
        visitor_id: Session/cookie-based visitor identifier.
        message: The visitor's message text.
        visitor_name: Optional visitor name.
    """

    widget_key: str = Field(..., description="Chatbot widget key")
    visitor_id: str = Field(..., min_length=1, description="Visitor session ID")
    message: str = Field(..., min_length=1, max_length=2000, description="Message text")
    visitor_name: str | None = Field(None, max_length=255)


class ProductSuggestion(BaseModel):
    """
    A product suggestion included in the AI response.

    Attributes:
        name: Product name.
        price: Product price string.
        url: Link to the product page.
    """

    name: str
    price: str
    url: str


class ChatResponse(BaseModel):
    """
    Public chat response from the AI assistant.

    Attributes:
        conversation_id: UUID of the conversation.
        message: The AI assistant's response text.
        product_suggestions: List of relevant product suggestions.
    """

    conversation_id: uuid.UUID
    message: str
    product_suggestions: list[ProductSuggestion] = []


# ── Paginated List ───────────────────────────────────────────────────


class PaginatedResponse(BaseModel):
    """
    Generic paginated list response.

    Attributes:
        items: List of items for the current page.
        total: Total number of items across all pages.
        page: Current page number (1-based).
        page_size: Number of items per page.
    """

    items: list
    total: int
    page: int
    page_size: int


# ── Analytics Schemas ────────────────────────────────────────────────


class AnalyticsOverview(BaseModel):
    """
    Overview analytics for the user's chatbots.

    Attributes:
        total_conversations: Total conversations across all chatbots.
        total_messages: Total messages across all chatbots.
        avg_satisfaction: Average satisfaction score (None if no ratings).
        active_chatbots: Number of active chatbots.
        conversations_today: Conversations started today.
        top_chatbot_name: Name of the chatbot with most conversations.
    """

    total_conversations: int
    total_messages: int
    avg_satisfaction: float | None
    active_chatbots: int
    conversations_today: int
    top_chatbot_name: str | None


class ChatbotAnalytics(BaseModel):
    """
    Analytics for a single chatbot.

    Attributes:
        chatbot_id: Chatbot UUID.
        chatbot_name: Chatbot name.
        total_conversations: Total conversations for this chatbot.
        total_messages: Total messages.
        avg_satisfaction: Average satisfaction score.
        avg_messages_per_conversation: Average messages per conversation.
    """

    chatbot_id: uuid.UUID
    chatbot_name: str
    total_conversations: int
    total_messages: int
    avg_satisfaction: float | None
    avg_messages_per_conversation: float


class AnalyticsSummary(BaseModel):
    """
    Enhanced analytics summary with session-level metrics.

    Attributes:
        total_sessions: Total chat sessions in the period.
        avg_satisfaction: Average satisfaction score.
        resolution_rate: Percentage of sessions marked as resolved.
        top_topics: Most common conversation topics.
        avg_response_time_ms: Average response time across all sessions.
    """

    total_sessions: int
    avg_satisfaction: float | None
    resolution_rate: float
    top_topics: list[dict]
    avg_response_time_ms: float


# ── Store Connection Schemas ────────────────────────────────────────


class StoreConnectionCreate(BaseModel):
    """
    Request schema for creating a store connection.

    Attributes:
        platform: Store platform (shopify, woocommerce, platform).
        store_url: Base URL of the store.
        api_key: API key / access token for the store.
        api_secret: Optional API secret (platform-dependent).
    """

    platform: str = Field(
        ..., min_length=1, max_length=50, description="Store platform"
    )
    store_url: str = Field(
        ..., min_length=1, max_length=500, description="Store base URL"
    )
    api_key: str = Field(
        ..., min_length=1, max_length=1000, description="API key"
    )
    api_secret: str | None = Field(
        None, max_length=1000, description="API secret"
    )


class StoreConnectionUpdate(BaseModel):
    """
    Request schema for updating a store connection.

    All fields are optional.

    Attributes:
        platform: Updated platform.
        store_url: Updated store URL.
        api_key: Updated API key.
        api_secret: Updated API secret.
        is_active: Whether the connection is active.
    """

    platform: str | None = Field(None, min_length=1, max_length=50)
    store_url: str | None = Field(None, min_length=1, max_length=500)
    api_key: str | None = Field(None, min_length=1, max_length=1000)
    api_secret: str | None = Field(None, max_length=1000)
    is_active: bool | None = None


class StoreConnectionResponse(BaseModel):
    """
    Response schema for a store connection (credentials masked).

    Attributes:
        id: Connection UUID.
        user_id: Owning user UUID.
        platform: Store platform.
        store_url: Store base URL.
        is_active: Whether the connection is enabled.
        last_synced_at: Last successful sync timestamp.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    platform: str
    store_url: str
    is_active: bool
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Personality Schemas ─────────────────────────────────────────────


class PersonalityCreate(BaseModel):
    """
    Request schema for creating/updating a chat personality.

    Attributes:
        greeting_message: Custom greeting for visitors.
        tone: Response tone (friendly, professional, casual).
        bot_name: Display name for the AI assistant.
        escalation_rules: JSON rules for human escalation.
        response_language: ISO 639-1 language code.
        custom_instructions: Additional AI instructions.
    """

    greeting_message: str = Field(
        "Hi there! How can I help you today?",
        max_length=1000,
        description="Custom greeting message",
    )
    tone: str = Field(
        "friendly",
        description="Response tone: friendly, professional, casual",
    )
    bot_name: str = Field(
        "ShopChat Assistant",
        max_length=100,
        description="AI assistant display name",
    )
    escalation_rules: dict | None = Field(
        None, description="JSON rules for human escalation"
    )
    response_language: str = Field(
        "en", max_length=10, description="ISO 639-1 language code"
    )
    custom_instructions: str | None = Field(
        None, max_length=2000, description="Additional AI instructions"
    )


class PersonalityResponse(BaseModel):
    """
    Response schema for a chat personality configuration.

    Attributes:
        id: Personality config UUID.
        user_id: Owning user UUID.
        greeting_message: Custom greeting.
        tone: Response tone style.
        bot_name: AI assistant name.
        escalation_rules: Escalation rules JSON.
        response_language: Response language code.
        custom_instructions: Additional AI instructions.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    greeting_message: str
    tone: str
    bot_name: str
    escalation_rules: dict | None
    response_language: str
    custom_instructions: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Session Rating Schemas ──────────────────────────────────────────


class SessionRating(BaseModel):
    """
    Request schema for rating a chat session with feedback.

    Attributes:
        score: Satisfaction score from 1 to 5.
        feedback: Optional text feedback from the visitor.
    """

    score: float = Field(..., ge=1.0, le=5.0, description="Satisfaction rating 1-5")
    feedback: str | None = Field(None, max_length=2000, description="Optional feedback text")
