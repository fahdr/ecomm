"""
SQLAlchemy models for the ShopChat service.

Exports all models so Alembic can detect them for migration generation.
"""

from app.models.api_key import ApiKey
from app.models.base import Base
from app.models.chat_analytics import ChatAnalytics
from app.models.chatbot import Chatbot
from app.models.conversation import Conversation
from app.models.knowledge_base import KnowledgeBase
from app.models.message import Message
from app.models.personality import ChatPersonality
from app.models.store_connection import StoreConnection
from app.models.subscription import Subscription
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Subscription",
    "ApiKey",
    "Chatbot",
    "KnowledgeBase",
    "Conversation",
    "Message",
    "StoreConnection",
    "ChatAnalytics",
    "ChatPersonality",
]
