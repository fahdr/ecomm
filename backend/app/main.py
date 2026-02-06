"""FastAPI application entry point.

Creates the FastAPI app instance, configures CORS middleware,
and registers all API routers.
All versioned endpoints are mounted under the /api/v1 prefix.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.products import router as products_router
from app.api.public import router as public_router
from app.api.stores import router as stores_router
from app.config import settings

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(stores_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint returning API information.

    Returns:
        dict: A welcome message and a link to the API documentation.
    """
    return {"message": "Dropshipping Platform API", "docs": "/docs"}
