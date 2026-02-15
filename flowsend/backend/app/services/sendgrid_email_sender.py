"""
SendGrid email sender for FlowSend.

Sends emails via the SendGrid v3 API using the official Python SDK.
Falls back to console logging if the API key is missing.

For Developers:
    Requires the ``sendgrid`` package. Configuration via settings:
    ``sendgrid_api_key``. Uses the ``sendgrid.helpers.mail`` module
    for message construction.

For QA Engineers:
    Mock the ``sendgrid.SendGridAPIClient`` in tests. The sender
    returns False on any API error and logs the exception.

For Project Managers:
    SendGrid offers robust delivery infrastructure with built-in
    analytics, bounce handling, and compliance features.

For End Users:
    Your emails are delivered through SendGrid's trusted email
    platform with automatic bounce and spam handling.
"""

import logging

from app.config import settings
from app.services.email_sender import AbstractEmailSender

logger = logging.getLogger(__name__)


class SendGridEmailSender(AbstractEmailSender):
    """
    SendGrid email sender using the official Python SDK.

    Constructs a Mail object and sends via the SendGrid v3 API.
    Supports HTML with optional plain-text fallback.

    Attributes:
        api_key: SendGrid API key for authentication.
        from_address: Verified sender email address.
        from_name: Sender display name.
    """

    def __init__(
        self,
        api_key: str = "",
        from_address: str = "",
        from_name: str = "",
    ):
        """
        Initialize SendGrid sender with API credentials.

        Args:
            api_key: SendGrid API key (default from settings).
            from_address: Sender email (default from settings).
            from_name: Sender display name (default from settings).
        """
        self.api_key = api_key or settings.sendgrid_api_key
        self.from_address = from_address or settings.email_from_address
        self.from_name = from_name or settings.email_from_name

    async def send(
        self,
        to: str,
        subject: str,
        html_body: str,
        plain_body: str | None = None,
    ) -> bool:
        """
        Send an email via the SendGrid API.

        Uses the SendGrid Python SDK to construct and send a message.
        The SDK call is synchronous but wrapped in the async interface
        for consistency with other senders.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_body: HTML body content.
            plain_body: Plain-text fallback body (optional).

        Returns:
            True if sent successfully (2xx response), False on failure.
        """
        try:
            import sendgrid
            from sendgrid.helpers.mail import (
                Content,
                Email,
                Mail,
                To,
            )

            sg = sendgrid.SendGridAPIClient(api_key=self.api_key)

            from_email = Email(self.from_address, self.from_name)
            to_email = To(to)
            html_content = Content("text/html", html_body)

            mail = Mail(from_email, to_email, subject, html_content)

            if plain_body:
                mail.add_content(Content("text/plain", plain_body))

            response = sg.client.mail.send.post(request_body=mail.get())

            if response.status_code in (200, 201, 202):
                logger.info(
                    "SendGridEmailSender: sent to=%s subject=%s status=%d",
                    to,
                    subject,
                    response.status_code,
                )
                return True

            logger.warning(
                "SendGridEmailSender: unexpected status=%d to=%s",
                response.status_code,
                to,
            )
            return False
        except Exception:
            logger.exception("SendGridEmailSender: failed to send to=%s", to)
            return False
