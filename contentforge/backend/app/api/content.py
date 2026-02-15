"""
Content generation API endpoints.

Provides CRUD operations for generation jobs and generated content.
Supports single and bulk generation from URLs, CSV, or manual input.

For Developers:
    All endpoints require authentication via `get_current_user` dependency.
    Generation jobs are processed asynchronously via Celery tasks (or
    synchronously in mock mode for testing).

    The `POST /generate` endpoint creates the job and immediately processes
    it (synchronous mode). In production with Celery, it would dispatch
    a task and return the pending job.

For QA Engineers:
    Test the full generation lifecycle:
    - POST /generate with manual data -> job created with status "completed"
    - GET /jobs -> paginated list includes the new job
    - GET /jobs/{id} -> returns job with content_items populated
    - PATCH /content/{id} -> updates content text
    - DELETE /jobs/{id} -> removes job and all content
    - POST /generate/bulk with URLs -> creates multiple jobs
    - Verify plan limits are enforced (403 when exceeded)

For Project Managers:
    These endpoints power the "Generate" page in the dashboard. Each
    generation consumes one monthly credit from the user's plan quota.

For End Users:
    Use the Generate page to create AI-optimized product content.
    You can generate from a product URL, enter details manually, or
    upload a CSV file for bulk generation.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.store_connection import StoreConnection
from app.schemas.content import (
    ABVariantRequest,
    ABVariantResponse,
    BulkGenerationRequest,
    BulkGenerationStatusResponse,
    BulkGenerationV2Request,
    ExportContentRequest,
    ExportContentResponse,
    GeneratedContentResponse,
    GeneratedContentUpdate,
    GenerationJobCreate,
    GenerationJobResponse,
    PaginatedGenerationJobs,
)
from app.services.content_service import (
    create_generation_job,
    delete_generation_job,
    generate_ab_variants,
    generate_content,
    get_generation_job,
    get_generation_jobs,
    process_generation,
    update_generated_content,
)

router = APIRouter(prefix="/content", tags=["content"])


@router.post("/generate", response_model=GenerationJobResponse, status_code=201)
async def create_generation(
    request: GenerationJobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a content generation job.

    Creates a new generation job from the provided source data (URL, manual,
    or CSV). The job is processed synchronously in mock mode or dispatched
    to Celery in production mode.

    Args:
        request: Generation job parameters (source data, template, content types).
        current_user: The authenticated user (injected via dependency).
        db: Database session.

    Returns:
        GenerationJobResponse with job details and generated content.

    Raises:
        HTTPException 403: If the user has exceeded their monthly generation limit.
        HTTPException 400: If the request data is invalid.
    """
    try:
        job = await create_generation_job(
            db,
            current_user,
            {
                "source_url": request.source_url,
                "source_type": request.source_type,
                "source_data": {
                    **request.source_data,
                    "content_types": request.content_types,
                },
                "template_id": request.template_id,
                "image_urls": request.image_urls,
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    # Process synchronously (in production, dispatch Celery task)
    await process_generation(db, job.id)

    # Refresh to get updated content
    updated_job = await get_generation_job(db, job.id)
    return updated_job


@router.post(
    "/generate/bulk",
    response_model=list[GenerationJobResponse],
    status_code=201,
)
async def create_bulk_generation(
    request: BulkGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create multiple generation jobs from a list of URLs or CSV data.

    Each URL or CSV row creates a separate generation job. All jobs
    use the same template and content type settings.

    Args:
        request: Bulk generation parameters (URLs or CSV, template, content types).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of GenerationJobResponse for all created jobs.

    Raises:
        HTTPException 400: If neither URLs nor CSV data are provided.
        HTTPException 403: If the user would exceed their plan limit.
    """
    if not request.urls and not request.csv_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either urls or csv_data for bulk generation.",
        )

    jobs = []

    # Process URLs
    for url in request.urls:
        try:
            job = await create_generation_job(
                db,
                current_user,
                {
                    "source_url": url,
                    "source_type": "url",
                    "source_data": {
                        "url": url,
                        "content_types": request.content_types,
                    },
                    "template_id": request.template_id,
                    "image_urls": [],
                },
            )
            await process_generation(db, job.id)
            updated = await get_generation_job(db, job.id)
            if updated:
                jobs.append(updated)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )

    # Process CSV data
    if request.csv_data:
        import csv
        import io

        reader = csv.DictReader(io.StringIO(request.csv_data))
        for row in reader:
            try:
                job = await create_generation_job(
                    db,
                    current_user,
                    {
                        "source_url": None,
                        "source_type": "csv",
                        "source_data": {
                            **dict(row),
                            "content_types": request.content_types,
                        },
                        "template_id": request.template_id,
                        "image_urls": [],
                    },
                )
                await process_generation(db, job.id)
                updated = await get_generation_job(db, job.id)
                if updated:
                    jobs.append(updated)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=str(e),
                )

    return jobs


@router.get("/jobs", response_model=PaginatedGenerationJobs)
async def list_generation_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List the current user's generation jobs with pagination.

    Jobs are ordered by creation date (newest first). Each job includes
    its content items and image items via eager loading.

    Args:
        page: Page number (1-indexed, default 1).
        per_page: Number of items per page (default 20, max 100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        PaginatedGenerationJobs with items, total, page, per_page.
    """
    result = await get_generation_jobs(db, current_user.id, page, per_page)
    return result


@router.get("/jobs/{job_id}", response_model=GenerationJobResponse)
async def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single generation job with all generated content and images.

    Args:
        job_id: The generation job UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        GenerationJobResponse with full content and image data.

    Raises:
        HTTPException 404: If the job is not found or not owned by the user.
    """
    job = await get_generation_job(db, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job not found.",
        )
    return job


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a generation job and all its content and image records.

    Args:
        job_id: The generation job UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If the job is not found or not owned by the user.
    """
    deleted = await delete_generation_job(db, job_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job not found.",
        )


@router.patch(
    "/{content_id}",
    response_model=GeneratedContentResponse,
)
async def edit_content(
    content_id: uuid.UUID,
    request: GeneratedContentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Edit the text of a generated content record.

    Allows the user to manually adjust AI-generated content while preserving
    the record in the generation history.

    Args:
        content_id: The generated content UUID.
        request: Updated content text.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        GeneratedContentResponse with updated content.

    Raises:
        HTTPException 404: If the content is not found or not owned by the user.
    """
    content = await update_generated_content(
        db, content_id, current_user.id, request.content
    )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found.",
        )
    return content


# ── Bulk Generation v2 ───────────────────────────────────────────────


@router.post(
    "/bulk",
    response_model=BulkGenerationStatusResponse,
    status_code=201,
)
async def create_bulk_generation_v2(
    request: BulkGenerationV2Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk generate content for multiple products (v2).

    Accepts a list of product data dicts or a connection_id to pull
    products from a connected store. Creates a generation job for each
    product and processes them all.

    Args:
        request: Bulk generation parameters (products, connection_id,
            template_name, content_types).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        BulkGenerationStatusResponse with job count and results.

    Raises:
        HTTPException 400: If no products or connection_id provided.
        HTTPException 404: If the connection_id is not found.
        HTTPException 403: If plan limits are exceeded.
    """
    products = list(request.products)

    # If connection_id provided, load products from connected store (mock)
    if request.connection_id:
        conn_result = await db.execute(
            select(StoreConnection).where(
                StoreConnection.id == request.connection_id,
                StoreConnection.user_id == current_user.id,
            )
        )
        connection = conn_result.scalar_one_or_none()
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store connection not found.",
            )
        # Mock: simulate pulling products from the connected store
        if not products:
            products = [
                {"name": f"Store Product {i + 1}", "price": f"{19.99 + i * 10:.2f}"}
                for i in range(3)
            ]

    if not products:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either products list or a connection_id.",
        )

    jobs = []
    errors = []

    for idx, product in enumerate(products):
        try:
            job = await create_generation_job(
                db,
                current_user,
                {
                    "source_url": None,
                    "source_type": "manual",
                    "source_data": {
                        **product,
                        "content_types": request.content_types,
                        "template_name": request.template_name,
                    },
                    "template_id": None,
                    "image_urls": [],
                },
            )
            await process_generation(db, job.id)
            updated = await get_generation_job(db, job.id)
            if updated:
                jobs.append(updated)
        except ValueError as e:
            errors.append(f"Product {idx + 1}: {str(e)}")
            break  # Stop on plan limit errors

    return BulkGenerationStatusResponse(
        total_products=len(products),
        jobs_created=len(jobs),
        jobs=jobs,
        errors=errors,
    )


# ── Export to Store ──────────────────────────────────────────────────


@router.post(
    "/{job_id}/export",
    response_model=ExportContentResponse,
)
async def export_content_to_store(
    job_id: uuid.UUID,
    request: ExportContentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export generated content to a connected store.

    Pushes the generated content from a completed job to a specific
    product in the connected Shopify/WooCommerce store.

    In the current implementation this simulates the export. In production
    it would call the store's API to update the product listing.

    Args:
        job_id: The generation job UUID containing the content to export.
        request: Export parameters (connection_id, product_id, field_mapping).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        ExportContentResponse with export status.

    Raises:
        HTTPException 404: If the job or connection is not found.
        HTTPException 400: If the job has no completed content.
    """
    # Verify job ownership
    job = await get_generation_job(db, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job not found.",
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job must be completed before exporting.",
        )

    # Verify connection ownership
    conn_result = await db.execute(
        select(StoreConnection).where(
            StoreConnection.id == request.connection_id,
            StoreConnection.user_id == current_user.id,
        )
    )
    connection = conn_result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store connection not found.",
        )

    # Collect content types from the job
    fields_updated = [item.content_type for item in job.content_items]

    # Mock export (in production: call store API to update product)
    return ExportContentResponse(
        success=True,
        job_id=job_id,
        connection_id=request.connection_id,
        product_id=request.product_id,
        fields_updated=fields_updated,
        message=(
            f"Successfully exported {len(fields_updated)} content fields "
            f"to {connection.platform} product {request.product_id}"
        ),
    )


# ── A/B Variant Generation ──────────────────────────────────────────


@router.post(
    "/ab-variants",
    response_model=ABVariantResponse,
    status_code=201,
)
async def generate_ab_test_variants(
    request: ABVariantRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate A/B test content variants for split-testing.

    Produces multiple distinct versions of a single content type for the
    given product, allowing users to test which version performs better
    on their store.

    Args:
        request: A/B variant parameters (product_data, content_type,
            template_name, count).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        ABVariantResponse with list of variant content strings.
    """
    variants = await generate_ab_variants(
        db=db,
        user_id=current_user.id,
        product_data=request.product_data,
        content_type=request.content_type,
        template_name=request.template_name,
        count=request.count,
    )

    return ABVariantResponse(
        content_type=request.content_type,
        variants=variants,
        template_name=request.template_name,
    )
