"""
Tests for email provider senders and webhook event processing in FlowSend.

Covers the full email delivery stack: sender factory, provider-specific
sender initialization, webhook event ingestion from AWS SES and SendGrid,
and the corresponding API endpoints.

For Developers:
    Unit tests mock external dependencies (settings, SMTP, SES, SendGrid)
    so they run without credentials. DB tests use the ``flowsend_test``
    schema via the shared conftest fixtures. Webhook API tests exercise
    the full HTTP path through the FastAPI router.

For Project Managers:
    These tests validate email delivery reliability, the core revenue
    feature. Webhook processing converts raw provider callbacks into
    actionable analytics (bounces, opens, clicks) for campaign dashboards.

For QA Engineers:
    Run with: ``pytest tests/test_email_providers.py -v``
    Verify: sender factory returns correct implementations, SES/SendGrid
    event mapping is accurate, webhook endpoints handle edge cases (bad
    JSON, unknown event types, subscription confirmations).

For End Users:
    These tests ensure your email delivery tracking works correctly --
    bounces, opens, and clicks are captured automatically from your
    email provider so you see accurate analytics in your dashboard.
"""

import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, EmailEvent
from app.models.contact import Contact
from app.models.user import User
from app.services.email_sender import ConsoleEmailSender, SmtpEmailSender, get_email_sender
from app.services.ses_email_sender import SesEmailSender
from app.services.sendgrid_email_sender import SendGridEmailSender
from app.services.webhook_event_service import process_sendgrid_event, process_ses_event


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user_and_contact(
    db: AsyncSession,
    contact_email: str = "contact@example.com",
    phone: str = "+15551234567",
) -> tuple:
    """Create a User and Contact in the database for webhook tests.

    Args:
        db: Async database session.
        contact_email: Email address for the contact.
        phone: Phone number for the contact.

    Returns:
        Tuple of (User, Contact) ORM instances.
    """
    user = User(
        email=f"user-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="fakehash",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    contact = Contact(
        user_id=user.id,
        email=contact_email,
        phone_number=phone,
        sms_subscribed=True,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return user, contact


def _ses_event_payload(
    notification_type: str,
    contact_id: str,
    campaign_id: str | None = None,
    bounce_type: str | None = None,
    complaint_feedback_type: str | None = None,
) -> dict:
    """Build a mock SES SNS notification payload.

    Args:
        notification_type: SES notification type (Bounce, Delivery, etc.).
        contact_id: UUID string for the target contact.
        campaign_id: Optional UUID string for the campaign.
        bounce_type: Optional bounce type (for Bounce notifications).
        complaint_feedback_type: Optional feedback type (for Complaint notifications).

    Returns:
        Dict structured like a parsed SES SNS notification.
    """
    tags: dict = {"contact_id": [contact_id]}
    if campaign_id:
        tags["campaign_id"] = [campaign_id]

    payload: dict = {
        "notificationType": notification_type,
        "mail": {
            "messageId": f"ses-msg-{uuid.uuid4().hex[:8]}",
            "tags": tags,
        },
    }
    if bounce_type:
        payload["bounce"] = {"bounceType": bounce_type}
    if complaint_feedback_type:
        payload["complaint"] = {"complaintFeedbackType": complaint_feedback_type}
    return payload


def _sendgrid_event_payload(
    event: str,
    contact_id: str,
    campaign_id: str | None = None,
    reason: str | None = None,
) -> dict:
    """Build a mock SendGrid webhook event payload.

    Args:
        event: SendGrid event type (delivered, bounce, open, etc.).
        contact_id: UUID string for the target contact.
        campaign_id: Optional UUID string for the campaign.
        reason: Optional bounce reason string.

    Returns:
        Dict structured like a single SendGrid webhook event.
    """
    payload: dict = {
        "event": event,
        "sg_message_id": f"sg-msg-{uuid.uuid4().hex[:8]}",
        "contact_id": contact_id,
    }
    if campaign_id:
        payload["campaign_id"] = campaign_id
    if reason:
        payload["reason"] = reason
    return payload


# ===========================================================================
# Email Sender Unit Tests
# ===========================================================================


class TestConsoleEmailSender:
    """Tests for ConsoleEmailSender -- the development-mode email backend."""

    @pytest.mark.asyncio
    async def test_send_logs_and_returns_true(self):
        """ConsoleEmailSender.send() logs the email and always returns True."""
        sender = ConsoleEmailSender()
        result = await sender.send(
            to="user@example.com",
            subject="Hello",
            html_body="<p>Hi</p>",
            plain_body="Hi",
        )
        assert result is True


class TestGetEmailSender:
    """Tests for the get_email_sender() factory function."""

    @pytest.mark.asyncio
    async def test_returns_console_sender_for_console_mode(self, monkeypatch):
        """get_email_sender() returns ConsoleEmailSender when mode='console'."""
        monkeypatch.setattr("app.services.email_sender.settings.email_sender_mode", "console")
        sender = get_email_sender()
        assert isinstance(sender, ConsoleEmailSender)

    @pytest.mark.asyncio
    async def test_returns_smtp_sender_for_smtp_mode(self, monkeypatch):
        """get_email_sender() returns SmtpEmailSender when mode='smtp'."""
        monkeypatch.setattr("app.services.email_sender.settings.email_sender_mode", "smtp")
        sender = get_email_sender()
        assert isinstance(sender, SmtpEmailSender)

    @pytest.mark.asyncio
    async def test_returns_ses_sender_for_ses_mode(self, monkeypatch):
        """get_email_sender() returns SesEmailSender when mode='ses'."""
        monkeypatch.setattr("app.services.email_sender.settings.email_sender_mode", "ses")
        sender = get_email_sender()
        assert isinstance(sender, SesEmailSender)

    @pytest.mark.asyncio
    async def test_returns_sendgrid_sender_for_sendgrid_mode(self, monkeypatch):
        """get_email_sender() returns SendGridEmailSender when mode='sendgrid'."""
        monkeypatch.setattr("app.services.email_sender.settings.email_sender_mode", "sendgrid")
        sender = get_email_sender()
        assert isinstance(sender, SendGridEmailSender)


class TestSesEmailSenderInit:
    """Tests for SesEmailSender initialization from settings."""

    @pytest.mark.asyncio
    async def test_reads_from_settings(self, monkeypatch):
        """SesEmailSender.__init__ populates attributes from settings."""
        monkeypatch.setattr("app.services.ses_email_sender.settings.ses_region", "eu-west-1")
        monkeypatch.setattr("app.services.ses_email_sender.settings.ses_access_key_id", "AKTEST")
        monkeypatch.setattr("app.services.ses_email_sender.settings.ses_secret_access_key", "SECRET")
        monkeypatch.setattr("app.services.ses_email_sender.settings.email_from_address", "ses@test.com")
        monkeypatch.setattr("app.services.ses_email_sender.settings.email_from_name", "SES Test")
        monkeypatch.setattr("app.services.ses_email_sender.settings.ses_configuration_set", "my-config-set")

        sender = SesEmailSender()
        assert sender.region == "eu-west-1"
        assert sender.access_key_id == "AKTEST"
        assert sender.secret_access_key == "SECRET"
        assert sender.from_address == "ses@test.com"
        assert sender.from_name == "SES Test"
        assert sender.configuration_set == "my-config-set"


class TestSendGridEmailSenderInit:
    """Tests for SendGridEmailSender initialization from settings."""

    @pytest.mark.asyncio
    async def test_reads_from_settings(self, monkeypatch):
        """SendGridEmailSender.__init__ populates attributes from settings."""
        monkeypatch.setattr("app.services.sendgrid_email_sender.settings.sendgrid_api_key", "SG.testkey")
        monkeypatch.setattr("app.services.sendgrid_email_sender.settings.email_from_address", "sg@test.com")
        monkeypatch.setattr("app.services.sendgrid_email_sender.settings.email_from_name", "SG Test")

        sender = SendGridEmailSender()
        assert sender.api_key == "SG.testkey"
        assert sender.from_address == "sg@test.com"
        assert sender.from_name == "SG Test"


# ===========================================================================
# Webhook Event Service Tests (DB)
# ===========================================================================


class TestProcessSesEvent:
    """Tests for process_ses_event() -- SES webhook event processing."""

    @pytest.mark.asyncio
    async def test_bounce_creates_email_event(self, db: AsyncSession):
        """process_ses_event creates an EmailEvent with event_type='bounced' for Bounce."""
        _, contact = await _create_user_and_contact(db)
        payload = _ses_event_payload("Bounce", str(contact.id), bounce_type="Permanent")

        event = await process_ses_event(db, payload)
        assert event is not None
        assert event.event_type == "bounced"
        assert event.contact_id == contact.id

    @pytest.mark.asyncio
    async def test_delivery_creates_email_event(self, db: AsyncSession):
        """process_ses_event creates an EmailEvent with event_type='delivered' for Delivery."""
        _, contact = await _create_user_and_contact(db)
        payload = _ses_event_payload("Delivery", str(contact.id))

        event = await process_ses_event(db, payload)
        assert event is not None
        assert event.event_type == "delivered"

    @pytest.mark.asyncio
    async def test_open_creates_email_event(self, db: AsyncSession):
        """process_ses_event creates an EmailEvent with event_type='opened' for Open."""
        _, contact = await _create_user_and_contact(db)
        payload = _ses_event_payload("Open", str(contact.id))

        event = await process_ses_event(db, payload)
        assert event is not None
        assert event.event_type == "opened"

    @pytest.mark.asyncio
    async def test_click_creates_email_event(self, db: AsyncSession):
        """process_ses_event creates an EmailEvent with event_type='clicked' for Click."""
        _, contact = await _create_user_and_contact(db)
        payload = _ses_event_payload("Click", str(contact.id))

        event = await process_ses_event(db, payload)
        assert event is not None
        assert event.event_type == "clicked"

    @pytest.mark.asyncio
    async def test_unknown_notification_type_returns_none(self, db: AsyncSession):
        """process_ses_event returns None for an unrecognized notification type."""
        _, contact = await _create_user_and_contact(db)
        payload = _ses_event_payload("UnknownType", str(contact.id))

        event = await process_ses_event(db, payload)
        assert event is None

    @pytest.mark.asyncio
    async def test_no_contact_id_returns_none(self, db: AsyncSession):
        """process_ses_event returns None when no contact_id is in the tags."""
        payload = {
            "notificationType": "Delivery",
            "mail": {
                "messageId": "test-msg-123",
                "tags": {},
            },
        }
        event = await process_ses_event(db, payload)
        assert event is None

    @pytest.mark.asyncio
    async def test_bounce_type_stored_as_error_code(self, db: AsyncSession):
        """process_ses_event stores bounce.bounceType as error_code."""
        _, contact = await _create_user_and_contact(db)
        payload = _ses_event_payload("Bounce", str(contact.id), bounce_type="Permanent")

        event = await process_ses_event(db, payload)
        assert event is not None
        assert event.error_code == "Permanent"

    @pytest.mark.asyncio
    async def test_complaint_feedback_type_stored_as_error_code(self, db: AsyncSession):
        """process_ses_event stores complaint.complaintFeedbackType as error_code."""
        _, contact = await _create_user_and_contact(db)
        payload = _ses_event_payload(
            "Complaint",
            str(contact.id),
            complaint_feedback_type="abuse",
        )

        event = await process_ses_event(db, payload)
        assert event is not None
        assert event.event_type == "bounced"  # Complaint maps to bounced
        assert event.error_code == "abuse"


class TestProcessSendGridEvent:
    """Tests for process_sendgrid_event() -- SendGrid webhook event processing."""

    @pytest.mark.asyncio
    async def test_delivered_creates_email_event(self, db: AsyncSession):
        """process_sendgrid_event creates EmailEvent with event_type='delivered'."""
        _, contact = await _create_user_and_contact(db)
        payload = _sendgrid_event_payload("delivered", str(contact.id))

        event = await process_sendgrid_event(db, payload)
        assert event is not None
        assert event.event_type == "delivered"
        assert event.contact_id == contact.id

    @pytest.mark.asyncio
    async def test_bounce_creates_email_event(self, db: AsyncSession):
        """process_sendgrid_event creates EmailEvent with event_type='bounced' for bounce."""
        _, contact = await _create_user_and_contact(db)
        payload = _sendgrid_event_payload("bounce", str(contact.id))

        event = await process_sendgrid_event(db, payload)
        assert event is not None
        assert event.event_type == "bounced"

    @pytest.mark.asyncio
    async def test_open_creates_email_event(self, db: AsyncSession):
        """process_sendgrid_event creates EmailEvent with event_type='opened' for open."""
        _, contact = await _create_user_and_contact(db)
        payload = _sendgrid_event_payload("open", str(contact.id))

        event = await process_sendgrid_event(db, payload)
        assert event is not None
        assert event.event_type == "opened"

    @pytest.mark.asyncio
    async def test_click_creates_email_event(self, db: AsyncSession):
        """process_sendgrid_event creates EmailEvent with event_type='clicked' for click."""
        _, contact = await _create_user_and_contact(db)
        payload = _sendgrid_event_payload("click", str(contact.id))

        event = await process_sendgrid_event(db, payload)
        assert event is not None
        assert event.event_type == "clicked"

    @pytest.mark.asyncio
    async def test_unsubscribe_creates_email_event(self, db: AsyncSession):
        """process_sendgrid_event creates EmailEvent with event_type='unsubscribed'."""
        _, contact = await _create_user_and_contact(db)
        payload = _sendgrid_event_payload("unsubscribe", str(contact.id))

        event = await process_sendgrid_event(db, payload)
        assert event is not None
        assert event.event_type == "unsubscribed"

    @pytest.mark.asyncio
    async def test_unknown_event_returns_none(self, db: AsyncSession):
        """process_sendgrid_event returns None for an unrecognized event type."""
        _, contact = await _create_user_and_contact(db)
        payload = _sendgrid_event_payload("dropped", str(contact.id))

        event = await process_sendgrid_event(db, payload)
        assert event is None

    @pytest.mark.asyncio
    async def test_no_contact_id_returns_none(self, db: AsyncSession):
        """process_sendgrid_event returns None when contact_id is missing."""
        payload = {"event": "delivered", "sg_message_id": "msg-123"}
        event = await process_sendgrid_event(db, payload)
        assert event is None

    @pytest.mark.asyncio
    async def test_bounce_reason_stored_as_error_code(self, db: AsyncSession):
        """process_sendgrid_event stores reason as error_code for bounce events."""
        _, contact = await _create_user_and_contact(db)
        payload = _sendgrid_event_payload(
            "bounce", str(contact.id), reason="550 User not found"
        )

        event = await process_sendgrid_event(db, payload)
        assert event is not None
        assert event.error_code == "550 User not found"


# ===========================================================================
# Webhook API Endpoint Tests
# ===========================================================================


class TestSesWebhookEndpoint:
    """Tests for POST /api/v1/webhooks/ses-events endpoint."""

    @pytest.mark.asyncio
    async def test_subscription_confirmation_returns_confirmed(
        self, client: AsyncClient
    ):
        """POST with SNS SubscriptionConfirmation returns status 'confirmed'."""
        payload = {
            "Type": "SubscriptionConfirmation",
            "SubscribeURL": "https://sns.example.com/confirm?token=abc",
        }
        resp = await client.post("/api/v1/webhooks/ses-events", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_notification_creates_email_event(
        self, client: AsyncClient, db: AsyncSession
    ):
        """POST with SNS Notification containing a valid SES event creates an EmailEvent."""
        _, contact = await _create_user_and_contact(db)
        ses_event = _ses_event_payload("Delivery", str(contact.id))
        payload = {
            "Type": "Notification",
            "Message": json.dumps(ses_event),
        }
        resp = await client.post("/api/v1/webhooks/ses-events", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "event_id" in data

    @pytest.mark.asyncio
    async def test_invalid_json_returns_400(self, client: AsyncClient):
        """POST with malformed JSON body returns 400."""
        resp = await client.post(
            "/api/v1/webhooks/ses-events",
            content=b"not json at all",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400


class TestSendGridWebhookEndpoint:
    """Tests for POST /api/v1/webhooks/sendgrid-events endpoint."""

    @pytest.mark.asyncio
    async def test_valid_event_array_creates_events(
        self, client: AsyncClient, db: AsyncSession
    ):
        """POST with a valid event array creates EmailEvent records."""
        _, contact = await _create_user_and_contact(db)
        events = [
            _sendgrid_event_payload("delivered", str(contact.id)),
            _sendgrid_event_payload("open", str(contact.id)),
        ]
        resp = await client.post("/api/v1/webhooks/sendgrid-events", json=events)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["processed"] == 2

    @pytest.mark.asyncio
    async def test_empty_array_returns_processed_zero(self, client: AsyncClient):
        """POST with an empty JSON array returns processed: 0."""
        resp = await client.post("/api/v1/webhooks/sendgrid-events", json=[])
        assert resp.status_code == 200
        data = resp.json()
        assert data["processed"] == 0

    @pytest.mark.asyncio
    async def test_non_array_returns_400(self, client: AsyncClient):
        """POST with a non-array JSON body returns 400."""
        resp = await client.post(
            "/api/v1/webhooks/sendgrid-events",
            json={"event": "delivered"},
        )
        assert resp.status_code == 400
