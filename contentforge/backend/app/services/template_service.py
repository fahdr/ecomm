"""
Content generation prompt template registry.

Provides a library of prompt templates for each content type and writing
style combination. Templates include system prompts, user prompt templates
with placeholders, and output format instructions.

For Developers:
    Use ``get_template(name, content_type)`` to retrieve a PromptTemplate
    for a given style and content type. The template includes a system
    prompt, a user prompt template (with {product_name}, {product_price},
    etc. placeholders), and output format instructions.

    To add a new template style, add an entry to ``TEMPLATE_REGISTRY``
    with prompts for each content type.

    To add a new content type, add entries for it in every style dict
    and add the type name to ``ALL_CONTENT_TYPES``.

For QA Engineers:
    Test that ``get_template()`` returns valid templates for all
    registered name/content_type combinations. Verify that
    ``list_template_names()`` returns all 10+ template styles.
    Verify fallback behavior when a template name is not found.

For Project Managers:
    Templates are the core differentiator that makes ContentForge's
    output feel customized rather than generic. Each template targets
    a different marketplace, brand voice, or content strategy.

For End Users:
    Choose a template style that matches your brand and target marketplace.
    For example, use 'amazon_style' for Amazon listings, 'shopify_seo' for
    Shopify stores optimized for search, or 'luxury_brand' for premium
    product positioning.
"""

from dataclasses import dataclass, field


# ── Content Type Constants ────────────────────────────────────────────

ALL_CONTENT_TYPES = [
    "title",
    "description",
    "meta_description",
    "keywords",
    "bullet_points",
    "social_caption",
]
"""All supported content types for generation."""


# ── PromptTemplate Data Class ─────────────────────────────────────────


@dataclass
class PromptTemplate:
    """
    A prompt template for a specific content type and style combination.

    Attributes:
        style_name: The template style identifier (e.g., 'amazon_style').
        content_type: The content type this template generates
            (e.g., 'title', 'description').
        system_prompt: System-level instructions for the LLM that establish
            context, persona, and constraints.
        user_prompt_template: User prompt with placeholders ({product_name},
            {product_price}, {product_category}, {product_features},
            {product_description}) that are filled in at generation time.
        output_format: Instructions for how the LLM should format its output
            (e.g., plain text, markdown, HTML, JSON).
        max_tokens: Recommended max tokens for this content type.
        temperature: Recommended temperature for this content type.
    """

    style_name: str
    content_type: str
    system_prompt: str
    user_prompt_template: str
    output_format: str = "plain text"
    max_tokens: int = 500
    temperature: float = 0.7


# ── Template Definitions ──────────────────────────────────────────────

_AMAZON_STYLE = {
    "title": PromptTemplate(
        style_name="amazon_style",
        content_type="title",
        system_prompt=(
            "You are an Amazon product listing expert. Write titles that maximize "
            "search visibility while following Amazon's style guidelines. Include "
            "the brand, key feature, size/quantity, and main use case. Keep titles "
            "under 200 characters."
        ),
        user_prompt_template=(
            "Write an Amazon-optimized product title for:\n"
            "Product: {product_name}\n"
            "Category: {product_category}\n"
            "Price: ${product_price}\n"
            "Key Features: {product_features}\n"
        ),
        output_format="plain text, single line, no quotes",
        max_tokens=100,
        temperature=0.5,
    ),
    "description": PromptTemplate(
        style_name="amazon_style",
        content_type="description",
        system_prompt=(
            "You are an Amazon product listing expert. Write compelling product "
            "descriptions that highlight benefits, build trust, and drive conversions. "
            "Use short paragraphs, simple language, and address common buyer concerns."
        ),
        user_prompt_template=(
            "Write a detailed Amazon product description for:\n"
            "Product: {product_name}\n"
            "Category: {product_category}\n"
            "Price: ${product_price}\n"
            "Features: {product_features}\n"
            "Additional Info: {product_description}\n"
        ),
        output_format="HTML with <p> tags for paragraphs",
        max_tokens=800,
        temperature=0.6,
    ),
    "meta_description": PromptTemplate(
        style_name="amazon_style",
        content_type="meta_description",
        system_prompt=(
            "Write a concise meta description optimized for Amazon search. "
            "Include the product name, key benefit, and a call to action. "
            "Keep it under 155 characters."
        ),
        user_prompt_template=(
            "Meta description for: {product_name} in {product_category}. "
            "Key features: {product_features}. Price: ${product_price}."
        ),
        output_format="plain text, under 155 characters",
        max_tokens=80,
        temperature=0.4,
    ),
    "keywords": PromptTemplate(
        style_name="amazon_style",
        content_type="keywords",
        system_prompt=(
            "Generate Amazon backend search keywords for maximum discoverability. "
            "Include synonyms, related terms, and common misspellings. "
            "Do not repeat words from the title. Comma-separated."
        ),
        user_prompt_template=(
            "Backend search keywords for: {product_name}\n"
            "Category: {product_category}\n"
            "Features: {product_features}\n"
        ),
        output_format="comma-separated keywords",
        max_tokens=200,
        temperature=0.5,
    ),
    "bullet_points": PromptTemplate(
        style_name="amazon_style",
        content_type="bullet_points",
        system_prompt=(
            "Write Amazon-style bullet points. Start each with a CAPITALIZED "
            "benefit phrase followed by a dash and details. Focus on benefits "
            "over features. Include dimensions, materials, or compatibility "
            "where relevant. 5 bullets."
        ),
        user_prompt_template=(
            "Write 5 Amazon bullet points for:\n"
            "Product: {product_name}\n"
            "Features: {product_features}\n"
            "Price: ${product_price}\n"
        ),
        output_format="markdown bullet list (- prefix)",
        max_tokens=500,
        temperature=0.6,
    ),
    "social_caption": PromptTemplate(
        style_name="amazon_style",
        content_type="social_caption",
        system_prompt=(
            "Write a social media caption promoting an Amazon product listing. "
            "Include relevant hashtags, an emoji, and a clear call to action. "
            "Keep it under 280 characters for Twitter compatibility."
        ),
        user_prompt_template=(
            "Social caption for: {product_name} (${product_price}) — "
            "{product_category}. Features: {product_features}."
        ),
        output_format="plain text with hashtags",
        max_tokens=100,
        temperature=0.8,
    ),
}

_SHOPIFY_SEO = {
    "title": PromptTemplate(
        style_name="shopify_seo",
        content_type="title",
        system_prompt=(
            "You are an SEO specialist for Shopify stores. Write product titles "
            "that rank well in Google while being attractive to shoppers. Include "
            "the primary keyword naturally. Keep under 70 characters."
        ),
        user_prompt_template=(
            "SEO-optimized Shopify title for:\n"
            "Product: {product_name}\n"
            "Category: {product_category}\n"
            "Features: {product_features}\n"
        ),
        output_format="plain text, under 70 characters",
        max_tokens=50,
        temperature=0.5,
    ),
    "description": PromptTemplate(
        style_name="shopify_seo",
        content_type="description",
        system_prompt=(
            "You are an SEO copywriter for Shopify stores. Write product "
            "descriptions that naturally incorporate keywords, use semantic HTML, "
            "and are structured for both readers and search engines. Include "
            "H2 subheadings, short paragraphs, and internal linking suggestions."
        ),
        user_prompt_template=(
            "SEO product description for:\n"
            "Product: {product_name}\n"
            "Category: {product_category}\n"
            "Price: ${product_price}\n"
            "Features: {product_features}\n"
            "Details: {product_description}\n"
        ),
        output_format="HTML with <h2>, <p>, <ul> tags",
        max_tokens=1000,
        temperature=0.6,
    ),
    "meta_description": PromptTemplate(
        style_name="shopify_seo",
        content_type="meta_description",
        system_prompt=(
            "Write a Google-optimized meta description for a Shopify product page. "
            "Include the primary keyword in the first 60 characters. Add a clear "
            "value proposition and call to action. 150-160 characters."
        ),
        user_prompt_template=(
            "Meta description for Shopify product: {product_name}\n"
            "Category: {product_category}\n"
            "Price: ${product_price}\n"
        ),
        output_format="plain text, 150-160 characters",
        max_tokens=80,
        temperature=0.4,
    ),
    "keywords": PromptTemplate(
        style_name="shopify_seo",
        content_type="keywords",
        system_prompt=(
            "Generate SEO keywords for a Shopify product page. Include primary "
            "keyword, long-tail variations, and related search terms. Focus on "
            "buyer intent keywords. Comma-separated list."
        ),
        user_prompt_template=(
            "SEO keywords for: {product_name}\n"
            "Category: {product_category}\n"
            "Features: {product_features}\n"
        ),
        output_format="comma-separated keywords",
        max_tokens=200,
        temperature=0.5,
    ),
    "bullet_points": PromptTemplate(
        style_name="shopify_seo",
        content_type="bullet_points",
        system_prompt=(
            "Write product highlights for a Shopify product page. Use concise, "
            "benefit-focused bullet points that incorporate relevant keywords "
            "naturally. Include specifications where helpful."
        ),
        user_prompt_template=(
            "Product highlights for:\n"
            "Product: {product_name}\n"
            "Features: {product_features}\n"
        ),
        output_format="markdown bullet list (- prefix)",
        max_tokens=400,
        temperature=0.6,
    ),
    "social_caption": PromptTemplate(
        style_name="shopify_seo",
        content_type="social_caption",
        system_prompt=(
            "Write a social media caption to promote a Shopify product. "
            "Include a hook, the key benefit, and a link placeholder [LINK]. "
            "Add 3-5 relevant hashtags."
        ),
        user_prompt_template=(
            "Social caption for Shopify product: {product_name}\n"
            "Price: ${product_price}\n"
            "Features: {product_features}\n"
        ),
        output_format="plain text with hashtags and [LINK] placeholder",
        max_tokens=150,
        temperature=0.8,
    ),
}

_LUXURY_BRAND = {
    "title": PromptTemplate(
        style_name="luxury_brand",
        content_type="title",
        system_prompt=(
            "You are a luxury brand copywriter. Write elegant, refined product "
            "titles that convey exclusivity and prestige. Use sophisticated "
            "vocabulary. Avoid exclamation marks and promotional language."
        ),
        user_prompt_template=(
            "Luxury product title for:\n"
            "Product: {product_name}\n"
            "Category: {product_category}\n"
        ),
        output_format="plain text, elegant and concise",
        max_tokens=60,
        temperature=0.6,
    ),
    "description": PromptTemplate(
        style_name="luxury_brand",
        content_type="description",
        system_prompt=(
            "You are a luxury brand storyteller. Write product descriptions that "
            "evoke desire through sensory language, heritage references, and "
            "craftsmanship details. Use a refined, unhurried tone. Emphasize "
            "materials, artisan processes, and the experience of ownership."
        ),
        user_prompt_template=(
            "Luxury product description for:\n"
            "Product: {product_name}\n"
            "Category: {product_category}\n"
            "Price: ${product_price}\n"
            "Craftsmanship details: {product_features}\n"
            "Story: {product_description}\n"
        ),
        output_format="HTML with <p> tags, no bullet lists",
        max_tokens=800,
        temperature=0.7,
    ),
    "meta_description": PromptTemplate(
        style_name="luxury_brand",
        content_type="meta_description",
        system_prompt=(
            "Write a refined meta description for a luxury product page. "
            "Convey exclusivity without being overtly promotional."
        ),
        user_prompt_template=(
            "Meta description for luxury: {product_name} in {product_category}."
        ),
        output_format="plain text, under 155 characters",
        max_tokens=80,
        temperature=0.5,
    ),
    "keywords": PromptTemplate(
        style_name="luxury_brand",
        content_type="keywords",
        system_prompt=(
            "Generate refined keywords for a luxury product listing. Include "
            "aspirational terms, material names, and luxury-market search terms."
        ),
        user_prompt_template=(
            "Keywords for luxury: {product_name}, {product_category}. "
            "Features: {product_features}."
        ),
        output_format="comma-separated keywords",
        max_tokens=150,
        temperature=0.5,
    ),
    "bullet_points": PromptTemplate(
        style_name="luxury_brand",
        content_type="bullet_points",
        system_prompt=(
            "Write refined product highlights for a luxury brand. Focus on "
            "materials, craftsmanship, heritage, and the sensory experience. "
            "No hype language."
        ),
        user_prompt_template=(
            "Luxury highlights for: {product_name}\n"
            "Details: {product_features}\n"
        ),
        output_format="markdown bullet list (- prefix)",
        max_tokens=400,
        temperature=0.6,
    ),
    "social_caption": PromptTemplate(
        style_name="luxury_brand",
        content_type="social_caption",
        system_prompt=(
            "Write an aspirational social media caption for a luxury brand. "
            "Evoke desire and exclusivity. Minimal hashtags (2-3 max). "
            "No exclamation marks."
        ),
        user_prompt_template=(
            "Luxury social caption for: {product_name} (${product_price})."
        ),
        output_format="plain text, aspirational tone",
        max_tokens=120,
        temperature=0.7,
    ),
}

_TECHNICAL_SPEC = {
    "title": PromptTemplate(
        style_name="technical_spec",
        content_type="title",
        system_prompt=(
            "Write a precise, specification-focused product title. Include "
            "model number, key specs, and primary use case. Factual and clear."
        ),
        user_prompt_template=(
            "Technical title for: {product_name}\n"
            "Category: {product_category}\n"
            "Specs: {product_features}\n"
        ),
        output_format="plain text, specs-focused",
        max_tokens=80,
        temperature=0.3,
    ),
    "description": PromptTemplate(
        style_name="technical_spec",
        content_type="description",
        system_prompt=(
            "Write a technical product description with detailed specifications, "
            "compatibility information, and performance metrics. Use tables where "
            "appropriate. Target knowledgeable buyers who compare specs."
        ),
        user_prompt_template=(
            "Technical description for:\n"
            "Product: {product_name}\n"
            "Category: {product_category}\n"
            "Specifications: {product_features}\n"
            "Details: {product_description}\n"
        ),
        output_format="HTML with specification tables",
        max_tokens=1000,
        temperature=0.4,
    ),
    "meta_description": PromptTemplate(
        style_name="technical_spec",
        content_type="meta_description",
        system_prompt=(
            "Write a spec-focused meta description. Include key technical "
            "specifications and model identifiers."
        ),
        user_prompt_template=(
            "Technical meta for: {product_name}. Specs: {product_features}."
        ),
        output_format="plain text, under 155 characters",
        max_tokens=80,
        temperature=0.3,
    ),
    "keywords": PromptTemplate(
        style_name="technical_spec",
        content_type="keywords",
        system_prompt=(
            "Generate technical keywords including model numbers, spec values, "
            "compatibility terms, and comparison keywords."
        ),
        user_prompt_template=(
            "Technical keywords for: {product_name}. "
            "Specs: {product_features}."
        ),
        output_format="comma-separated keywords",
        max_tokens=200,
        temperature=0.3,
    ),
    "bullet_points": PromptTemplate(
        style_name="technical_spec",
        content_type="bullet_points",
        system_prompt=(
            "Write specification-focused bullet points. Lead with the spec "
            "name followed by the value. Include units and ranges."
        ),
        user_prompt_template=(
            "Spec bullet points for: {product_name}\n"
            "Features: {product_features}\n"
        ),
        output_format="markdown bullet list (- Spec: Value)",
        max_tokens=400,
        temperature=0.3,
    ),
    "social_caption": PromptTemplate(
        style_name="technical_spec",
        content_type="social_caption",
        system_prompt=(
            "Write a social caption highlighting the key technical advantage. "
            "Include one impressive spec number. Tech-enthusiast audience."
        ),
        user_prompt_template=(
            "Tech social caption for: {product_name}. Specs: {product_features}."
        ),
        output_format="plain text with hashtags",
        max_tokens=120,
        temperature=0.7,
    ),
}

_CASUAL_FRIENDLY = {
    "title": PromptTemplate(
        style_name="casual_friendly",
        content_type="title",
        system_prompt=(
            "Write a fun, approachable product title. Use conversational "
            "language that feels like a friend's recommendation."
        ),
        user_prompt_template=(
            "Fun product title for: {product_name} ({product_category})."
        ),
        output_format="plain text, conversational",
        max_tokens=60,
        temperature=0.8,
    ),
    "description": PromptTemplate(
        style_name="casual_friendly",
        content_type="description",
        system_prompt=(
            "Write a casual, friendly product description like you're telling "
            "a friend about a great find. Use contractions, relatable scenarios, "
            "and enthusiasm without being over-the-top."
        ),
        user_prompt_template=(
            "Friendly description for:\n"
            "Product: {product_name}\n"
            "Price: ${product_price}\n"
            "Features: {product_features}\n"
            "Details: {product_description}\n"
        ),
        output_format="HTML with casual tone",
        max_tokens=600,
        temperature=0.8,
    ),
    "meta_description": PromptTemplate(
        style_name="casual_friendly",
        content_type="meta_description",
        system_prompt="Write a friendly, inviting meta description. Conversational tone.",
        user_prompt_template="Fun meta for: {product_name}. Features: {product_features}.",
        output_format="plain text, under 155 characters",
        max_tokens=80,
        temperature=0.7,
    ),
    "keywords": PromptTemplate(
        style_name="casual_friendly",
        content_type="keywords",
        system_prompt="Generate conversational, buyer-intent keywords including colloquial terms.",
        user_prompt_template="Keywords for: {product_name}. Category: {product_category}.",
        output_format="comma-separated keywords",
        max_tokens=150,
        temperature=0.6,
    ),
    "bullet_points": PromptTemplate(
        style_name="casual_friendly",
        content_type="bullet_points",
        system_prompt=(
            "Write casual, benefit-focused bullet points. Start each with "
            "a relatable scenario or benefit, not a spec."
        ),
        user_prompt_template="Friendly bullets for: {product_name}. Features: {product_features}.",
        output_format="markdown bullet list",
        max_tokens=400,
        temperature=0.8,
    ),
    "social_caption": PromptTemplate(
        style_name="casual_friendly",
        content_type="social_caption",
        system_prompt="Write a fun, shareable social media caption. Include emojis and hashtags.",
        user_prompt_template="Fun caption for: {product_name} (${product_price}).",
        output_format="plain text with emojis and hashtags",
        max_tokens=120,
        temperature=0.9,
    ),
}

_MINIMALIST = {
    "title": PromptTemplate(
        style_name="minimalist",
        content_type="title",
        system_prompt="Write a clean, minimal product title. Maximum 5 words. No adjectives.",
        user_prompt_template="Minimal title: {product_name}, {product_category}.",
        output_format="plain text, ultra-concise",
        max_tokens=30,
        temperature=0.4,
    ),
    "description": PromptTemplate(
        style_name="minimalist",
        content_type="description",
        system_prompt=(
            "Write a minimalist product description. Short sentences. "
            "White space between ideas. Focus on essential details only. "
            "No filler words. Zen-like clarity."
        ),
        user_prompt_template=(
            "Minimalist description:\n"
            "Product: {product_name}\n"
            "Features: {product_features}\n"
            "Price: ${product_price}\n"
        ),
        output_format="HTML with short paragraphs, breathing room",
        max_tokens=300,
        temperature=0.5,
    ),
    "meta_description": PromptTemplate(
        style_name="minimalist",
        content_type="meta_description",
        system_prompt="Write a minimal, clean meta description. Under 120 characters.",
        user_prompt_template="Minimal meta: {product_name}. {product_features}.",
        output_format="plain text, ultra-concise",
        max_tokens=50,
        temperature=0.3,
    ),
    "keywords": PromptTemplate(
        style_name="minimalist",
        content_type="keywords",
        system_prompt="Generate essential keywords only. No redundancy. Max 8 terms.",
        user_prompt_template="Core keywords: {product_name}, {product_category}.",
        output_format="comma-separated, max 8 keywords",
        max_tokens=80,
        temperature=0.3,
    ),
    "bullet_points": PromptTemplate(
        style_name="minimalist",
        content_type="bullet_points",
        system_prompt="Write 3 minimal bullet points. One key fact each. No fluff.",
        user_prompt_template="Minimal bullets: {product_name}. {product_features}.",
        output_format="markdown bullet list, 3 items max",
        max_tokens=150,
        temperature=0.4,
    ),
    "social_caption": PromptTemplate(
        style_name="minimalist",
        content_type="social_caption",
        system_prompt="Write a minimal social caption. Under 100 characters. One hashtag.",
        user_prompt_template="Minimal caption: {product_name}.",
        output_format="plain text, ultra-concise",
        max_tokens=50,
        temperature=0.5,
    ),
}

_STORYTELLING = {
    "title": PromptTemplate(
        style_name="storytelling",
        content_type="title",
        system_prompt=(
            "Write a product title that hints at a story or transformation. "
            "Evoke curiosity and emotion."
        ),
        user_prompt_template="Storytelling title: {product_name}, {product_category}.",
        output_format="plain text, evocative",
        max_tokens=60,
        temperature=0.8,
    ),
    "description": PromptTemplate(
        style_name="storytelling",
        content_type="description",
        system_prompt=(
            "Write a narrative product description that tells the story of the "
            "product's creation, the problem it solves, or the transformation "
            "it enables. Use sensory details, a clear arc (problem -> solution "
            "-> outcome), and emotionally resonant language."
        ),
        user_prompt_template=(
            "Tell the story of:\n"
            "Product: {product_name}\n"
            "Category: {product_category}\n"
            "Features: {product_features}\n"
            "Background: {product_description}\n"
        ),
        output_format="HTML with narrative paragraphs",
        max_tokens=1000,
        temperature=0.8,
    ),
    "meta_description": PromptTemplate(
        style_name="storytelling",
        content_type="meta_description",
        system_prompt="Write a story-hook meta description that creates curiosity.",
        user_prompt_template="Story meta: {product_name}. {product_features}.",
        output_format="plain text, curiosity-driven",
        max_tokens=80,
        temperature=0.7,
    ),
    "keywords": PromptTemplate(
        style_name="storytelling",
        content_type="keywords",
        system_prompt="Generate keywords including emotional and aspirational terms.",
        user_prompt_template="Story keywords: {product_name}, {product_category}.",
        output_format="comma-separated keywords",
        max_tokens=150,
        temperature=0.6,
    ),
    "bullet_points": PromptTemplate(
        style_name="storytelling",
        content_type="bullet_points",
        system_prompt=(
            "Write bullet points that tell micro-stories. Each bullet describes "
            "a scenario where the product shines."
        ),
        user_prompt_template="Story bullets: {product_name}. {product_features}.",
        output_format="markdown bullet list with mini-narratives",
        max_tokens=500,
        temperature=0.8,
    ),
    "social_caption": PromptTemplate(
        style_name="storytelling",
        content_type="social_caption",
        system_prompt=(
            "Write a social caption that starts with a mini-story or relatable "
            "moment, then reveals the product as the hero."
        ),
        user_prompt_template="Story caption: {product_name} (${product_price}).",
        output_format="plain text, narrative hook",
        max_tokens=150,
        temperature=0.9,
    ),
}

_FEATURE_FOCUSED = {
    "title": PromptTemplate(
        style_name="feature_focused",
        content_type="title",
        system_prompt="Write a feature-packed product title highlighting the top 2-3 features.",
        user_prompt_template="Feature title: {product_name}. Features: {product_features}.",
        output_format="plain text, feature-dense",
        max_tokens=80,
        temperature=0.5,
    ),
    "description": PromptTemplate(
        style_name="feature_focused",
        content_type="description",
        system_prompt=(
            "Write a feature-focused product description. Organize by feature "
            "categories. Each feature gets a heading and detailed explanation "
            "of what it does and why it matters."
        ),
        user_prompt_template=(
            "Feature description:\n"
            "Product: {product_name}\n"
            "Features: {product_features}\n"
            "Details: {product_description}\n"
        ),
        output_format="HTML with feature headings and detail paragraphs",
        max_tokens=800,
        temperature=0.5,
    ),
    "meta_description": PromptTemplate(
        style_name="feature_focused",
        content_type="meta_description",
        system_prompt="Write a feature-packed meta description. List top 3 features.",
        user_prompt_template="Feature meta: {product_name}. {product_features}.",
        output_format="plain text, feature-dense",
        max_tokens=80,
        temperature=0.4,
    ),
    "keywords": PromptTemplate(
        style_name="feature_focused",
        content_type="keywords",
        system_prompt="Generate feature-based keywords including specific capability terms.",
        user_prompt_template="Feature keywords: {product_name}. {product_features}.",
        output_format="comma-separated keywords",
        max_tokens=200,
        temperature=0.4,
    ),
    "bullet_points": PromptTemplate(
        style_name="feature_focused",
        content_type="bullet_points",
        system_prompt="Write feature-focused bullets: Feature Name — What it does and why it matters.",
        user_prompt_template="Feature bullets: {product_name}. {product_features}.",
        output_format="markdown bullet list (- Feature: explanation)",
        max_tokens=500,
        temperature=0.5,
    ),
    "social_caption": PromptTemplate(
        style_name="feature_focused",
        content_type="social_caption",
        system_prompt="Write a social caption highlighting the standout feature.",
        user_prompt_template="Feature caption: {product_name}. Best feature: {product_features}.",
        output_format="plain text with hashtags",
        max_tokens=120,
        temperature=0.7,
    ),
}

_BENEFIT_DRIVEN = {
    "title": PromptTemplate(
        style_name="benefit_driven",
        content_type="title",
        system_prompt=(
            "Write a benefit-driven product title. Lead with the outcome "
            "the buyer gets, not the product name."
        ),
        user_prompt_template="Benefit title: {product_name}, {product_category}. Features: {product_features}.",
        output_format="plain text, benefit-first",
        max_tokens=70,
        temperature=0.6,
    ),
    "description": PromptTemplate(
        style_name="benefit_driven",
        content_type="description",
        system_prompt=(
            "Write a benefit-driven product description. Structure: "
            "1) Main benefit headline, 2) How the product delivers that benefit, "
            "3) Secondary benefits, 4) Social proof / trust signal, 5) Call to action. "
            "Focus on outcomes, not specs."
        ),
        user_prompt_template=(
            "Benefit description:\n"
            "Product: {product_name}\n"
            "Benefits from features: {product_features}\n"
            "Price: ${product_price}\n"
        ),
        output_format="HTML with benefit-focused sections",
        max_tokens=800,
        temperature=0.7,
    ),
    "meta_description": PromptTemplate(
        style_name="benefit_driven",
        content_type="meta_description",
        system_prompt="Write a benefit-first meta description. Lead with the outcome.",
        user_prompt_template="Benefit meta: {product_name}. Outcomes: {product_features}.",
        output_format="plain text, benefit-led",
        max_tokens=80,
        temperature=0.5,
    ),
    "keywords": PromptTemplate(
        style_name="benefit_driven",
        content_type="keywords",
        system_prompt="Generate benefit-oriented keywords including outcome and solution terms.",
        user_prompt_template="Benefit keywords: {product_name}. Benefits: {product_features}.",
        output_format="comma-separated keywords",
        max_tokens=150,
        temperature=0.5,
    ),
    "bullet_points": PromptTemplate(
        style_name="benefit_driven",
        content_type="bullet_points",
        system_prompt="Write benefit-led bullets: 'Benefit — how the product delivers it.'",
        user_prompt_template="Benefit bullets: {product_name}. Features: {product_features}.",
        output_format="markdown bullet list",
        max_tokens=400,
        temperature=0.6,
    ),
    "social_caption": PromptTemplate(
        style_name="benefit_driven",
        content_type="social_caption",
        system_prompt="Write a social caption focusing on the life improvement the product brings.",
        user_prompt_template="Benefit caption: {product_name} (${product_price}). Benefits: {product_features}.",
        output_format="plain text with hashtags",
        max_tokens=120,
        temperature=0.8,
    ),
}

_COMPARISON = {
    "title": PromptTemplate(
        style_name="comparison",
        content_type="title",
        system_prompt=(
            "Write a product title that positions the product as the superior "
            "choice in its category. Use comparative language without naming competitors."
        ),
        user_prompt_template="Comparison title: {product_name}, {product_category}. Edge: {product_features}.",
        output_format="plain text, competitive positioning",
        max_tokens=70,
        temperature=0.6,
    ),
    "description": PromptTemplate(
        style_name="comparison",
        content_type="description",
        system_prompt=(
            "Write a product description that positions this product against "
            "generic alternatives. Use a 'Why this vs. that' structure. "
            "Highlight unique advantages without naming specific competitors. "
            "Include a comparison-style section."
        ),
        user_prompt_template=(
            "Comparison description:\n"
            "Product: {product_name}\n"
            "Category: {product_category}\n"
            "Advantages: {product_features}\n"
            "Details: {product_description}\n"
        ),
        output_format="HTML with comparison sections",
        max_tokens=900,
        temperature=0.6,
    ),
    "meta_description": PromptTemplate(
        style_name="comparison",
        content_type="meta_description",
        system_prompt="Write a meta description that positions the product as the category leader.",
        user_prompt_template="Comparison meta: {product_name}. Advantages: {product_features}.",
        output_format="plain text, competitive tone",
        max_tokens=80,
        temperature=0.5,
    ),
    "keywords": PromptTemplate(
        style_name="comparison",
        content_type="keywords",
        system_prompt=(
            "Generate comparison keywords: 'best X', 'X vs', 'top X', "
            "'alternative to', and category-leading terms."
        ),
        user_prompt_template="Comparison keywords: {product_name}, {product_category}.",
        output_format="comma-separated keywords",
        max_tokens=200,
        temperature=0.5,
    ),
    "bullet_points": PromptTemplate(
        style_name="comparison",
        content_type="bullet_points",
        system_prompt=(
            "Write comparison-style bullet points: 'Unlike typical X, this product Y.' "
            "Position each feature as a competitive advantage."
        ),
        user_prompt_template="Comparison bullets: {product_name}. Advantages: {product_features}.",
        output_format="markdown bullet list, comparative",
        max_tokens=500,
        temperature=0.6,
    ),
    "social_caption": PromptTemplate(
        style_name="comparison",
        content_type="social_caption",
        system_prompt="Write a social caption positioning the product as the best choice in its category.",
        user_prompt_template="Comparison caption: {product_name} vs the rest. {product_features}.",
        output_format="plain text with hashtags",
        max_tokens=120,
        temperature=0.7,
    ),
}


# ── Template Registry ─────────────────────────────────────────────────

TEMPLATE_REGISTRY: dict[str, dict[str, PromptTemplate]] = {
    "amazon_style": _AMAZON_STYLE,
    "shopify_seo": _SHOPIFY_SEO,
    "luxury_brand": _LUXURY_BRAND,
    "technical_spec": _TECHNICAL_SPEC,
    "casual_friendly": _CASUAL_FRIENDLY,
    "minimalist": _MINIMALIST,
    "storytelling": _STORYTELLING,
    "feature_focused": _FEATURE_FOCUSED,
    "benefit_driven": _BENEFIT_DRIVEN,
    "comparison": _COMPARISON,
}
"""
Registry of all built-in prompt template styles.

Each key is a template style name. Each value is a dict mapping
content types to PromptTemplate instances.
"""

# Default fallback style when no template is specified
DEFAULT_TEMPLATE_NAME = "shopify_seo"
"""Default template style used when no specific template is requested."""


def get_template(name: str, content_type: str) -> PromptTemplate | None:
    """
    Retrieve a prompt template by style name and content type.

    Looks up the template in the registry and returns the PromptTemplate
    for the given content type. Falls back to the default template style
    if the requested name is not found.

    Args:
        name: Template style name (e.g., 'amazon_style', 'luxury_brand').
        content_type: Content type to generate (e.g., 'title', 'description').

    Returns:
        PromptTemplate if found, None if neither the requested name nor
        default template has the requested content type.
    """
    style_templates = TEMPLATE_REGISTRY.get(name)
    if not style_templates:
        # Fall back to default
        style_templates = TEMPLATE_REGISTRY.get(DEFAULT_TEMPLATE_NAME, {})
    return style_templates.get(content_type)


def list_template_names() -> list[str]:
    """
    List all available template style names.

    Returns:
        Sorted list of registered template style names.
    """
    return sorted(TEMPLATE_REGISTRY.keys())


def list_content_types() -> list[str]:
    """
    List all supported content types.

    Returns:
        List of all content type identifiers.
    """
    return list(ALL_CONTENT_TYPES)


def get_all_templates_for_style(name: str) -> dict[str, PromptTemplate]:
    """
    Get all prompt templates for a given style.

    Args:
        name: Template style name.

    Returns:
        Dict mapping content type to PromptTemplate, or empty dict
        if the style is not registered.
    """
    return dict(TEMPLATE_REGISTRY.get(name, {}))
