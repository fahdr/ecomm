"""
Main generation endpoint for the LLM Gateway.

This is the endpoint that all downstream services call to get LLM completions.
It handles routing, caching, rate limiting, cost tracking, and error handling.

For Developers:
    ``POST /api/v1/generate`` accepts a service key header and a JSON body.
    The flow: auth → cache check → rate limit → provider call → log → respond.

For QA Engineers:
    Test with valid/invalid service keys.
    Verify caching (second identical request returns cached=True).
    Verify rate limiting (burst requests return 429).

For Project Managers:
    This single endpoint replaces 8 separate LLM SDK integrations.
    All AI costs flow through here for centralized tracking.
"""

import time

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.providers.base import ProviderError
from app.services import cache_service, cost_service, rate_limit_service, router_service

router = APIRouter()


class GenerateRequest(BaseModel):
    """
    Request schema for LLM generation.

    Attributes:
        user_id: The requesting customer's user ID.
        service: The calling service name.
        task_type: Caller-defined task label for analytics.
        prompt: The user message / prompt text.
        system: Optional system instruction.
        max_tokens: Maximum output tokens.
        temperature: Sampling temperature (0.0 - 2.0).
        json_mode: Whether to request structured JSON output.
    """

    user_id: str
    service: str
    task_type: str = "general"
    prompt: str
    system: str = ""
    max_tokens: int = Field(1000, ge=1, le=8000)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    json_mode: bool = False


class GenerateResponse(BaseModel):
    """
    Response schema for LLM generation.

    Attributes:
        content: The generated text.
        provider: Provider that handled the request.
        model: Model used for generation.
        input_tokens: Input token count.
        output_tokens: Output token count.
        cost_usd: Estimated cost in USD.
        cached: Whether the response came from cache.
        latency_ms: End-to-end latency in milliseconds.
    """

    content: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cached: bool
    latency_ms: int


def _verify_service_key(x_service_key: str = Header(...)) -> str:
    """
    Verify the service authentication key.

    Args:
        x_service_key: The service key from the request header.

    Returns:
        The verified key.

    Raises:
        HTTPException: If the key is invalid.
    """
    if x_service_key != settings.service_key:
        raise HTTPException(status_code=401, detail="Invalid service key")
    return x_service_key


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    body: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(_verify_service_key),
):
    """
    Generate an LLM completion.

    Flow:
    1. Check cache for identical request
    2. Resolve provider and model (check overrides)
    3. Check rate limits for the provider
    4. Call the provider
    5. Calculate cost and log usage
    6. Cache the result
    7. Return response

    Args:
        body: The generation request.
        db: Database session.
        _key: Verified service key.

    Returns:
        GenerateResponse with content, costs, and metadata.
    """
    start_time = time.time()

    # 1. Resolve provider and model
    try:
        provider, model_name = await router_service.resolve_provider(
            db, body.user_id, body.service
        )
    except ProviderError as e:
        raise HTTPException(status_code=503, detail=str(e))

    provider_name = provider.PROVIDER_NAME if hasattr(provider, "PROVIDER_NAME") else "unknown"

    # 2. Check cache
    cached_result = await cache_service.get_cached(
        provider=provider_name,
        model=model_name,
        prompt=body.prompt,
        system=body.system,
        temperature=body.temperature,
        json_mode=body.json_mode,
    )

    if cached_result:
        latency_ms = int((time.time() - start_time) * 1000)
        cost = cost_service.calculate_cost(
            provider_name, model_name, cached_result.input_tokens, cached_result.output_tokens
        )
        await cost_service.log_usage(
            db=db,
            user_id=body.user_id,
            service_name=body.service,
            task_type=body.task_type,
            provider_name=provider_name,
            model_name=model_name,
            input_tokens=cached_result.input_tokens,
            output_tokens=cached_result.output_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            cached=True,
            prompt_preview=body.prompt,
        )
        return GenerateResponse(
            content=cached_result.content,
            provider=provider_name,
            model=model_name,
            input_tokens=cached_result.input_tokens,
            output_tokens=cached_result.output_tokens,
            cost_usd=round(cost, 6),
            cached=True,
            latency_ms=latency_ms,
        )

    # 3. Check rate limit
    allowed = await rate_limit_service.check_rate_limit(provider_name, 60)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for provider '{provider_name}'",
        )

    # 4. Call provider
    try:
        result = await provider.generate(
            prompt=body.prompt,
            system=body.system,
            model=model_name,
            max_tokens=body.max_tokens,
            temperature=body.temperature,
            json_mode=body.json_mode,
        )
    except ProviderError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        await cost_service.log_usage(
            db=db,
            user_id=body.user_id,
            service_name=body.service,
            task_type=body.task_type,
            provider_name=provider_name,
            model_name=model_name,
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            latency_ms=latency_ms,
            error=str(e),
            prompt_preview=body.prompt,
        )
        raise HTTPException(status_code=502, detail=str(e))

    latency_ms = int((time.time() - start_time) * 1000)

    # 5. Calculate cost and log
    cost = cost_service.calculate_cost(
        provider_name, model_name, result.input_tokens, result.output_tokens
    )
    await cost_service.log_usage(
        db=db,
        user_id=body.user_id,
        service_name=body.service,
        task_type=body.task_type,
        provider_name=provider_name,
        model_name=model_name,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=cost,
        latency_ms=latency_ms,
        prompt_preview=body.prompt,
    )

    # 6. Cache result
    await cache_service.set_cached(
        provider=provider_name,
        model=model_name,
        prompt=body.prompt,
        system=body.system,
        temperature=body.temperature,
        json_mode=body.json_mode,
        result=result,
    )

    return GenerateResponse(
        content=result.content,
        provider=provider_name,
        model=model_name,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=round(cost, 6),
        cached=False,
        latency_ms=latency_ms,
    )
