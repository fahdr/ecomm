"""
SMS sender abstraction for FlowSend.

Provides a pluggable SMS delivery layer mirroring the email sender pattern:
- ConsoleSmsSender: Logs SMS to stdout (development/testing).
- Factory function ``get_sms_sender()`` returns the appropriate sender.

For Developers:
    Always use ``get_sms_sender()`` to obtain a sender instance.
    To add a new provider, subclass ``AbstractSmsSender`` and
    update the factory. Providers are imported lazily to avoid
    requiring optional dependencies.

For QA Engineers:
    Tests should use ConsoleSmsSender (the default). Mock the
    ``send()`` method to verify SMS content.

For Project Managers:
    SMS marketing opens a direct mobile channel alongside email.
    Console mode prevents accidental sends. Switch to "twilio"
    or "sns" for production delivery.

For End Users:
    FlowSend sends SMS messages to your contacts via trusted
    mobile messaging infrastructure with delivery tracking.
"""

import logging
from abc import ABC, abstractmethod

from app.config import settings

logger = logging.getLogger(__name__)


class AbstractSmsSender(ABC):
    """
    Abstract base class for SMS delivery backends.

    All SMS senders must implement the ``send()`` method, which handles
    delivering a single SMS to one recipient.
    """

    @abstractmethod
    async def send(
        self,
        to: str,
        body: str,
        from_number: str = "",
    ) -> bool:
        """
        Send a single SMS message.

        Args:
            to: Recipient phone number in E.164 format (e.g., +15551234567).
            body: SMS message body (max ~1600 chars for concatenated SMS).
            from_number: Sender phone number or short code (optional, uses default).

        Returns:
            True if the SMS was sent successfully, False otherwise.
        """
        ...


class ConsoleSmsSender(AbstractSmsSender):
    """
    Development SMS sender that logs messages to the console.

    Does not actually send SMS. Useful for local development and testing
    where you want to verify message content without a carrier connection.
    """

    async def send(
        self,
        to: str,
        body: str,
        from_number: str = "",
    ) -> bool:
        """
        Log SMS details to the console instead of sending.

        Args:
            to: Recipient phone number.
            body: SMS message body.
            from_number: Sender phone number (ignored in console mode).

        Returns:
            Always returns True (logging never fails).
        """
        logger.info(
            "ConsoleSmsSender: to=%s body_length=%d from=%s",
            to,
            len(body),
            from_number or "default",
        )
        return True


def get_sms_sender() -> AbstractSmsSender:
    """
    Factory function returning the appropriate SMS sender.

    Reads ``settings.sms_provider_mode`` to decide which implementation:
    - "console" (default): Returns ConsoleSmsSender (logs to stdout).
    - "twilio": Returns TwilioSmsSender (Twilio REST API delivery).
    - "sns": Returns AwsSnsSmsSender (AWS SNS delivery).

    Returns:
        An AbstractSmsSender instance ready for use.
    """
    mode = settings.sms_provider_mode
    if mode == "twilio":
        from app.services.twilio_sms_sender import TwilioSmsSender

        return TwilioSmsSender()
    elif mode == "sns":
        from app.services.sns_sms_sender import AwsSnsSmsSender

        return AwsSnsSmsSender()
    return ConsoleSmsSender()
