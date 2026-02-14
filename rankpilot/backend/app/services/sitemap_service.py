"""
XML sitemap generation service for the RankPilot SEO engine.

Generates valid XML sitemaps conforming to the Sitemap protocol 0.9
specification (https://www.sitemaps.org/protocol.html). Sitemaps help
search engines discover and index all pages on a website.

For Developers:
    ``generate_xml_sitemap(urls)`` takes a list of URL dicts and produces
    a valid XML string. Each URL dict can include 'loc', 'lastmod',
    'changefreq', and 'priority' fields. Only 'loc' is required.
    The output includes the XML declaration and urlset namespace.

For QA Engineers:
    Verify the output is valid XML with proper namespace.
    Test with various URL counts (0, 1, many).
    Test with optional fields (lastmod, changefreq, priority).
    Validate that special characters in URLs are properly escaped.

For Project Managers:
    Sitemap generation helps users submit complete sitemaps to
    Google Search Console, improving indexation coverage.

For End Users:
    Generate an XML sitemap for your website containing all important
    pages. Submit it to search engines to ensure complete indexation.
"""

from xml.sax.saxutils import escape


def generate_xml_sitemap(urls: list[dict]) -> str:
    """
    Generate a valid XML sitemap from a list of URL entries.

    Produces an XML document conforming to the Sitemap protocol 0.9
    specification, ready to be served as an XML file or submitted
    to search engines.

    Args:
        urls: List of URL dicts. Each dict should contain:
            - loc (str): The page URL (required).
            - lastmod (str, optional): Last modification date (ISO 8601).
            - changefreq (str, optional): Change frequency
              ('always', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'never').
            - priority (str|float, optional): Priority from 0.0 to 1.0.

    Returns:
        A complete XML sitemap string with XML declaration,
        urlset element with namespace, and url entries.

    Example:
        >>> urls = [{"loc": "https://example.com/", "priority": "1.0"}]
        >>> xml = generate_xml_sitemap(urls)
        >>> assert '<?xml version="1.0"' in xml
        >>> assert '<urlset' in xml
    """
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for url_entry in urls:
        loc = url_entry.get("loc", "")
        if not loc:
            continue

        lines.append("  <url>")
        lines.append(f"    <loc>{escape(loc)}</loc>")

        if url_entry.get("lastmod"):
            lines.append(f"    <lastmod>{escape(str(url_entry['lastmod']))}</lastmod>")
        if url_entry.get("changefreq"):
            lines.append(f"    <changefreq>{escape(str(url_entry['changefreq']))}</changefreq>")
        if url_entry.get("priority") is not None:
            lines.append(f"    <priority>{escape(str(url_entry['priority']))}</priority>")

        lines.append("  </url>")

    lines.append("</urlset>")

    return "\n".join(lines)
