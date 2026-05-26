"""Tests for pricing data loader."""

import pytest

from sponge.cost.models import ModelPricing
from sponge.cost.pricing import get_model_pricing
from sponge.utils.errors import ConfigError


def test_get_model_pricing_valid() -> None:
    """Valid provider + model returns ModelPricing."""
    pricing = get_model_pricing("anthropic", "claude-sonnet-4")
    assert isinstance(pricing, ModelPricing)
    assert pricing.input_per_1k > 0
    assert pricing.output_per_1k > 0


def test_get_model_pricing_unknown_provider() -> None:
    """Unknown provider raises ConfigError."""
    with pytest.raises(ConfigError, match="Provider 'nonexistent'"):
        get_model_pricing("nonexistent", "claude-sonnet-4")


def test_get_model_pricing_unknown_model() -> None:
    """Unknown model raises ConfigError."""
    with pytest.raises(ConfigError, match="Model 'nonexistent'"):
        get_model_pricing("anthropic", "nonexistent")


def test_get_model_pricing_all_providers() -> None:
    """Every provider in pricing.toml has at least one loadable model."""
    providers = ["anthropic", "openai", "deepseek"]
    for provider in providers:
        pricing = get_model_pricing(provider, _first_model(provider))
        assert pricing.input_per_1k > 0


def _first_model(provider: str) -> str:
    """Get the first model for a provider."""
    from sponge.cost.pricing import _get_pricing_data

    data = _get_pricing_data()
    return next(iter(data["providers"][provider]["models"]))
