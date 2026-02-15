"""
AWS SES email sender for FlowSend.

Sends emails via Amazon Simple Email Service using aioboto3 for async
operations. Falls back to console logging if AWS credentials are missing.

For Developers:
    Requires ``aioboto3`` package. Configuration via settings:
    ``ses_region``, ``ses_access_key_id``, ``ses_secret_access_key``.
    The sender uses SES ``send_raw_email`` for full MIME control.

For QA Engineers:
    Mock ``aioboto3.Session`` in tests. The sender returns False on
    any AWS error and logs the exception.

For Project Managers:
    SES is the most cost-effective email provider for high-volume sends.
    Requires verified sender domains in the AWS SES console.

For End Users:
    Your emails are delivered through Amazon's enterprise email
    infrastructure with industry-leading deliverability.
"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings
from app.services.email_sender import AbstractEmailSender

logger = logging.getLogger(__name__)


class SesEmailSender(AbstractEmailSender):
    """
    AWS SES email sender using aioboto3 for async operations.

    Constructs a MIME message and sends via SES ``send_raw_email`` API.
    Supports HTML with optional plain-text fallback.

    Attributes:
        region: AWS region for the SES endpoint (e.g., ``us-east-1``).
        access_key_id: AWS IAM access key ID.
        secret_access_key: AWS IAM secret access key.
        from_address: Verified SES sender email address.
        from_name: Sender display name.
        configuration_set: Optional SES configuration set for event tracking.
    """

    def __init__(
        self,
        region: str = "",
        access_key_id: str = "",
        secret_access_key: str = "",
        from_address: str = "",
        from_name: str = "",
        configuration_set: str = "",
    ):
        """
        Initialize SES sender with AWS credentials.

        Args:
            region: AWS region (default from settings).
            access_key_id: AWS access key (default from settings).
            secret_access_key: AWS secret key (default from settings).
            from_address: Sender email (default from settings).
            from_name: Sender display name (default from settings).
            configuration_set: SES configuration set name (default from settings).
        """
        self.region = region or settings.ses_region
        self.access_key_id = access_key_id or settings.ses_access_key_id
        self.secret_access_key = secret_access_key or settings.ses_secret_access_key
        self.from_address = from_address or settings.email_from_address
        self.from_name = from_name or settings.email_from_name
        self.configuration_set = configuration_set or settings.ses_configuration_set

    async def send(
        self,
        to: str,
        subject: str,
        html_body: str,
        plain_body: str | None = None,
    ) -> bool:
        """
        Send an email via AWS SES.

        Constructs a multipart MIME message and sends it using the SES
        ``send_raw_email`` API through aioboto3.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_body: HTML body content.
            plain_body: Plain-text fallback body (optional).

        Returns:
            True if sent successfully, False on failure.
        """
        try:
            import aioboto3

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_address}>"
            msg["To"] = to

            if plain_body:
                msg.attach(MIMEText(plain_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            session = aioboto3.Session(
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region,
            )

            async with session.client("ses") as client:
                kwargs = {
                    "Source": msg["From"],
                    "Destinations": [to],
                    "RawMessage": {"Data": msg.as_string()},
                }
                if self.configuration_set:
                    kwargs["ConfigurationSetName"] = self.configuration_set

                await client.send_raw_email(**kwargs)

            logger.info("SesEmailSender: sent to=%s subject=%s", to, subject)
            return True
        except Exception:
            logger.exception("SesEmailSender: failed to send to=%s", to)
            return False
