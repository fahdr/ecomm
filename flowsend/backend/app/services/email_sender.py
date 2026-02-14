"""
Email sender abstraction for FlowSend.

Provides a pluggable email delivery layer with two implementations:
- ConsoleEmailSender: Logs emails to stdout (development/testing).
- SmtpEmailSender: Sends emails via SMTP (production, behind feature flag).

A factory function ``get_email_sender()`` returns the appropriate sender
based on the ``email_sender_mode`` setting.

For Developers:
    Always use ``get_email_sender()`` to obtain a sender instance.
    Never instantiate senders directly in application code. To add a new
    provider (e.g., SendGrid, SES), subclass ``AbstractEmailSender`` and
    update the factory.

For QA Engineers:
    Tests should use ConsoleEmailSender (the default). To verify email
    content, capture log output or mock the ``send()`` method.

For Project Managers:
    Email delivery is the core revenue driver. Console mode prevents
    accidental sends during development. SMTP mode is gated behind
    ``email_sender_mode=smtp`` in production configuration.

For End Users:
    FlowSend handles email delivery automatically. Your emails are sent
    through secure SMTP infrastructure with delivery tracking.
"""

import logging
from abc import ABC, abstractmethod

from app.config import settings

logger = logging.getLogger(__name__)


class AbstractEmailSender(ABC):
    """
    Abstract base class for email delivery backends.

    All email senders must implement the ``send()`` method, which handles
    delivering a single email to one recipient.
    """

    @abstractmethod
    async def send(
        self,
        to: str,
        subject: str,
        html_body: str,
        plain_body: str | None = None,
    ) -> bool:
        """
        Send a single email.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_body: HTML body content.
            plain_body: Plain-text fallback body (optional).

        Returns:
            True if the email was sent (or logged) successfully, False otherwise.
        """
        ...


class ConsoleEmailSender(AbstractEmailSender):
    """
    Development email sender that logs emails to the console.

    Does not actually send emails. Useful for local development and testing
    where you want to verify email content without an SMTP server.
    """

    async def send(
        self,
        to: str,
        subject: str,
        html_body: str,
        plain_body: str | None = None,
    ) -> bool:
        """
        Log email details to the console instead of sending.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_body: HTML body content.
            plain_body: Plain-text fallback body (optional).

        Returns:
            Always returns True (logging never fails).
        """
        logger.info(
            "ConsoleEmailSender: to=%s subject=%s html_length=%d plain_length=%d",
            to,
            subject,
            len(html_body),
            len(plain_body) if plain_body else 0,
        )
        return True


class SmtpEmailSender(AbstractEmailSender):
    """
    Production email sender using aiosmtplib for async SMTP delivery.

    Reads SMTP configuration from FlowSend settings. Actual sending is
    gated behind the ``email_sender_mode=smtp`` feature flag.

    Attributes:
        host: SMTP server hostname.
        port: SMTP server port.
        username: SMTP authentication username.
        password: SMTP authentication password.
        use_tls: Whether to use STARTTLS.
        from_address: Sender email address.
        from_name: Sender display name.
    """

    def __init__(
        self,
        host: str = "",
        port: int = 587,
        username: str = "",
        password: str = "",
        use_tls: bool = True,
        from_address: str = "",
        from_name: str = "",
    ):
        """
        Initialize SMTP sender with connection parameters.

        Args:
            host: SMTP server hostname.
            port: SMTP server port (default 587 for STARTTLS).
            username: SMTP username for authentication.
            password: SMTP password for authentication.
            use_tls: Enable STARTTLS (default True).
            from_address: Sender email address.
            from_name: Sender display name.
        """
        self.host = host or settings.smtp_host
        self.port = port or settings.smtp_port
        self.username = username or settings.smtp_username
        self.password = password or settings.smtp_password
        self.use_tls = use_tls
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
        Send an email via SMTP using aiosmtplib.

        Constructs a multipart MIME message with HTML and optional plain-text
        parts, then sends via the configured SMTP server.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_body: HTML body content.
            plain_body: Plain-text fallback body (optional).

        Returns:
            True if sent successfully, False on failure.
        """
        try:
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            import aiosmtplib

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_address}>"
            msg["To"] = to

            if plain_body:
                msg.attach(MIMEText(plain_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.username or None,
                password=self.password or None,
                start_tls=self.use_tls,
            )
            logger.info("SmtpEmailSender: sent to=%s subject=%s", to, subject)
            return True
        except Exception:
            logger.exception("SmtpEmailSender: failed to send to=%s", to)
            return False


def get_email_sender() -> AbstractEmailSender:
    """
    Factory function returning the appropriate email sender.

    Reads ``settings.email_sender_mode`` to decide which implementation
    to return:
    - "console" (default): Returns ConsoleEmailSender (logs to stdout).
    - "smtp": Returns SmtpEmailSender (real SMTP delivery).

    Returns:
        An AbstractEmailSender instance ready for use.
    """
    if settings.email_sender_mode == "smtp":
        return SmtpEmailSender()
    return ConsoleEmailSender()
