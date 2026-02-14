"""
Tests for ecomm_core shared package.

Verifies that core modules are importable and basic functionality works.
"""

import uuid

import pytest

from ecomm_core.auth.service import hash_password, verify_password, create_access_token, decode_token
from ecomm_core.config import BaseServiceConfig
from ecomm_core.health import create_health_router
from ecomm_core.models import Base, User, PlanTier, ApiKey, Subscription, SubscriptionStatus
from ecomm_core.plans import PlanLimits, create_default_plan_limits, resolve_plan_from_price_id
from ecomm_core.schemas import RegisterRequest, TokenResponse, UserResponse, PlanInfo
from ecomm_core.llm_client import call_llm_mock
from ecomm_core.middleware import setup_cors


class TestPasswordHashing:
    """Test bcrypt password hashing and verification."""

    def test_hash_and_verify(self):
        """Password should verify against its own hash."""
        pw = "testpassword123"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed)

    def test_wrong_password_fails(self):
        """Wrong password should not verify."""
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)

    def test_hash_is_different_each_time(self):
        """Hashing same password should produce different salted hashes."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2


class TestJWT:
    """Test JWT token creation and decoding."""

    def test_create_and_decode_access_token(self):
        """Access token should round-trip through create/decode."""
        user_id = uuid.uuid4()
        token = create_access_token(user_id, secret_key="test-secret")
        payload = decode_token(token, secret_key="test-secret")
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_decode_with_wrong_key_fails(self):
        """Token decoded with wrong key should return None."""
        user_id = uuid.uuid4()
        token = create_access_token(user_id, secret_key="key1")
        payload = decode_token(token, secret_key="key2")
        assert payload is None

    def test_decode_garbage_returns_none(self):
        """Garbage token should return None, not raise."""
        assert decode_token("not.a.token", secret_key="key") is None


class TestConfig:
    """Test BaseServiceConfig."""

    def test_default_values(self):
        """Config should have sensible defaults."""
        config = BaseServiceConfig()
        assert config.service_name == "service"
        assert config.jwt_algorithm == "HS256"
        assert config.jwt_access_token_expire_minutes == 15

    def test_cors_origins_list(self):
        """CORS origins string should parse to list."""
        config = BaseServiceConfig(cors_origins="http://a.com, http://b.com")
        assert config.cors_origins_list == ["http://a.com", "http://b.com"]


class TestPlanLimits:
    """Test plan limits and resolution."""

    def test_create_default_limits(self):
        """Default limits should have three tiers."""
        limits = create_default_plan_limits()
        assert PlanTier.free in limits
        assert PlanTier.pro in limits
        assert PlanTier.enterprise in limits
        assert limits[PlanTier.free].max_items == 10
        assert limits[PlanTier.enterprise].max_items == -1

    def test_resolve_price_id(self):
        """Should resolve price ID back to plan tier."""
        limits = create_default_plan_limits()
        # Set a price ID
        limits[PlanTier.pro] = PlanLimits(
            max_items=100, max_secondary=500, price_monthly_cents=2900,
            stripe_price_id="price_pro_123", trial_days=14, api_access=True,
        )
        assert resolve_plan_from_price_id(limits, "price_pro_123") == PlanTier.pro
        assert resolve_plan_from_price_id(limits, "unknown") is None


class TestModels:
    """Test that models are importable and have correct table names."""

    def test_user_tablename(self):
        assert User.__tablename__ == "users"

    def test_api_key_tablename(self):
        assert ApiKey.__tablename__ == "api_keys"

    def test_subscription_tablename(self):
        assert Subscription.__tablename__ == "subscriptions"

    def test_plan_tier_values(self):
        assert PlanTier.free.value == "free"
        assert PlanTier.pro.value == "pro"
        assert PlanTier.enterprise.value == "enterprise"


class TestSchemas:
    """Test that schemas validate correctly."""

    def test_register_request_valid(self):
        req = RegisterRequest(email="test@example.com", password="12345678")
        assert req.email == "test@example.com"

    def test_register_request_short_password(self):
        with pytest.raises(Exception):
            RegisterRequest(email="test@example.com", password="short")

    def test_token_response(self):
        resp = TokenResponse(access_token="a", refresh_token="r")
        assert resp.token_type == "bearer"


class TestHealthRouter:
    """Test health check router factory."""

    def test_creates_router(self):
        router = create_health_router("test-service")
        routes = [r.path for r in router.routes]
        assert "/health" in routes


@pytest.mark.asyncio
async def test_llm_mock_client():
    """Test mock LLM client returns expected format."""
    result = await call_llm_mock("test prompt")
    assert result["provider"] == "mock"
    assert result["content"] == "Mock LLM response for testing."
    assert result["cost_usd"] == 0.0
