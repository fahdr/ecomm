"""
Tests for SMS marketing features in FlowSend.

Covers SMS senders, campaign service layer, SMS API endpoints (campaigns
and templates), and SMS delivery webhook endpoints (Twilio and AWS SNS).

For Developers:
    SMS sender tests mock external SDKs (Twilio, boto3) via monkeypatch.
    Campaign service tests exercise the ORM layer against the
    ``flowsend_test`` schema. API tests use the httpx AsyncClient with
    auth_headers for JWT-protected endpoints and raw POST for webhooks.

For Project Managers:
    SMS is the second marketing channel alongside email. These tests
    ensure reliable campaign creation, delivery tracking, template
    management, and webhook ingestion from Twilio and AWS SNS.

For QA Engineers:
    Run with: ``pytest tests/test_sms.py -v``
    Test matrix:
    - Sender factory returns correct provider instances
    - Campaign CRUD + send + analytics through service layer
    - API endpoints: auth enforcement, validation, pagination, 404s
    - Template CRUD via API
    - Webhook endpoints: Twilio form-encoded, SNS JSON, edge cases

For End Users:
    These tests validate your SMS marketing workflow -- creating
    campaigns, sending messages, managing templates, and tracking
    delivery status all work correctly end-to-end.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.contact import Contact
from app.models.sms_event import SmsEvent
from app.models.sms_template import SmsTemplate
from app.models.user import User
from app.services.sms_sender import ConsoleSmsSender, get_sms_sender
from app.services.twilio_sms_sender import TwilioSmsSender
from app.services.sns_sms_sender import AwsSnsSmsSender
from app.services.sms_campaign_service import (
    create_sms_campaign,
    get_sms_campaign,
    get_sms_campaign_analytics,
    get_sms_campaigns,
    send_sms_campaign_mock,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SMS_CAMPAIGNS_URL = "/api/v1/sms/campaigns"
SMS_TEMPLATES_URL = "/api/v1/sms/templates"


async def _create_user(db: AsyncSession) -> User:
    """Create a test User record in the database.

    Args:
        db: Async database session.

    Returns:
        The created User ORM instance.
    """
    user = User(
        email=f"sms-user-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="fakehash",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_contact(
    db: AsyncSession,
    user_id,
    email: str = "contact@example.com",
    phone: str = "+15551234567",
    sms_subscribed: bool = True,
) -> Contact:
    """Create a test Contact record in the database.

    Args:
        db: Async database session.
        user_id: UUID of the owning user.
        email: Contact email address.
        phone: Contact phone number in E.164 format.
        sms_subscribed: Whether the contact opted in for SMS.

    Returns:
        The created Contact ORM instance.
    """
    contact = Contact(
        user_id=user_id,
        email=email,
        phone_number=phone,
        sms_subscribed=sms_subscribed,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


# ===========================================================================
# SMS Sender Unit Tests
# ===========================================================================


class TestConsoleSmsSender:
    """Tests for ConsoleSmsSender -- the development-mode SMS backend."""

    @pytest.mark.asyncio
    async def test_send_logs_and_returns_true(self):
        """ConsoleSmsSender.send() logs the SMS and always returns True."""
        sender = ConsoleSmsSender()
        result = await sender.send(
            to="+15551234567",
            body="Hello from FlowSend!",
        )
        assert result is True


class TestGetSmsSender:
    """Tests for the get_sms_sender() factory function."""

    @pytest.mark.asyncio
    async def test_returns_console_sender_for_console_mode(self, monkeypatch):
        """get_sms_sender() returns ConsoleSmsSender when mode='console'."""
        monkeypatch.setattr("app.services.sms_sender.settings.sms_provider_mode", "console")
        sender = get_sms_sender()
        assert isinstance(sender, ConsoleSmsSender)

    @pytest.mark.asyncio
    async def test_returns_twilio_sender_for_twilio_mode(self, monkeypatch):
        """get_sms_sender() returns TwilioSmsSender when mode='twilio'."""
        monkeypatch.setattr("app.services.sms_sender.settings.sms_provider_mode", "twilio")
        sender = get_sms_sender()
        assert isinstance(sender, TwilioSmsSender)

    @pytest.mark.asyncio
    async def test_returns_sns_sender_for_sns_mode(self, monkeypatch):
        """get_sms_sender() returns AwsSnsSmsSender when mode='sns'."""
        monkeypatch.setattr("app.services.sms_sender.settings.sms_provider_mode", "sns")
        sender = get_sms_sender()
        assert isinstance(sender, AwsSnsSmsSender)


# ===========================================================================
# SMS Campaign Service Tests (DB)
# ===========================================================================


class TestSmsCampaignService:
    """Tests for the SMS campaign service layer functions."""

    @pytest.mark.asyncio
    async def test_create_sms_campaign(self, db: AsyncSession):
        """create_sms_campaign creates a campaign with channel='sms'."""
        user = await _create_user(db)
        campaign = await create_sms_campaign(
            db=db,
            user_id=user.id,
            name="SMS Promo",
            sms_body="50% off today!",
        )
        assert campaign.channel == "sms"
        assert campaign.name == "SMS Promo"
        assert campaign.sms_body == "50% off today!"
        assert campaign.status == "draft"

    @pytest.mark.asyncio
    async def test_get_sms_campaigns_filters_by_channel(self, db: AsyncSession):
        """get_sms_campaigns returns only campaigns with channel='sms'."""
        user = await _create_user(db)
        await create_sms_campaign(db, user.id, "SMS Camp", "Hello SMS")

        # Also create an email campaign directly to verify filtering
        email_campaign = Campaign(
            user_id=user.id,
            name="Email Camp",
            subject="Email Subject",
            channel="email",
            status="draft",
            total_recipients=0,
            sent_count=0,
        )
        db.add(email_campaign)
        await db.commit()

        campaigns = await get_sms_campaigns(db, user.id)
        assert len(campaigns) == 1
        assert campaigns[0].channel == "sms"
        assert campaigns[0].name == "SMS Camp"

    @pytest.mark.asyncio
    async def test_get_sms_campaigns_excludes_email_campaigns(self, db: AsyncSession):
        """get_sms_campaigns does not return email-channel campaigns."""
        user = await _create_user(db)
        email_campaign = Campaign(
            user_id=user.id,
            name="Email Only",
            subject="Email",
            channel="email",
            status="draft",
            total_recipients=0,
            sent_count=0,
        )
        db.add(email_campaign)
        await db.commit()

        campaigns = await get_sms_campaigns(db, user.id)
        assert len(campaigns) == 0

    @pytest.mark.asyncio
    async def test_get_sms_campaign_by_id(self, db: AsyncSession):
        """get_sms_campaign returns a specific SMS campaign by ID."""
        user = await _create_user(db)
        created = await create_sms_campaign(db, user.id, "Find Me", "Body")

        found = await get_sms_campaign(db, user.id, created.id)
        assert found.id == created.id
        assert found.name == "Find Me"

    @pytest.mark.asyncio
    async def test_get_sms_campaign_raises_for_missing(self, db: AsyncSession):
        """get_sms_campaign raises ValueError for a non-existent campaign."""
        user = await _create_user(db)
        with pytest.raises(ValueError, match="not found"):
            await get_sms_campaign(db, user.id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_sms_campaign_raises_for_email_campaign(self, db: AsyncSession):
        """get_sms_campaign raises ValueError for an email-channel campaign."""
        user = await _create_user(db)
        email_campaign = Campaign(
            user_id=user.id,
            name="Not SMS",
            subject="Subject",
            channel="email",
            status="draft",
            total_recipients=0,
            sent_count=0,
        )
        db.add(email_campaign)
        await db.commit()
        await db.refresh(email_campaign)

        with pytest.raises(ValueError, match="not found"):
            await get_sms_campaign(db, user.id, email_campaign.id)

    @pytest.mark.asyncio
    async def test_send_sms_campaign_mock_sends_to_subscribed_contacts(
        self, db: AsyncSession
    ):
        """send_sms_campaign_mock sends to contacts with sms_subscribed=True."""
        user = await _create_user(db)
        await _create_contact(db, user.id, "a@test.com", "+15551111111", sms_subscribed=True)
        await _create_contact(db, user.id, "b@test.com", "+15552222222", sms_subscribed=True)
        # Unsubscribed contact -- should be skipped
        await _create_contact(db, user.id, "c@test.com", "+15553333333", sms_subscribed=False)

        campaign = await create_sms_campaign(db, user.id, "Send Test", "Hi!")
        updated = await send_sms_campaign_mock(db, campaign)

        assert updated.sent_count == 2
        assert updated.total_recipients == 2

    @pytest.mark.asyncio
    async def test_send_sms_campaign_mock_skips_contacts_without_phone(
        self, db: AsyncSession
    ):
        """send_sms_campaign_mock skips contacts that have no phone number."""
        user = await _create_user(db)
        await _create_contact(db, user.id, "withphone@test.com", "+15554444444")
        # Contact without phone number
        no_phone = Contact(
            user_id=user.id,
            email="nophone@test.com",
            phone_number=None,
            sms_subscribed=True,
        )
        db.add(no_phone)
        await db.commit()

        campaign = await create_sms_campaign(db, user.id, "Phone Check", "Test")
        updated = await send_sms_campaign_mock(db, campaign)

        # total_recipients includes both, but sent_count only the one with phone
        assert updated.sent_count == 1
        assert updated.total_recipients == 2

    @pytest.mark.asyncio
    async def test_send_sms_campaign_mock_updates_status_to_sent(
        self, db: AsyncSession
    ):
        """send_sms_campaign_mock transitions campaign status to 'sent'."""
        user = await _create_user(db)
        await _create_contact(db, user.id, "status@test.com", "+15555555555")

        campaign = await create_sms_campaign(db, user.id, "Status Test", "Go!")
        assert campaign.status == "draft"

        updated = await send_sms_campaign_mock(db, campaign)
        assert updated.status == "sent"
        assert updated.sent_at is not None

    @pytest.mark.asyncio
    async def test_get_sms_campaign_analytics_returns_breakdown(
        self, db: AsyncSession
    ):
        """get_sms_campaign_analytics returns correct event type breakdown."""
        user = await _create_user(db)
        await _create_contact(db, user.id, "analytics@test.com", "+15556666666")

        campaign = await create_sms_campaign(db, user.id, "Analytics", "Analyze")
        await send_sms_campaign_mock(db, campaign)

        analytics = await get_sms_campaign_analytics(db, user.id, campaign.id)
        assert analytics["campaign_id"] == str(campaign.id)
        assert analytics["total_sent"] >= 1
        assert "breakdown" in analytics
        assert "sent" in analytics["breakdown"]


# ===========================================================================
# SMS Campaign API Tests (httpx)
# ===========================================================================


class TestSmsCampaignApi:
    """Tests for SMS campaign HTTP API endpoints."""

    @pytest.mark.asyncio
    async def test_create_sms_campaign_201(
        self, client: AsyncClient, auth_headers: dict
    ):
        """POST /sms/campaigns creates an SMS campaign and returns 201."""
        payload = {"name": "API SMS Camp", "sms_body": "Buy now!"}
        resp = await client.post(SMS_CAMPAIGNS_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "API SMS Camp"
        assert data["channel"] == "sms"
        assert data["sms_body"] == "Buy now!"
        assert data["status"] == "draft"

    @pytest.mark.asyncio
    async def test_create_sms_campaign_validates_sms_body_required(
        self, client: AsyncClient, auth_headers: dict
    ):
        """POST /sms/campaigns without sms_body returns 422."""
        payload = {"name": "Missing Body"}
        resp = await client.post(SMS_CAMPAIGNS_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_sms_campaigns_only(
        self, client: AsyncClient, auth_headers: dict
    ):
        """GET /sms/campaigns lists only SMS campaigns."""
        # Create an SMS campaign
        await client.post(
            SMS_CAMPAIGNS_URL,
            json={"name": "SMS List", "sms_body": "Test"},
            headers=auth_headers,
        )
        # Create an email campaign through the email campaigns API
        await client.post(
            "/api/v1/campaigns",
            json={"name": "Email Camp", "subject": "Subject"},
            headers=auth_headers,
        )

        resp = await client.get(SMS_CAMPAIGNS_URL, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for camp in data:
            assert camp["channel"] == "sms"

    @pytest.mark.asyncio
    async def test_list_sms_campaigns_supports_pagination(
        self, client: AsyncClient, auth_headers: dict
    ):
        """GET /sms/campaigns supports page and page_size parameters."""
        for i in range(3):
            await client.post(
                SMS_CAMPAIGNS_URL,
                json={"name": f"Page Camp {i}", "sms_body": f"Body {i}"},
                headers=auth_headers,
            )

        resp = await client.get(
            f"{SMS_CAMPAIGNS_URL}?page=1&page_size=2", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_sms_campaign_by_id(
        self, client: AsyncClient, auth_headers: dict
    ):
        """GET /sms/campaigns/{id} returns the campaign."""
        create_resp = await client.post(
            SMS_CAMPAIGNS_URL,
            json={"name": "Get By ID", "sms_body": "Find me"},
            headers=auth_headers,
        )
        campaign_id = create_resp.json()["id"]

        resp = await client.get(
            f"{SMS_CAMPAIGNS_URL}/{campaign_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Get By ID"

    @pytest.mark.asyncio
    async def test_get_sms_campaign_404_for_missing(
        self, client: AsyncClient, auth_headers: dict
    ):
        """GET /sms/campaigns/{id} returns 404 for a non-existent campaign."""
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"{SMS_CAMPAIGNS_URL}/{fake_id}", headers=auth_headers
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_send_sms_campaign(
        self, client: AsyncClient, auth_headers: dict
    ):
        """POST /sms/campaigns/{id}/send sends the campaign."""
        # Create a contact via the contacts API so the user has recipients
        await client.post(
            "/api/v1/contacts",
            json={
                "email": "sms-recipient@example.com",
                "phone_number": "+15557777777",
                "sms_subscribed": True,
            },
            headers=auth_headers,
        )

        create_resp = await client.post(
            SMS_CAMPAIGNS_URL,
            json={"name": "Sendable SMS", "sms_body": "Go!"},
            headers=auth_headers,
        )
        campaign_id = create_resp.json()["id"]

        send_resp = await client.post(
            f"{SMS_CAMPAIGNS_URL}/{campaign_id}/send", headers=auth_headers
        )
        assert send_resp.status_code == 200
        data = send_resp.json()
        assert data["status"] == "sent"

    @pytest.mark.asyncio
    async def test_get_sms_campaign_analytics(
        self, client: AsyncClient, auth_headers: dict
    ):
        """GET /sms/campaigns/{id}/analytics returns analytics data."""
        await client.post(
            "/api/v1/contacts",
            json={
                "email": "analytics-sms@example.com",
                "phone_number": "+15558888888",
                "sms_subscribed": True,
            },
            headers=auth_headers,
        )

        create_resp = await client.post(
            SMS_CAMPAIGNS_URL,
            json={"name": "Analytics SMS", "sms_body": "Track me"},
            headers=auth_headers,
        )
        campaign_id = create_resp.json()["id"]

        # Send first so there are events
        await client.post(
            f"{SMS_CAMPAIGNS_URL}/{campaign_id}/send", headers=auth_headers
        )

        resp = await client.get(
            f"{SMS_CAMPAIGNS_URL}/{campaign_id}/analytics", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_sent" in data
        assert "breakdown" in data

    @pytest.mark.asyncio
    async def test_sms_campaign_endpoints_require_auth(self, client: AsyncClient):
        """All SMS campaign endpoints return 401 without auth headers."""
        resp_list = await client.get(SMS_CAMPAIGNS_URL)
        assert resp_list.status_code == 401

        resp_create = await client.post(
            SMS_CAMPAIGNS_URL, json={"name": "NoAuth", "sms_body": "test"}
        )
        assert resp_create.status_code == 401

        fake_id = str(uuid.uuid4())
        resp_get = await client.get(f"{SMS_CAMPAIGNS_URL}/{fake_id}")
        assert resp_get.status_code == 401

        resp_send = await client.post(f"{SMS_CAMPAIGNS_URL}/{fake_id}/send")
        assert resp_send.status_code == 401

        resp_analytics = await client.get(f"{SMS_CAMPAIGNS_URL}/{fake_id}/analytics")
        assert resp_analytics.status_code == 401


# ===========================================================================
# SMS Template API Tests (httpx)
# ===========================================================================


class TestSmsTemplateApi:
    """Tests for SMS template HTTP API endpoints."""

    @pytest.mark.asyncio
    async def test_create_template_201(
        self, client: AsyncClient, auth_headers: dict
    ):
        """POST /sms/templates creates a template and returns 201."""
        payload = {
            "name": "Welcome SMS",
            "body": "Welcome to our store!",
            "category": "transactional",
        }
        resp = await client.post(
            SMS_TEMPLATES_URL, json=payload, headers=auth_headers
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Welcome SMS"
        assert data["body"] == "Welcome to our store!"
        assert data["category"] == "transactional"

    @pytest.mark.asyncio
    async def test_create_template_validates_body_max_1600(
        self, client: AsyncClient, auth_headers: dict
    ):
        """POST /sms/templates rejects body exceeding 1600 characters."""
        payload = {
            "name": "Too Long",
            "body": "x" * 1601,
        }
        resp = await client.post(
            SMS_TEMPLATES_URL, json=payload, headers=auth_headers
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_templates(self, client: AsyncClient, auth_headers: dict):
        """GET /sms/templates lists all SMS templates for the user."""
        await client.post(
            SMS_TEMPLATES_URL,
            json={"name": "Template A", "body": "Body A"},
            headers=auth_headers,
        )
        await client.post(
            SMS_TEMPLATES_URL,
            json={"name": "Template B", "body": "Body B"},
            headers=auth_headers,
        )

        resp = await client.get(SMS_TEMPLATES_URL, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_template_by_id(
        self, client: AsyncClient, auth_headers: dict
    ):
        """GET /sms/templates/{id} returns the template."""
        create_resp = await client.post(
            SMS_TEMPLATES_URL,
            json={"name": "Get Template", "body": "Find me"},
            headers=auth_headers,
        )
        template_id = create_resp.json()["id"]

        resp = await client.get(
            f"{SMS_TEMPLATES_URL}/{template_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Get Template"

    @pytest.mark.asyncio
    async def test_get_template_404_for_missing(
        self, client: AsyncClient, auth_headers: dict
    ):
        """GET /sms/templates/{id} returns 404 for a non-existent template."""
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"{SMS_TEMPLATES_URL}/{fake_id}", headers=auth_headers
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_template(
        self, client: AsyncClient, auth_headers: dict
    ):
        """PATCH /sms/templates/{id} updates the template fields."""
        create_resp = await client.post(
            SMS_TEMPLATES_URL,
            json={"name": "Old Name", "body": "Old body"},
            headers=auth_headers,
        )
        template_id = create_resp.json()["id"]

        patch_resp = await client.patch(
            f"{SMS_TEMPLATES_URL}/{template_id}",
            json={"name": "New Name", "body": "New body"},
            headers=auth_headers,
        )
        assert patch_resp.status_code == 200
        data = patch_resp.json()
        assert data["name"] == "New Name"
        assert data["body"] == "New body"

    @pytest.mark.asyncio
    async def test_delete_template_204(
        self, client: AsyncClient, auth_headers: dict
    ):
        """DELETE /sms/templates/{id} deletes the template and returns 204."""
        create_resp = await client.post(
            SMS_TEMPLATES_URL,
            json={"name": "Delete Me", "body": "Bye"},
            headers=auth_headers,
        )
        template_id = create_resp.json()["id"]

        del_resp = await client.delete(
            f"{SMS_TEMPLATES_URL}/{template_id}", headers=auth_headers
        )
        assert del_resp.status_code == 204

        # Verify it is gone
        get_resp = await client.get(
            f"{SMS_TEMPLATES_URL}/{template_id}", headers=auth_headers
        )
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_template_endpoints_require_auth(self, client: AsyncClient):
        """All SMS template endpoints return 401 without auth headers."""
        resp_list = await client.get(SMS_TEMPLATES_URL)
        assert resp_list.status_code == 401

        resp_create = await client.post(
            SMS_TEMPLATES_URL, json={"name": "NoAuth", "body": "test"}
        )
        assert resp_create.status_code == 401

        fake_id = str(uuid.uuid4())
        resp_get = await client.get(f"{SMS_TEMPLATES_URL}/{fake_id}")
        assert resp_get.status_code == 401

        resp_patch = await client.patch(
            f"{SMS_TEMPLATES_URL}/{fake_id}", json={"name": "NoAuth"}
        )
        assert resp_patch.status_code == 401

        resp_delete = await client.delete(f"{SMS_TEMPLATES_URL}/{fake_id}")
        assert resp_delete.status_code == 401


# ===========================================================================
# SMS Webhook Endpoint Tests
# ===========================================================================


class TestTwilioSmsWebhook:
    """Tests for POST /api/v1/webhooks/twilio-sms-status endpoint."""

    @pytest.mark.asyncio
    async def test_delivered_status_creates_event(
        self, client: AsyncClient, db: AsyncSession
    ):
        """Twilio webhook with delivered status creates a 'delivered' SmsEvent."""
        user = await _create_user(db)
        contact = await _create_contact(db, user.id, "twilio-d@test.com", "+15559990001")

        resp = await client.post(
            "/api/v1/webhooks/twilio-sms-status",
            data={
                "MessageSid": "SM1234567890",
                "MessageStatus": "delivered",
                "contact_id": str(contact.id),
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # Verify SmsEvent was created
        result = await db.execute(
            select(SmsEvent).where(SmsEvent.provider_message_id == "SM1234567890")
        )
        event = result.scalar_one_or_none()
        assert event is not None
        assert event.event_type == "delivered"

    @pytest.mark.asyncio
    async def test_failed_status_creates_event(
        self, client: AsyncClient, db: AsyncSession
    ):
        """Twilio webhook with failed status creates a 'failed' SmsEvent."""
        user = await _create_user(db)
        contact = await _create_contact(db, user.id, "twilio-f@test.com", "+15559990002")

        resp = await client.post(
            "/api/v1/webhooks/twilio-sms-status",
            data={
                "MessageSid": "SM0000000001",
                "MessageStatus": "failed",
                "contact_id": str(contact.id),
                "ErrorCode": "30006",
            },
        )
        assert resp.status_code == 200

        result = await db.execute(
            select(SmsEvent).where(SmsEvent.provider_message_id == "SM0000000001")
        )
        event = result.scalar_one_or_none()
        assert event is not None
        assert event.event_type == "failed"
        assert event.error_code == "30006"

    @pytest.mark.asyncio
    async def test_missing_message_sid_returns_400(self, client: AsyncClient):
        """Twilio webhook without MessageSid returns 400."""
        resp = await client.post(
            "/api/v1/webhooks/twilio-sms-status",
            data={"MessageStatus": "delivered"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_unknown_status_returns_skipped(self, client: AsyncClient):
        """Twilio webhook with an unmapped status returns skipped=True."""
        resp = await client.post(
            "/api/v1/webhooks/twilio-sms-status",
            data={
                "MessageSid": "SM_UNKNOWN",
                "MessageStatus": "receiving",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("skipped") is True


class TestSnsSmsWebhook:
    """Tests for POST /api/v1/webhooks/sns-sms-status endpoint."""

    @pytest.mark.asyncio
    async def test_subscription_confirmation_returns_confirmed(
        self, client: AsyncClient
    ):
        """SNS SMS webhook with SubscriptionConfirmation returns confirmed."""
        payload = {
            "Type": "SubscriptionConfirmation",
            "SubscribeURL": "https://sns.example.com/confirm",
        }
        resp = await client.post("/api/v1/webhooks/sns-sms-status", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_success_creates_delivered_event(
        self, client: AsyncClient, db: AsyncSession
    ):
        """SNS SMS webhook with SUCCESS status creates a 'delivered' SmsEvent."""
        user = await _create_user(db)
        contact = await _create_contact(db, user.id, "sns-s@test.com", "+15559990003")

        import json

        message_data = {
            "status": "SUCCESS",
            "notification": {"messageId": "sns-msg-001"},
            "contact_id": str(contact.id),
        }
        payload = {
            "Type": "Notification",
            "Message": json.dumps(message_data),
        }
        resp = await client.post("/api/v1/webhooks/sns-sms-status", json=payload)
        assert resp.status_code == 200

        result = await db.execute(
            select(SmsEvent).where(SmsEvent.provider_message_id == "sns-msg-001")
        )
        event = result.scalar_one_or_none()
        assert event is not None
        assert event.event_type == "delivered"

    @pytest.mark.asyncio
    async def test_failure_creates_failed_event(
        self, client: AsyncClient, db: AsyncSession
    ):
        """SNS SMS webhook with FAILURE status creates a 'failed' SmsEvent."""
        user = await _create_user(db)
        contact = await _create_contact(db, user.id, "sns-f@test.com", "+15559990004")

        import json

        message_data = {
            "status": "FAILURE",
            "notification": {"messageId": "sns-msg-002"},
            "contact_id": str(contact.id),
        }
        payload = {
            "Type": "Notification",
            "Message": json.dumps(message_data),
        }
        resp = await client.post("/api/v1/webhooks/sns-sms-status", json=payload)
        assert resp.status_code == 200

        result = await db.execute(
            select(SmsEvent).where(SmsEvent.provider_message_id == "sns-msg-002")
        )
        event = result.scalar_one_or_none()
        assert event is not None
        assert event.event_type == "failed"

    @pytest.mark.asyncio
    async def test_invalid_json_returns_400(self, client: AsyncClient):
        """SNS SMS webhook with malformed JSON returns 400."""
        resp = await client.post(
            "/api/v1/webhooks/sns-sms-status",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400
