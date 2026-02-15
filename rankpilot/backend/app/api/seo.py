"""
SEO utility API routes for sitemap generation and page analysis.

Provides endpoints for generating XML sitemaps and analyzing individual
pages for SEO factors. These are standalone tools that complement the
full site audit feature.

For Developers:
    The sitemap endpoint accepts a list of URL objects and returns XML.
    The page analysis endpoint fetches a URL and returns SEO scores.
    Both require authentication.

For QA Engineers:
    Test sitemap generation with various URL counts and optional fields.
    Test page analysis with mock HTTP responses (do not hit real URLs).

For Project Managers:
    These tools provide instant value to users — they can generate
    sitemaps and analyze pages without waiting for a full audit.

For End Users:
    Generate XML sitemaps for your website and analyze individual
    pages to see detailed SEO scores and recommendations.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.seo import (
    PageAnalysisResponse,
    SitemapGenerateRequest,
    PageAnalyzeRequest,
)
from app.services.sitemap_service import generate_xml_sitemap
from app.services.audit_service import analyze_page, analyze_page_html

router = APIRouter(prefix="/seo", tags=["seo"])


@router.post("/sitemap/generate")
async def generate_sitemap_endpoint(
    body: SitemapGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate an XML sitemap from a list of URLs.

    Accepts a list of URL objects with optional lastmod, changefreq,
    and priority fields. Returns a valid XML sitemap document.

    Args:
        body: SitemapGenerateRequest with a list of URL entries.
        current_user: The authenticated user.

    Returns:
        XML sitemap as application/xml response.
    """
    url_dicts = [u.model_dump() for u in body.urls]
    xml_content = generate_xml_sitemap(url_dicts)
    return Response(
        content=xml_content,
        media_type="application/xml",
    )


@router.post("/analyze", response_model=PageAnalysisResponse)
async def analyze_page_endpoint(
    body: PageAnalyzeRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Analyze a single web page for SEO factors.

    Fetches the page at the given URL, parses the HTML, and returns
    detailed SEO scores, extracted elements, and actionable issues.

    Args:
        body: PageAnalyzeRequest with the URL to analyze.
        current_user: The authenticated user.

    Returns:
        PageAnalysisResponse with scores, extracted data, and issues.

    Raises:
        HTTPException 400: If the URL cannot be fetched.
    """
    try:
        analysis = await analyze_page(body.url)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not analyze page: {str(e)}",
        )

    return PageAnalysisResponse(
        url=analysis.url,
        title=analysis.title,
        meta_description=analysis.meta_description,
        h1_tags=analysis.h1_tags,
        h2_tags=analysis.h2_tags,
        h3_tags=analysis.h3_tags,
        images_without_alt=analysis.images_without_alt,
        internal_link_count=len(analysis.internal_links),
        external_link_count=len(analysis.external_links),
        word_count=analysis.word_count,
        canonical_url=analysis.canonical_url,
        og_tags=analysis.og_tags,
        meta_score=analysis.meta_score,
        content_score=analysis.content_score,
        technical_score=analysis.technical_score,
        mobile_score=analysis.mobile_score,
        performance_score=analysis.performance_score,
        overall_score=analysis.overall_score,
        issues=analysis.issues,
    )
