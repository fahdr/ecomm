"""
SQLAlchemy models for the FlowSend service.

Exports all models so Alembic can detect them for migration generation.
"""

from app.models.api_key import ApiKey
from app.models.base import Base
from app.models.campaign import Campaign, EmailEvent
from app.models.contact import Contact, ContactList
from app.models.email_template import EmailTemplate
from app.models.flow import Flow, FlowExecution
from app.models.subscription import Subscription
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Subscription",
    "ApiKey",
    "Contact",
    "ContactList",
    "EmailTemplate",
    "Flow",
    "FlowExecution",
    "Campaign",
    "EmailEvent",
]
