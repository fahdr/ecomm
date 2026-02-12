"""
Tests for blog post API endpoints.

Covers the full CRUD lifecycle for blog posts, including creation with
plan limits, listing with optional site filters, AI content generation,
status transitions, and deletion.

For Developers:
    Blog posts require a parent site. Each test creates a fresh site
    before creating posts. The `auth_headers` fixture provides JWT auth.
    Plan limits are enforced: free tier allows 2 posts/month.

For QA Engineers:
    These tests verify:
    - Create blog post returns 201 with title, slug, status='draft', and word_count.
    - List posts returns paginated results with optional site_id filter.
    - Get post by ID returns 200 or 404 for invalid IDs.
    - Update post modifies title, content, status, and keywords.
    - Publishing a post transitions status to 'published'.
    - Delete post returns 204 and removes it.
    - AI generate fills in content and meta_description.
    - Cross-user post access is blocked.

For Project Managers:
    Blog posts are a primary plan differentiator. AI generation is the
    key feature that drives upgrades from free to paid plans.
"""

import uuid

import pytest
from httpx import AsyncClient


# ── Helpers ────────────────────────────────────────────────────────────────


async def create_test_site(
    client: AsyncClient,
    auth_headers: dict,
    domain: str = "blog-test.com",
) -> dict:
    """
    Create a site for blog post testing and return the response body.

    Args:
        client: The test HTTP client.
        auth_headers: Authorization header dict.
        domain: The domain name for the site.

    Returns:
        The created site as a dict (SiteResponse).
    """
    resp = await client.post(
        "/api/v1/sites",
        json={"domain": domain},
        headers=auth_headers,
    )
    assert resp.status_code == 201, f"Site creation failed: {resp.text}"
    return resp.json()


async def create_test_blog_post(
    client: AsyncClient,
    auth_headers: dict,
    site_id: str,
    title: str = "Test Blog Post",
    content: str | None = None,
    meta_description: str | None = None,
    keywords: list[str] | None = None,
) -> dict:
    """
    Create a blog post via the API and return the response body.

    Args:
        client: The test HTTP client.
        auth_headers: Authorization header dict.
        site_id: UUID of the parent site.
        title: The blog post title.
        content: Optional post content.
        meta_description: Optional SEO meta description.
        keywords: Optional list of target keywords.

    Returns:
        The created blog post as a dict (BlogPostResponse).
    """
    payload: dict = {"site_id": site_id, "title": title}
    if content is not None:
        payload["content"] = content
    if meta_description is not None:
        payload["meta_description"] = meta_description
    if keywords is not None:
        payload["keywords"] = keywords

    resp = await client.post(
        "/api/v1/blog-posts",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 201, f"Blog post creation failed: {resp.text}"
    return resp.json()


# ── Create Blog Post Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_blog_post_basic(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/blog-posts creates a post with correct fields."""
    site = await create_test_site(client, auth_headers, domain="create-blog.com")

    data = await create_test_blog_post(
        client, auth_headers, site["id"], title="My First SEO Post"
    )

    assert data["title"] == "My First SEO Post"
    assert data["site_id"] == site["id"]
    assert data["status"] == "draft"
    assert "id" in data
    assert "slug" in data
    assert "user_id" in data
    assert "word_count" in data
    assert "created_at" in data
    assert isinstance(data["keywords"], list)


@pytest.mark.asyncio
async def test_create_blog_post_with_content(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/blog-posts with content stores the content and calculates word_count."""
    site = await create_test_site(client, auth_headers, domain="content-blog.com")

    content = "This is a test blog post with some content for SEO purposes."
    data = await create_test_blog_post(
        client,
        auth_headers,
        site["id"],
        title="Content Post",
        content=content,
    )

    assert data["content"] == content
    assert data["word_count"] > 0


@pytest.mark.asyncio
async def test_create_blog_post_with_keywords(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/blog-posts with keywords stores the keyword list."""
    site = await create_test_site(client, auth_headers, domain="kw-blog.com")

    data = await create_test_blog_post(
        client,
        auth_headers,
        site["id"],
        title="Keyword Post",
        keywords=["seo", "rankings", "backlinks"],
    )

    assert data["keywords"] == ["seo", "rankings", "backlinks"]


@pytest.mark.asyncio
async def test_create_blog_post_with_meta_description(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/blog-posts with meta_description stores it."""
    site = await create_test_site(client, auth_headers, domain="meta-blog.com")

    data = await create_test_blog_post(
        client,
        auth_headers,
        site["id"],
        title="Meta Post",
        meta_description="A great meta description for SEO.",
    )

    assert data["meta_description"] == "A great meta description for SEO."


@pytest.mark.asyncio
async def test_create_blog_post_nonexistent_site(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/blog-posts with a non-existent site_id returns 404."""
    fake_site_id = str(uuid.uuid4())

    resp = await client.post(
        "/api/v1/blog-posts",
        json={"site_id": fake_site_id, "title": "Orphan Post"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_blog_post_unauthenticated(client: AsyncClient):
    """POST /api/v1/blog-posts without auth returns 401."""
    resp = await client.post(
        "/api/v1/blog-posts",
        json={"site_id": str(uuid.uuid4()), "title": "No Auth Post"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_blog_post_empty_title(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/blog-posts with an empty title returns 422."""
    site = await create_test_site(client, auth_headers, domain="empty-title.com")

    resp = await client.post(
        "/api/v1/blog-posts",
        json={"site_id": site["id"], "title": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ── List Blog Posts Tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_blog_posts_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/blog-posts with no posts returns an empty paginated response."""
    resp = await client.get("/api/v1/blog-posts", headers=auth_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_blog_posts_returns_created(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/blog-posts returns posts that were previously created."""
    site = await create_test_site(client, auth_headers, domain="list-blog.com")

    await create_test_blog_post(client, auth_headers, site["id"], title="Post One")
    await create_test_blog_post(client, auth_headers, site["id"], title="Post Two")

    resp = await client.get("/api/v1/blog-posts", headers=auth_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] == 2
    titles = {item["title"] for item in data["items"]}
    assert "Post One" in titles
    assert "Post Two" in titles


@pytest.mark.asyncio
async def test_list_blog_posts_filter_by_site(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/blog-posts with site_id filter returns only matching posts."""
    site1 = await create_test_site(client, auth_headers, domain="blog-filter-a.com")
    site2 = await create_test_site(client, auth_headers, domain="blog-filter-b.com")

    await create_test_blog_post(client, auth_headers, site1["id"], title="Site1 Post")
    await create_test_blog_post(client, auth_headers, site2["id"], title="Site2 Post")

    resp = await client.get(
        "/api/v1/blog-posts",
        params={"site_id": site1["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Site1 Post"


@pytest.mark.asyncio
async def test_list_blog_posts_pagination(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/blog-posts respects page and per_page parameters."""
    site = await create_test_site(client, auth_headers, domain="paginate-blog.com")

    # Free plan limit is 2, so we create exactly 2
    await create_test_blog_post(client, auth_headers, site["id"], title="Page Post 1")
    await create_test_blog_post(client, auth_headers, site["id"], title="Page Post 2")

    resp = await client.get(
        "/api/v1/blog-posts",
        params={"page": 1, "per_page": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert len(data["items"]) == 1
    assert data["total"] == 2
    assert data["per_page"] == 1


# ── Get Blog Post by ID Tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_blog_post_by_id(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/blog-posts/{id} returns the correct post."""
    site = await create_test_site(client, auth_headers, domain="get-blog.com")
    post = await create_test_blog_post(client, auth_headers, site["id"], title="Get This Post")

    resp = await client.get(f"/api/v1/blog-posts/{post['id']}", headers=auth_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["id"] == post["id"]
    assert data["title"] == "Get This Post"


@pytest.mark.asyncio
async def test_get_blog_post_not_found(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/blog-posts/{id} with a non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/blog-posts/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_blog_post_other_user(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/blog-posts/{id} for another user's post returns 404."""
    from tests.conftest import register_and_login

    site = await create_test_site(client, auth_headers, domain="crossuser-blog.com")
    post = await create_test_blog_post(client, auth_headers, site["id"], title="Private Post")

    user2_headers = await register_and_login(client, email="blogspy@example.com")
    resp = await client.get(f"/api/v1/blog-posts/{post['id']}", headers=user2_headers)
    assert resp.status_code == 404


# ── Update Blog Post Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_blog_post_title(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/blog-posts/{id} updates the title field."""
    site = await create_test_site(client, auth_headers, domain="update-blog-title.com")
    post = await create_test_blog_post(client, auth_headers, site["id"], title="Original Title")

    resp = await client.patch(
        f"/api/v1/blog-posts/{post['id']}",
        json={"title": "Updated Title"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_update_blog_post_content(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/blog-posts/{id} updates the content and recalculates word_count."""
    site = await create_test_site(client, auth_headers, domain="update-blog-content.com")
    post = await create_test_blog_post(client, auth_headers, site["id"], title="Content Update")

    new_content = "Updated content with exactly seven words here."
    resp = await client.patch(
        f"/api/v1/blog-posts/{post['id']}",
        json={"content": new_content},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["content"] == new_content
    assert data["word_count"] > 0


@pytest.mark.asyncio
async def test_update_blog_post_status_published(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/blog-posts/{id} with status='published' sets published_at."""
    site = await create_test_site(client, auth_headers, domain="publish-blog.com")
    post = await create_test_blog_post(client, auth_headers, site["id"], title="Publish Me")

    assert post["status"] == "draft"
    assert post["published_at"] is None

    resp = await client.patch(
        f"/api/v1/blog-posts/{post['id']}",
        json={"status": "published"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "published"
    assert data["published_at"] is not None


@pytest.mark.asyncio
async def test_update_blog_post_keywords(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/blog-posts/{id} updates the keywords list."""
    site = await create_test_site(client, auth_headers, domain="update-blog-kw.com")
    post = await create_test_blog_post(
        client, auth_headers, site["id"],
        title="KW Update",
        keywords=["old"],
    )

    resp = await client.patch(
        f"/api/v1/blog-posts/{post['id']}",
        json={"keywords": ["new", "updated"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["keywords"] == ["new", "updated"]


@pytest.mark.asyncio
async def test_update_blog_post_not_found(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/blog-posts/{id} with a non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.patch(
        f"/api/v1/blog-posts/{fake_id}",
        json={"title": "Ghost Post"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ── Delete Blog Post Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_blog_post(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/blog-posts/{id} removes the post and returns 204."""
    site = await create_test_site(client, auth_headers, domain="delete-blog.com")
    post = await create_test_blog_post(client, auth_headers, site["id"], title="Delete Me")

    resp = await client.delete(f"/api/v1/blog-posts/{post['id']}", headers=auth_headers)
    assert resp.status_code == 204

    # Verify it is gone
    resp = await client.get(f"/api/v1/blog-posts/{post['id']}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_blog_post_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/blog-posts/{id} with a non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/api/v1/blog-posts/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_blog_post_other_user(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/blog-posts/{id} for another user's post returns 404."""
    from tests.conftest import register_and_login

    site = await create_test_site(client, auth_headers, domain="protect-blog.com")
    post = await create_test_blog_post(client, auth_headers, site["id"], title="Protected Post")

    user2_headers = await register_and_login(client, email="blogdeleter@example.com")
    resp = await client.delete(f"/api/v1/blog-posts/{post['id']}", headers=user2_headers)
    assert resp.status_code == 404


# ── AI Generate Blog Content Tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_blog_content(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/blog-posts/generate fills content and meta_description."""
    site = await create_test_site(client, auth_headers, domain="generate-blog.com")
    post = await create_test_blog_post(
        client,
        auth_headers,
        site["id"],
        title="AI Generated Post",
        keywords=["seo", "automation"],
    )

    # Content should be empty or minimal initially
    resp = await client.post(
        "/api/v1/blog-posts/generate",
        json={"post_id": post["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["id"] == post["id"]
    # AI generation should have filled in content
    assert len(data["content"]) > 0
    assert data["word_count"] > 0
    # Meta description should be populated
    assert data["meta_description"] is not None
    assert len(data["meta_description"]) > 0


@pytest.mark.asyncio
async def test_generate_blog_content_not_found(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/blog-posts/generate with a non-existent post_id returns 404."""
    fake_id = str(uuid.uuid4())

    resp = await client.post(
        "/api/v1/blog-posts/generate",
        json={"post_id": fake_id},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_generate_blog_content_other_user(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/blog-posts/generate for another user's post returns 404."""
    from tests.conftest import register_and_login

    site = await create_test_site(client, auth_headers, domain="gen-crossuser.com")
    post = await create_test_blog_post(
        client, auth_headers, site["id"], title="Private Gen Post"
    )

    user2_headers = await register_and_login(client, email="genthief@example.com")
    resp = await client.post(
        "/api/v1/blog-posts/generate",
        json={"post_id": post["id"]},
        headers=user2_headers,
    )
    assert resp.status_code == 404
