"""
AWS SNS SMS sender for FlowSend.

Sends SMS messages via Amazon Simple Notification Service using aioboto3
for async operations.

For Developers:
    Requires ``aioboto3`` package. Configuration via settings:
    ``sns_region``, ``sns_access_key_id``, ``sns_secret_access_key``.
    Uses SNS ``publish`` API with ``PhoneNumber`` parameter for
    direct SMS delivery (no topic required).

For QA Engineers:
    Mock ``aioboto3.Session`` in tests. The sender returns False on
    any AWS error and logs the exception.

For Project Managers:
    AWS SNS provides cost-effective SMS delivery in 200+ countries.
    Supports transactional and promotional message types.

For End Users:
    Your SMS messages are delivered through Amazon's global mobile
    messaging infrastructure.
"""

import logging

from app.config import settings
from app.services.sms_sender import AbstractSmsSender

logger = logging.getLogger(__name__)


class AwsSnsSmsSender(AbstractSmsSender):
    """
    AWS SNS SMS sender using aioboto3 for async operations.

    Publishes SMS messages directly to phone numbers via the SNS
    ``publish`` API. Does not require an SNS topic.

    Attributes:
        region: AWS region for the SNS endpoint.
        access_key_id: AWS IAM access key ID.
        secret_access_key: AWS IAM secret access key.
    """

    def __init__(
        self,
        region: str = "",
        access_key_id: str = "",
        secret_access_key: str = "",
    ):
        """
        Initialize SNS sender with AWS credentials.

        Args:
            region: AWS region (default from settings).
            access_key_id: AWS access key (default from settings).
            secret_access_key: AWS secret key (default from settings).
        """
        self.region = region or settings.sns_region
        self.access_key_id = access_key_id or settings.sns_access_key_id
        self.secret_access_key = secret_access_key or settings.sns_secret_access_key

    async def send(
        self,
        to: str,
        body: str,
        from_number: str = "",
    ) -> bool:
        """
        Send an SMS via AWS SNS.

        Uses the SNS ``publish`` API with the ``PhoneNumber`` parameter
        for direct SMS delivery without requiring a topic subscription.

        Args:
            to: Recipient phone number in E.164 format.
            body: SMS message body.
            from_number: Ignored for SNS (sender ID set in AWS console).

        Returns:
            True if published successfully, False on failure.
        """
        try:
            import aioboto3

            session = aioboto3.Session(
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region,
            )

            async with session.client("sns") as client:
                response = await client.publish(
                    PhoneNumber=to,
                    Message=body,
                    MessageAttributes={
                        "AWS.SNS.SMS.SMSType": {
                            "DataType": "String",
                            "StringValue": "Transactional",
                        }
                    },
                )
                message_id = response.get("MessageId", "unknown")

            logger.info(
                "AwsSnsSmsSender: sent to=%s message_id=%s",
                to,
                message_id,
            )
            return True
        except Exception:
            logger.exception("AwsSnsSmsSender: failed to send to=%s", to)
            return False
