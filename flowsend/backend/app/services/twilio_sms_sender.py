"""
Twilio SMS sender for FlowSend.

Sends SMS messages via the Twilio REST API using the official Python SDK.

For Developers:
    Requires the ``twilio`` package. Configuration via settings:
    ``twilio_account_sid``, ``twilio_auth_token``, ``twilio_from_number``.

For QA Engineers:
    Mock ``twilio.rest.Client`` in tests. The sender returns False on
    any Twilio API error and logs the exception.

For Project Managers:
    Twilio is the industry-standard SMS provider with global reach,
    phone number provisioning, and compliance features.

For End Users:
    Your SMS messages are delivered through Twilio's trusted mobile
    messaging network with delivery confirmation.
"""

import logging

from app.config import settings
from app.services.sms_sender import AbstractSmsSender

logger = logging.getLogger(__name__)


class TwilioSmsSender(AbstractSmsSender):
    """
    Twilio SMS sender using the official Python SDK.

    Uses the Twilio REST API to send SMS messages. Supports standard
    SMS and concatenated long messages.

    Attributes:
        account_sid: Twilio account SID.
        auth_token: Twilio auth token.
        from_number: Default Twilio phone number (E.164 format).
    """

    def __init__(
        self,
        account_sid: str = "",
        auth_token: str = "",
        from_number: str = "",
    ):
        """
        Initialize Twilio sender with account credentials.

        Args:
            account_sid: Twilio account SID (default from settings).
            auth_token: Twilio auth token (default from settings).
            from_number: Default sender number (default from settings).
        """
        self.account_sid = account_sid or settings.twilio_account_sid
        self.auth_token = auth_token or settings.twilio_auth_token
        self.from_number = from_number or settings.twilio_from_number

    async def send(
        self,
        to: str,
        body: str,
        from_number: str = "",
    ) -> bool:
        """
        Send an SMS via the Twilio REST API.

        The Twilio SDK is synchronous but the call is fast (HTTP POST).
        For high-volume sending, consider running in a thread pool.

        Args:
            to: Recipient phone number in E.164 format.
            body: SMS message body.
            from_number: Override sender number (optional).

        Returns:
            True if the message was queued successfully, False on failure.
        """
        try:
            from twilio.rest import Client

            client = Client(self.account_sid, self.auth_token)
            message = client.messages.create(
                body=body,
                from_=from_number or self.from_number,
                to=to,
            )
            logger.info(
                "TwilioSmsSender: sent to=%s sid=%s status=%s",
                to,
                message.sid,
                message.status,
            )
            return True
        except Exception:
            logger.exception("TwilioSmsSender: failed to send to=%s", to)
            return False
