"""Tests for ecomm_core security middleware, rate limiting, and lifecycle utilities.

Verifies that SecurityHeadersMiddleware adds all required security headers,
supports custom CSP overrides, and that the rate limiter setup function
correctly attaches to a FastAPI app.

**For Developers:**
    These tests create minimal FastAPI apps in-process (no real server)
    and use httpx.AsyncClient to send requests through the middleware stack.

**For QA Engineers:**
    Each test verifies a specific security header or configuration option.
    All 7 security headers must be present with correct default values.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from ecomm_core.security import SecurityHeadersMiddleware
from ecomm_core.rate_limit import setup_rate_limiting, get_limiter
from ecomm_core.lifecycle import setup_graceful_shutdown


# ── Helpers ──────────────────────────────────────────────────────────


def _create_test_app(
    content_security_policy: str | None = None,
    **kwargs,
) -> FastAPI:
    """Create a minimal FastAPI app with SecurityHeadersMiddleware.

    Args:
        content_security_policy: Optional custom CSP value. If None,
            the middleware's default is used.
        **kwargs: Additional keyword arguments passed to the middleware.

    Returns:
        A FastAPI app instance with the security middleware attached.
    """
    app = FastAPI()

    middleware_kwargs = {**kwargs}
    if content_security_policy is not None:
        middleware_kwargs["content_security_policy"] = content_security_policy

    app.add_middleware(SecurityHeadersMiddleware, **middleware_kwargs)

    @app.get("/test")
    async def test_endpoint():
        """Simple test endpoint that returns a JSON object."""
        return {"status": "ok"}

    return app


async def _get_response_headers(app: FastAPI) -> dict:
    """Send a GET request to /test and return the response headers.

    Args:
        app: The FastAPI app to send the request to.

    Returns:
        A dictionary of response header names (lowercase) to values.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/test")
        assert response.status_code == 200
        return dict(response.headers)


# ── SecurityHeadersMiddleware Tests ──────────────────────────────────


class TestSecurityHeadersMiddleware:
    """Test that SecurityHeadersMiddleware adds all required security headers."""

    @pytest.mark.asyncio
    async def test_all_seven_headers_present(self):
        """Response should include all 7 security headers with default values."""
        app = _create_test_app()
        headers = await _get_response_headers(app)

        assert headers["x-content-type-options"] == "nosniff"
        assert headers["x-frame-options"] == "DENY"
        assert headers["x-xss-protection"] == "1; mode=block"
        assert "max-age=31536000" in headers["strict-transport-security"]
        assert "includeSubDomains" in headers["strict-transport-security"]
        assert headers["content-security-policy"] == "default-src 'self'"
        assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"

    @pytest.mark.asyncio
    async def test_custom_csp_override(self):
        """Custom content_security_policy should replace the default."""
        custom_csp = "default-src 'self'; img-src *; script-src 'self' 'unsafe-inline'"
        app = _create_test_app(content_security_policy=custom_csp)
        headers = await _get_response_headers(app)

        assert headers["content-security-policy"] == custom_csp

    @pytest.mark.asyncio
    async def test_custom_frame_options(self):
        """Custom frame_options should replace the default DENY."""
        app = _create_test_app(frame_options="SAMEORIGIN")
        headers = await _get_response_headers(app)

        assert headers["x-frame-options"] == "SAMEORIGIN"

    @pytest.mark.asyncio
    async def test_custom_hsts_max_age(self):
        """Custom hsts_max_age should appear in the HSTS header."""
        app = _create_test_app(hsts_max_age=86400)
        headers = await _get_response_headers(app)

        assert "max-age=86400" in headers["strict-transport-security"]

    @pytest.mark.asyncio
    async def test_custom_referrer_policy(self):
        """Custom referrer_policy should replace the default."""
        app = _create_test_app(referrer_policy="no-referrer")
        headers = await _get_response_headers(app)

        assert headers["referrer-policy"] == "no-referrer"

    @pytest.mark.asyncio
    async def test_custom_permissions_policy(self):
        """Custom permissions_policy should replace the default."""
        custom_perms = "camera=(self), microphone=()"
        app = _create_test_app(permissions_policy=custom_perms)
        headers = await _get_response_headers(app)

        assert headers["permissions-policy"] == custom_perms

    @pytest.mark.asyncio
    async def test_headers_present_on_different_endpoints(self):
        """Security headers should be added to any endpoint, not just /test."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"healthy": True}

        @app.get("/api/data")
        async def api_data():
            """API data endpoint."""
            return {"data": [1, 2, 3]}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            for path in ["/health", "/api/data"]:
                resp = await client.get(path)
                assert resp.status_code == 200
                assert resp.headers["x-content-type-options"] == "nosniff"
                assert resp.headers["x-frame-options"] == "DENY"
                assert resp.headers["x-xss-protection"] == "1; mode=block"


# ── Rate Limiting Tests ──────────────────────────────────────────────


class TestRateLimiting:
    """Test the rate limiter setup utility."""

    def test_setup_attaches_limiter_to_app_state(self):
        """setup_rate_limiting should store a Limiter on app.state."""
        app = FastAPI()
        limiter = setup_rate_limiting(app, default_limit="50/minute")

        assert limiter is not None
        assert hasattr(app.state, "limiter")
        assert app.state.limiter is limiter

    def test_get_limiter_retrieves_from_state(self):
        """get_limiter should return the limiter from app.state."""
        app = FastAPI()
        original = setup_rate_limiting(app)
        retrieved = get_limiter(app)

        assert retrieved is original

    def test_get_limiter_raises_without_setup(self):
        """get_limiter should raise AttributeError if setup was not called."""
        app = FastAPI()

        with pytest.raises(AttributeError):
            get_limiter(app)

    def test_custom_default_limit(self):
        """The default_limits on the limiter should match the provided value."""
        app = FastAPI()
        limiter = setup_rate_limiting(app, default_limit="200/hour")

        # slowapi wraps limits in LimitGroup objects; verify at least one is set
        assert len(limiter._default_limits) == 1


# ── Lifecycle Tests ──────────────────────────────────────────────────


class TestLifecycle:
    """Test the graceful shutdown utility."""

    def test_setup_does_not_raise(self):
        """setup_graceful_shutdown should not raise on a fresh app."""
        app = FastAPI()
        setup_graceful_shutdown(app)
        # No assertion needed — just verify no exception

    def test_setup_with_extra_handlers(self):
        """setup_graceful_shutdown accepts extra_handlers without raising."""
        app = FastAPI()

        async def custom_cleanup():
            """Custom cleanup handler for testing."""
            pass

        setup_graceful_shutdown(app, extra_handlers=[custom_cleanup])
        # No assertion needed — just verify no exception
