"""
Security headers middleware for all ecomm SaaS services.

Adds a comprehensive set of security headers to every HTTP response to protect
against common web vulnerabilities: clickjacking (X-Frame-Options), MIME sniffing
(X-Content-Type-Options), reflected XSS (X-XSS-Protection), protocol downgrade
(Strict-Transport-Security), inline script injection (Content-Security-Policy),
referrer leakage (Referrer-Policy), and device API abuse (Permissions-Policy).

For Developers:
    Add this middleware to any FastAPI app before all other middleware:
        from ecomm_core.security import SecurityHeadersMiddleware
        app.add_middleware(SecurityHeadersMiddleware)

    You can customize the CSP policy with the ``content_security_policy`` parameter:
        app.add_middleware(
            SecurityHeadersMiddleware,
            content_security_policy="default-src 'self'; img-src *",
        )

For QA Engineers:
    Verify every response includes these headers:
        X-Content-Type-Options: nosniff
        X-Frame-Options: DENY
        X-XSS-Protection: 1; mode=block
        Strict-Transport-Security: max-age=31536000; includeSubDomains
        Content-Security-Policy: default-src 'self'
        Referrer-Policy: strict-origin-when-cross-origin
        Permissions-Policy: camera=(), microphone=(), geolocation=()

For Project Managers:
    This middleware is a zero-effort security baseline. Once added, every
    API response automatically includes best-practice security headers,
    reducing the attack surface for all 12 backend services.

For End Users:
    This layer works invisibly behind the scenes to keep your data safe
    by instructing browsers to enforce strict security policies.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that injects security headers into every HTTP response.

    Attributes:
        content_security_policy: CSP directive string. Defaults to ``default-src 'self'``.
        hsts_max_age: HSTS max-age in seconds. Defaults to 31536000 (1 year).
        frame_options: X-Frame-Options value. Defaults to ``DENY``.
        referrer_policy: Referrer-Policy value. Defaults to ``strict-origin-when-cross-origin``.
        permissions_policy: Permissions-Policy value disabling device APIs.

    Args:
        app: The ASGI application to wrap.
        content_security_policy: Override the default CSP directive.
        hsts_max_age: Override the HSTS max-age in seconds.
        frame_options: Override X-Frame-Options (``DENY`` or ``SAMEORIGIN``).
        referrer_policy: Override the Referrer-Policy directive.
        permissions_policy: Override the Permissions-Policy directive.
    """

    def __init__(
        self,
        app,
        content_security_policy: str = "default-src 'self'",
        hsts_max_age: int = 31536000,
        frame_options: str = "DENY",
        referrer_policy: str = "strict-origin-when-cross-origin",
        permissions_policy: str = "camera=(), microphone=(), geolocation=()",
    ):
        """
        Initialize SecurityHeadersMiddleware with configurable header values.

        Args:
            app: The ASGI application to wrap.
            content_security_policy: Content-Security-Policy header value.
            hsts_max_age: Max age in seconds for HSTS header.
            frame_options: X-Frame-Options header value.
            referrer_policy: Referrer-Policy header value.
            permissions_policy: Permissions-Policy header value.
        """
        super().__init__(app)
        self.content_security_policy = content_security_policy
        self.hsts_max_age = hsts_max_age
        self.frame_options = frame_options
        self.referrer_policy = referrer_policy
        self.permissions_policy = permissions_policy

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process the request and inject security headers into the response.

        Args:
            request: The incoming HTTP request.
            call_next: Callable to invoke the next middleware or route handler.

        Returns:
            The HTTP response with security headers added.
        """
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking by denying framing
        response.headers["X-Frame-Options"] = self.frame_options

        # Enable browser-side XSS filtering
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Enforce HTTPS via HSTS
        response.headers["Strict-Transport-Security"] = (
            f"max-age={self.hsts_max_age}; includeSubDomains"
        )

        # Restrict resource loading origins
        response.headers["Content-Security-Policy"] = self.content_security_policy

        # Control referrer information leakage
        response.headers["Referrer-Policy"] = self.referrer_policy

        # Disable access to sensitive browser APIs
        response.headers["Permissions-Policy"] = self.permissions_policy

        return response
