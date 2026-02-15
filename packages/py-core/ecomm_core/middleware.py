"""
Shared middleware factories for ecomm SaaS services.

Provides CORS setup, structured request logging, and request ID tracking.

For Developers:
    Use ``setup_cors(app, settings)`` in your main.py to configure CORS.
    Use ``RequestLoggingMiddleware`` for structured access logs with timing
    and request IDs. The middleware adds an ``X-Request-ID`` header to every
    response so distributed tracing is possible across services.

For QA Engineers:
    Verify that every response includes an ``X-Request-ID`` header.
    Verify that request logs include method, path, status_code, and
    duration_ms fields.

For Project Managers:
    Request logging middleware provides production observability: every
    HTTP request is logged with timing data and a unique correlation ID.
    This makes it possible to trace a single user request across multiple
    services.

For End Users:
    These features are invisible. They help the engineering team monitor
    performance and diagnose issues faster.
"""

import logging
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)


def setup_cors(app: FastAPI, cors_origins: list[str]) -> None:
    """
    Configure CORS middleware on a FastAPI application.

    Args:
        app: The FastAPI application instance.
        cors_origins: List of allowed origin URLs.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every HTTP request with structured data.

    For each request, this middleware:
    1. Generates a unique request ID (UUID4) or reads it from the
       incoming ``X-Request-ID`` header (for upstream propagation).
    2. Records the start time before dispatching to the next handler.
    3. After the response is produced, logs the method, path, status code,
       and elapsed time in milliseconds.
    4. Attaches the ``X-Request-ID`` header to the outgoing response.

    Attributes:
        service_name: Identifier included in every log line to distinguish
            logs from different services in aggregated logging systems.
    """

    def __init__(self, app, service_name: str = "service") -> None:
        """
        Initialize the logging middleware.

        Args:
            app: The ASGI application to wrap.
            service_name: Service identifier for log lines.
        """
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """
        Process a request: assign ID, time it, log it, attach header.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler in the chain.

        Returns:
            The HTTP response with ``X-Request-ID`` header added.
        """
        # Use incoming request ID if provided (e.g. from load balancer),
        # otherwise generate a new one.
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            # Log the failed request before re-raising
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "request_error service=%s method=%s path=%s request_id=%s duration_ms=%.1f",
                self.service_name,
                request.method,
                request.url.path,
                request_id,
                duration_ms,
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Structured log line
        log_method = logger.info if response.status_code < 400 else logger.warning
        log_method(
            "request service=%s method=%s path=%s status=%d duration_ms=%.1f request_id=%s",
            self.service_name,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )

        # Attach request ID to response for downstream correlation
        response.headers["X-Request-ID"] = request_id

        return response
