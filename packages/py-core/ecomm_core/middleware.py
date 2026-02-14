"""
Shared middleware factories for ecomm SaaS services.

Provides CORS setup and request logging utilities.

For Developers:
    Use `setup_cors(app, settings)` in your main.py to configure CORS.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


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
