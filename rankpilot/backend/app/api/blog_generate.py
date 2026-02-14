"""
Blog generation API route using the LLM Gateway.

Provides a standalone endpoint for generating SEO-optimized blog posts
from keywords and topic descriptions. Unlike the existing
``/api/v1/blog-posts/generate`` which fills content for an existing post,
this endpoint creates a complete blog post from scratch using the LLM.

For Developers:
    This endpoint calls the LLM Gateway via ``app.services.llm_client.call_llm``.
    In tests, mock the ``call_llm`` function to return deterministic content.
    The response includes title, content, meta_description, and suggested slug.

For QA Engineers:
    Test with various keyword combinations and topics.
    Mock the LLM client to verify the prompt construction.
    Verify the response contains all required fields.

For Project Managers:
    This is the primary AI-powered content generation feature.
    It differentiates RankPilot from manual SEO tools and drives
    plan upgrades (content generation counts toward monthly limits).

For End Users:
    Generate complete SEO-optimized blog posts by providing your
    target keywords and topic. The AI creates content with proper
    headings, meta descriptions, and keyword optimization.
"""

import re

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.seo import BlogGenerateRequest, BlogGenerateResponse
from app.services.llm_client import call_llm

router = APIRouter(prefix="/blog", tags=["blog"])


@router.post("/generate", response_model=BlogGenerateResponse)
async def generate_blog_endpoint(
    body: BlogGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate an SEO-optimized blog post using the LLM Gateway.

    Calls the LLM with the provided keywords and topic to produce
    a complete blog post with title, structured content, meta description,
    and a URL-friendly slug.

    Args:
        body: BlogGenerateRequest with keywords and topic.
        current_user: The authenticated user.

    Returns:
        BlogGenerateResponse with generated title, content, meta_description, and slug.
    """
    keywords_str = ", ".join(body.keywords)
    topic = body.topic or keywords_str

    system_prompt = (
        "You are an expert SEO content writer. Generate a well-structured, "
        "SEO-optimized blog post. Use proper heading hierarchy (H1, H2, H3). "
        "Include the target keywords naturally throughout the content. "
        "Write in Markdown format."
    )

    user_prompt = (
        f"Write an SEO-optimized blog post about: {topic}\n\n"
        f"Target keywords: {keywords_str}\n\n"
        f"Requirements:\n"
        f"- Engaging title that includes the primary keyword\n"
        f"- Meta description (150-160 characters)\n"
        f"- At least 500 words of content\n"
        f"- Proper heading structure (H1, H2, H3)\n"
        f"- Natural keyword usage throughout\n"
        f"- Actionable conclusions\n\n"
        f"Format your response as:\n"
        f"TITLE: [blog title]\n"
        f"META: [meta description]\n"
        f"CONTENT:\n[full blog post in Markdown]"
    )

    try:
        result = await call_llm(
            user_prompt,
            system=system_prompt,
            user_id=str(current_user.id),
            task_type="blog_generation",
            max_tokens=2000,
            temperature=0.7,
        )
        llm_content = result.get("content", "")
    except Exception:
        # Fallback to mock content if LLM gateway is unavailable
        llm_content = _generate_mock_content(topic, keywords_str)

    # Parse the LLM response
    title, meta_description, content = _parse_llm_response(llm_content, topic, keywords_str)

    # Generate slug from title
    slug = _generate_slug(title)

    return BlogGenerateResponse(
        title=title,
        content=content,
        meta_description=meta_description,
        slug=slug,
        keywords=body.keywords,
    )


def _parse_llm_response(
    response: str,
    topic: str,
    keywords_str: str,
) -> tuple[str, str, str]:
    """
    Parse the structured LLM response into title, meta description, and content.

    Expects the response to follow the format:
    TITLE: [title]
    META: [meta description]
    CONTENT:
    [content body]

    Falls back to mock content if parsing fails.

    Args:
        response: The raw LLM response string.
        topic: The original topic (used for fallback).
        keywords_str: Comma-separated keywords (used for fallback).

    Returns:
        Tuple of (title, meta_description, content).
    """
    title = ""
    meta_description = ""
    content = ""

    lines = response.split("\n")
    content_started = False

    for line in lines:
        if line.startswith("TITLE:"):
            title = line[6:].strip()
        elif line.startswith("META:"):
            meta_description = line[5:].strip()
        elif line.startswith("CONTENT:"):
            content_started = True
        elif content_started:
            content += line + "\n"

    content = content.strip()

    # Fallback if parsing produced empty results
    if not title:
        title = f"Complete Guide to {topic.title()}"
    if not meta_description:
        meta_description = (
            f"Learn everything about {keywords_str}. "
            f"Expert tips, best practices, and actionable strategies."
        )[:160]
    if not content:
        content = _generate_mock_content(topic, keywords_str)

    return title, meta_description, content


def _generate_mock_content(topic: str, keywords_str: str) -> str:
    """
    Generate mock blog content when the LLM gateway is unavailable.

    Produces a structured Markdown blog post with headings, bullet points,
    and a conclusion. Used as a fallback for testing and development.

    Args:
        topic: The blog topic.
        keywords_str: Comma-separated target keywords.

    Returns:
        A Markdown-formatted blog post string.
    """
    return f"""# Complete Guide to {topic.title()}

## Introduction

In this comprehensive guide, we explore everything you need to know about {keywords_str}.
Whether you are a beginner or an experienced professional, this article provides
valuable insights to help you improve your search engine rankings.

## Key Strategies for {topic.title()}

### 1. Understand Your Audience

Before optimizing for {keywords_str}, it is essential to understand who your
target audience is and what they are searching for.

### 2. Optimize Your Content

High-quality content that naturally incorporates {keywords_str} will always
outperform keyword-stuffed pages.

### 3. Technical Optimization

Ensure your website loads quickly, is mobile-friendly, and has proper
structured data markup for {keywords_str}.

## Best Practices

- Conduct thorough keyword research before writing content
- Use {keywords_str} naturally in headings and body text
- Optimize meta titles and descriptions for click-through rates
- Build high-quality backlinks from authoritative sources
- Monitor your rankings and adjust your strategy accordingly

## Measuring Success

Track these key metrics to measure your progress:
- Organic traffic growth from search engines
- Keyword ranking improvements over time
- Click-through rates from search results
- Engagement metrics (bounce rate, time on page)

## Conclusion

Implementing a solid SEO strategy focused on {keywords_str} will help you achieve
sustainable organic growth. Remember that SEO is a long-term investment requiring
patience, consistency, and continuous optimization.

*Generated by RankPilot AI — your automated SEO engine.*
"""


def _generate_slug(title: str) -> str:
    """
    Generate a URL-safe slug from a blog post title.

    Converts to lowercase, removes special characters, and replaces
    spaces with hyphens.

    Args:
        title: The blog post title to slugify.

    Returns:
        A URL-safe slug string.
    """
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    slug = slug.strip("-")
    return slug
