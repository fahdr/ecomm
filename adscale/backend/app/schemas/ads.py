"""
Ad management schemas for AdScale.

Defines Pydantic v2 request/response models for ad accounts, campaigns,
ad groups, creatives, metrics, and optimization rules.

For Developers:
    All schemas use `model_config = {"from_attributes": True}` for ORM
    compatibility. Create/Update schemas omit server-generated fields.
    Pagination uses offset/limit with a `PaginatedResponse` wrapper.

For QA Engineers:
    Test validation: required fields missing (422), invalid enum values,
    negative budgets, and date range consistency (start_date < end_date).

For Project Managers:
    These schemas define the exact shape of API request and response data.
    They enforce data integrity before anything reaches the database.

For End Users:
    The API validates your input and returns clear error messages
    if something is incorrect (e.g., budget must be positive).
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.ad_account import AccountStatus, AdPlatform
from app.models.ad_creative import CreativeStatus
from app.models.ad_group import AdGroupStatus, BidStrategy
from app.models.campaign import CampaignObjective, CampaignStatus
from app.models.optimization_rule import RuleType


# ── Pagination ────────────────────────────────────────────────────────


class PaginatedResponse(BaseModel):
    """
    Generic paginated response wrapper.

    Attributes:
        items: List of items for the current page.
        total: Total number of matching items across all pages.
        offset: Current page offset.
        limit: Maximum items per page.
    """

    items: list
    total: int
    offset: int
    limit: int


# ── Ad Account Schemas ────────────────────────────────────────────────


class AdAccountConnect(BaseModel):
    """
    Request to connect a new ad account.

    Attributes:
        platform: Advertising platform to connect (google or meta).
        account_id_external: The platform's account identifier.
        account_name: Human-readable name for the account.
        access_token: OAuth access token (optional, mock in dev).
    """

    platform: AdPlatform
    account_id_external: str = Field(..., min_length=1, max_length=255)
    account_name: str = Field(..., min_length=1, max_length=255)
    access_token: str | None = None


class AdAccountResponse(BaseModel):
    """
    Ad account response with connection details.

    Attributes:
        id: Account record UUID.
        user_id: Owning user UUID.
        platform: Advertising platform.
        account_id_external: External platform account ID.
        account_name: Human-readable account name.
        is_connected: Whether the account is currently connected.
        status: Connection health status.
        connected_at: When the account was first connected.
        created_at: Record creation timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    platform: AdPlatform
    account_id_external: str
    account_name: str
    is_connected: bool
    status: AccountStatus
    connected_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Campaign Schemas ──────────────────────────────────────────────────


class CampaignCreate(BaseModel):
    """
    Request to create a new campaign.

    Attributes:
        ad_account_id: UUID of the ad account to run the campaign on.
        name: Campaign name.
        objective: Optimization objective (traffic, conversions, awareness, sales).
        budget_daily: Daily budget in USD (optional).
        budget_lifetime: Lifetime budget in USD (optional).
        status: Initial status (default: draft).
        start_date: Campaign start date (optional).
        end_date: Campaign end date (optional).
    """

    ad_account_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    objective: CampaignObjective
    budget_daily: float | None = Field(None, ge=0)
    budget_lifetime: float | None = Field(None, ge=0)
    status: CampaignStatus = CampaignStatus.draft
    start_date: date | None = None
    end_date: date | None = None


class CampaignUpdate(BaseModel):
    """
    Request to update an existing campaign.

    All fields are optional — only provided fields are updated.

    Attributes:
        name: Updated campaign name.
        objective: Updated objective.
        budget_daily: Updated daily budget.
        budget_lifetime: Updated lifetime budget.
        status: Updated campaign status.
        start_date: Updated start date.
        end_date: Updated end date.
    """

    name: str | None = Field(None, min_length=1, max_length=255)
    objective: CampaignObjective | None = None
    budget_daily: float | None = Field(None, ge=0)
    budget_lifetime: float | None = Field(None, ge=0)
    status: CampaignStatus | None = None
    start_date: date | None = None
    end_date: date | None = None


class CampaignResponse(BaseModel):
    """
    Campaign response with all fields.

    Attributes:
        id: Campaign UUID.
        user_id: Owning user UUID.
        ad_account_id: Associated ad account UUID.
        name: Campaign name.
        platform: Advertising platform.
        objective: Optimization objective.
        budget_daily: Daily budget in USD.
        budget_lifetime: Lifetime budget in USD.
        status: Current campaign status.
        start_date: Campaign start date.
        end_date: Campaign end date.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    ad_account_id: uuid.UUID
    name: str
    platform: str
    objective: CampaignObjective
    budget_daily: float | None
    budget_lifetime: float | None
    status: CampaignStatus
    start_date: date | None
    end_date: date | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Ad Group Schemas ──────────────────────────────────────────────────


class AdGroupCreate(BaseModel):
    """
    Request to create a new ad group within a campaign.

    Attributes:
        campaign_id: UUID of the parent campaign.
        name: Ad group name.
        targeting: JSON dict with audience targeting parameters.
        bid_strategy: Bidding optimization strategy.
        bid_amount: Manual bid amount in USD (optional).
        status: Initial status (default: active).
    """

    campaign_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    targeting: dict = Field(default_factory=dict)
    bid_strategy: BidStrategy = BidStrategy.auto_cpc
    bid_amount: float | None = Field(None, ge=0)
    status: AdGroupStatus = AdGroupStatus.active


class AdGroupUpdate(BaseModel):
    """
    Request to update an existing ad group.

    All fields are optional — only provided fields are updated.

    Attributes:
        name: Updated ad group name.
        targeting: Updated targeting parameters.
        bid_strategy: Updated bid strategy.
        bid_amount: Updated bid amount.
        status: Updated status.
    """

    name: str | None = Field(None, min_length=1, max_length=255)
    targeting: dict | None = None
    bid_strategy: BidStrategy | None = None
    bid_amount: float | None = Field(None, ge=0)
    status: AdGroupStatus | None = None


class AdGroupResponse(BaseModel):
    """
    Ad group response with all fields.

    Attributes:
        id: Ad group UUID.
        campaign_id: Parent campaign UUID.
        name: Ad group name.
        targeting: Audience targeting parameters.
        bid_strategy: Bidding strategy.
        bid_amount: Manual bid amount (nullable).
        status: Current status.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
    """

    id: uuid.UUID
    campaign_id: uuid.UUID
    name: str
    targeting: dict
    bid_strategy: BidStrategy
    bid_amount: float | None
    status: AdGroupStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Ad Creative Schemas ───────────────────────────────────────────────


class CreativeCreate(BaseModel):
    """
    Request to create a new ad creative.

    Attributes:
        ad_group_id: UUID of the parent ad group.
        headline: Ad headline text.
        description: Ad body/description text.
        image_url: URL to the ad image asset (optional).
        destination_url: Landing page URL.
        call_to_action: CTA button text.
        status: Initial status (default: active).
    """

    ad_group_id: uuid.UUID
    headline: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=1024)
    image_url: str | None = None
    destination_url: str = Field(..., min_length=1, max_length=1024)
    call_to_action: str = Field(default="Shop Now", max_length=50)
    status: CreativeStatus = CreativeStatus.active


class CreativeUpdate(BaseModel):
    """
    Request to update an existing ad creative.

    All fields are optional — only provided fields are updated.

    Attributes:
        headline: Updated headline.
        description: Updated description.
        image_url: Updated image URL.
        destination_url: Updated landing page URL.
        call_to_action: Updated CTA text.
        status: Updated status.
    """

    headline: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1, max_length=1024)
    image_url: str | None = None
    destination_url: str | None = Field(None, min_length=1, max_length=1024)
    call_to_action: str | None = Field(None, max_length=50)
    status: CreativeStatus | None = None


class CreativeResponse(BaseModel):
    """
    Ad creative response with all fields.

    Attributes:
        id: Creative UUID.
        ad_group_id: Parent ad group UUID.
        headline: Ad headline text.
        description: Ad description text.
        image_url: Image URL (nullable).
        destination_url: Landing page URL.
        call_to_action: CTA button text.
        status: Creative status.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
    """

    id: uuid.UUID
    ad_group_id: uuid.UUID
    headline: str
    description: str
    image_url: str | None
    destination_url: str
    call_to_action: str
    status: CreativeStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GenerateCopyRequest(BaseModel):
    """
    Request to generate AI ad copy.

    Attributes:
        product_name: Name of the product to advertise.
        product_description: Brief product description for context.
        target_audience: Description of the target audience (optional).
        tone: Desired tone of voice (optional, e.g., "professional", "playful").
    """

    product_name: str = Field(..., min_length=1, max_length=255)
    product_description: str = Field(..., min_length=1, max_length=1024)
    target_audience: str | None = None
    tone: str | None = None


class GenerateCopyResponse(BaseModel):
    """
    AI-generated ad copy response.

    Attributes:
        headline: Generated ad headline.
        description: Generated ad description.
        call_to_action: Suggested CTA text.
    """

    headline: str
    description: str
    call_to_action: str


# ── Campaign Metrics Schemas ──────────────────────────────────────────


class MetricsResponse(BaseModel):
    """
    Campaign metrics response with calculated performance fields.

    Attributes:
        id: Metric record UUID.
        campaign_id: Associated campaign UUID.
        date: Date the metrics apply to.
        impressions: Number of ad impressions.
        clicks: Number of ad clicks.
        conversions: Number of conversions.
        spend: Total ad spend in USD.
        revenue: Total attributed revenue in USD.
        roas: Return on ad spend (revenue/spend).
        cpa: Cost per acquisition (spend/conversions).
        ctr: Click-through rate percentage (clicks/impressions * 100).
        created_at: Record creation timestamp.
    """

    id: uuid.UUID
    campaign_id: uuid.UUID
    date: date
    impressions: int
    clicks: int
    conversions: int
    spend: float
    revenue: float
    roas: float | None
    cpa: float | None
    ctr: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MetricsOverview(BaseModel):
    """
    Aggregated metrics overview across all campaigns.

    Attributes:
        total_spend: Sum of all campaign spend.
        total_revenue: Sum of all campaign revenue.
        total_impressions: Sum of all impressions.
        total_clicks: Sum of all clicks.
        total_conversions: Sum of all conversions.
        avg_roas: Average return on ad spend.
        avg_ctr: Average click-through rate.
        avg_cpa: Average cost per acquisition.
    """

    total_spend: float
    total_revenue: float
    total_impressions: int
    total_clicks: int
    total_conversions: int
    avg_roas: float | None
    avg_ctr: float | None
    avg_cpa: float | None


# ── Optimization Rule Schemas ─────────────────────────────────────────


class RuleCreate(BaseModel):
    """
    Request to create a new optimization rule.

    Attributes:
        name: Human-readable rule name.
        rule_type: Type of optimization action.
        conditions: JSON dict with evaluation conditions.
        threshold: Numeric threshold for the rule condition.
        is_active: Whether the rule starts enabled (default: True).
    """

    name: str = Field(..., min_length=1, max_length=255)
    rule_type: RuleType
    conditions: dict = Field(default_factory=dict)
    threshold: float
    is_active: bool = True


class RuleUpdate(BaseModel):
    """
    Request to update an existing optimization rule.

    All fields are optional — only provided fields are updated.

    Attributes:
        name: Updated rule name.
        rule_type: Updated rule type.
        conditions: Updated conditions.
        threshold: Updated threshold.
        is_active: Updated active state.
    """

    name: str | None = Field(None, min_length=1, max_length=255)
    rule_type: RuleType | None = None
    conditions: dict | None = None
    threshold: float | None = None
    is_active: bool | None = None


class RuleResponse(BaseModel):
    """
    Optimization rule response with execution history.

    Attributes:
        id: Rule UUID.
        user_id: Owning user UUID.
        name: Rule name.
        rule_type: Optimization action type.
        conditions: Evaluation conditions.
        threshold: Numeric threshold value.
        is_active: Whether the rule is enabled.
        last_executed: Timestamp of last execution (nullable).
        executions_count: Total execution count.
        created_at: Record creation timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    rule_type: RuleType
    conditions: dict
    threshold: float
    is_active: bool
    last_executed: datetime | None
    executions_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RuleExecutionResult(BaseModel):
    """
    Result of executing an optimization rule.

    Attributes:
        rule_id: UUID of the executed rule.
        campaigns_affected: Number of campaigns that were modified.
        actions_taken: List of action descriptions.
    """

    rule_id: uuid.UUID
    campaigns_affected: int
    actions_taken: list[str]
