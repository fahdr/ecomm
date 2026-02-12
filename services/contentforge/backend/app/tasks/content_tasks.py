"""
Celery tasks for asynchronous content generation processing.

These tasks run in background workers to process generation jobs without
blocking the API server. In mock mode (testing), generation is done
synchronously in the API handler instead.

For Developers:
    The `process_generation_job` task is dispatched after a GenerationJob
    is created. It creates a synchronous database session (Celery workers
    cannot use async), loads the job, generates content using mock AI,
    and updates the job status.

    To dispatch: `process_generation_job.delay(str(job_id))`

    The task is registered with the service-specific queue via
    celery_app.conf.task_default_queue.

For QA Engineers:
    In test mode, tasks are not dispatched — generation is synchronous.
    To test Celery integration manually, run the worker and POST to
    /api/v1/content/generate, then poll GET /api/v1/content/jobs/{id}
    until status is "completed".

For Project Managers:
    Background processing ensures the API remains responsive during
    content generation. Users see immediate feedback (job created with
    "pending" status) and can check back for results.
"""

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="app.tasks.content_tasks.process_generation_job")
def process_generation_job(self, job_id: str) -> dict:
    """
    Process a content generation job in the background.

    Creates a synchronous database session, loads the job, generates
    content for all requested types, processes images, and marks the
    job as completed (or failed on error).

    This task uses synchronous SQLAlchemy because Celery workers do not
    natively support asyncio. The sync session connects via the sync
    database URL.

    Args:
        job_id: The generation job UUID as a string.

    Returns:
        Dict with job_id and final status.
    """
    import uuid
    from datetime import UTC, datetime

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.config import settings
    from app.models.generation import GeneratedContent, GenerationJob
    from app.models.image_job import ImageJob
    from app.models.template import Template
    from app.services.content_service import generate_mock_content

    engine = create_engine(settings.database_url_sync)

    with Session(engine) as db:
        try:
            # Load job
            job = db.execute(
                select(GenerationJob).where(
                    GenerationJob.id == uuid.UUID(job_id)
                )
            ).scalar_one_or_none()

            if not job:
                return {"job_id": job_id, "status": "not_found"}

            job.status = "processing"
            db.commit()

            # Determine template settings
            tone = "professional"
            style = "detailed"
            content_types = [
                "title",
                "description",
                "meta_description",
                "keywords",
                "bullet_points",
            ]

            if job.template_id:
                template = db.execute(
                    select(Template).where(Template.id == job.template_id)
                ).scalar_one_or_none()
                if template:
                    tone = template.tone
                    style = template.style
                    content_types = template.content_types

            # Override with source_data content_types if present
            if "content_types" in job.source_data:
                content_types = job.source_data["content_types"]

            # Generate content for each type
            product_data = dict(job.source_data)
            for ct in content_types:
                text = generate_mock_content(product_data, ct, tone, style)
                content_record = GeneratedContent(
                    job_id=job.id,
                    content_type=ct,
                    content=text,
                    version=1,
                    word_count=len(text.split()),
                )
                db.add(content_record)

            # Process images (mock)
            images = db.execute(
                select(ImageJob).where(ImageJob.job_id == job.id)
            ).scalars().all()

            for img in images:
                img.status = "completed"
                img.optimized_url = img.original_url.replace(".", "_optimized.", 1)
                img.format = "webp"
                img.width = 800
                img.height = 600
                img.size_bytes = 45_000

            job.status = "completed"
            job.completed_at = datetime.now(UTC)
            db.commit()

            return {"job_id": job_id, "status": "completed"}

        except Exception as e:
            db.rollback()
            # Mark job as failed
            try:
                job = db.execute(
                    select(GenerationJob).where(
                        GenerationJob.id == uuid.UUID(job_id)
                    )
                ).scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.error_message = str(e)
                    job.completed_at = datetime.now(UTC)
                    db.commit()
            except Exception:
                pass

            return {"job_id": job_id, "status": "failed", "error": str(e)}
