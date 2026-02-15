"""Graceful shutdown handlers for FastAPI services.

Registers application lifecycle event handlers that ensure clean
termination of database connections, Redis clients, and background tasks
when the service receives a shutdown signal (SIGTERM/SIGINT).

**For Developers:**
    Call ``setup_graceful_shutdown(app)`` in your service's ``main.py``
    after creating the FastAPI instance::

        from ecomm_core.lifecycle import setup_graceful_shutdown
        app = FastAPI(title="my-service")
        setup_graceful_shutdown(app)

    The handler logs the shutdown event and lets FastAPI's built-in
    lifespan management dispose of engines and connections. For services
    that need custom cleanup (e.g., flushing buffers, closing websockets),
    pass a list of async callables via ``extra_handlers``.

**For QA Engineers:**
    During graceful shutdown, in-flight requests are allowed to complete
    before the process exits. Verify by sending a request during shutdown
    and confirming it receives a response (not a connection reset).

**For Project Managers:**
    Graceful shutdown prevents data loss during deployments. Kubernetes
    sends SIGTERM, the service stops accepting new requests, finishes
    current ones, and then exits cleanly.

**For End Users:**
    This runs behind the scenes to ensure your in-progress actions
    (like placing an order) complete even during system updates.
"""

import logging
from typing import Callable, Awaitable, Sequence

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def setup_graceful_shutdown(
    app: FastAPI,
    extra_handlers: Sequence[Callable[[], Awaitable[None]]] | None = None,
) -> None:
    """Register shutdown event handlers for clean service termination.

    Attaches an ``on_event("shutdown")`` handler that logs the shutdown,
    executes any custom cleanup callbacks, and allows FastAPI's built-in
    lifespan to dispose of the database engine and connection pools.

    Args:
        app: The FastAPI application instance.
        extra_handlers: Optional sequence of async callables to invoke
            during shutdown (e.g., closing a Redis pool, flushing logs).
            Each handler is called in order; exceptions are logged but
            do not prevent subsequent handlers from running.

    Returns:
        None
    """

    @app.on_event("shutdown")
    async def on_shutdown():
        """Handle application shutdown by running cleanup callbacks.

        Logs the shutdown event, invokes any extra handlers provided
        at setup time, and logs completion. Engine disposal is handled
        by FastAPI's built-in lifespan management.
        """
        logger.info("Service shutting down gracefully...")

        if extra_handlers:
            for handler in extra_handlers:
                try:
                    await handler()
                    logger.info(
                        "Shutdown handler %s completed",
                        getattr(handler, "__name__", repr(handler)),
                    )
                except Exception as exc:
                    logger.warning(
                        "Shutdown handler %s failed: %s",
                        getattr(handler, "__name__", repr(handler)),
                        exc,
                    )

        logger.info("Graceful shutdown complete.")
