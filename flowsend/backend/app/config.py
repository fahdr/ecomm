"""
FlowSend application configuration.

Extends the shared BaseServiceConfig with FlowSend-specific defaults.

For Developers:
    Only add service-specific settings here. Common settings (JWT, DB,
    Redis, Stripe, CORS) are inherited from BaseServiceConfig.

For QA Engineers:
    Override settings via environment variables in test fixtures.
"""

from ecomm_core.config import BaseServiceConfig


class Settings(BaseServiceConfig):
    """
    FlowSend-specific configuration extending shared base.

    Adds settings for email sending (SMTP), the LLM Gateway integration,
    and store connection management.

    For Developers:
        Override via environment variables (e.g., SMTP_HOST=smtp.example.com).
        LLM Gateway settings inherit from BaseServiceConfig (llm_gateway_url,
        llm_gateway_key) and are used by the llm_client module.

    For QA Engineers:
        Set email_sender_mode="console" (default) for test runs.
        SMTP mode requires a running mail server.

    For Project Managers:
        Email sending is gated behind email_sender_mode. Console mode logs
        emails without sending; switch to "smtp" for production delivery.
    """

    service_name: str = "flowsend"
    service_display_name: str = "FlowSend"
    service_port: int = 8104
    cors_origins: str = "http://localhost:3104"
    stripe_billing_success_url: str = "http://localhost:3104/billing?success=true"
    stripe_billing_cancel_url: str = "http://localhost:3104/billing?canceled=true"
    anthropic_api_key: str = ""

    # Email sending
    email_sender_mode: str = "console"  # "console" or "smtp"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    email_from_address: str = "noreply@flowsend.app"
    email_from_name: str = "FlowSend"

    # Store connection defaults
    store_api_timeout: float = 30.0


settings = Settings()
