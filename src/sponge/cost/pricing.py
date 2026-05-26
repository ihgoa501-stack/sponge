"""Pricing data loader.

Reads provider pricing from src/sponge/data/pricing.toml and returns
ModelPricing instances. Never hardcodes provider prices.
"""

from __future__ import annotations

import tomllib
from importlib import resources
from pathlib import Path
from typing import Any

from sponge.cost.models import ModelPricing
from sponge.utils.errors import ConfigError


def _load_pricing_data() -> dict[str, Any]:
    """Load the raw pricing TOML data."""
    # Try importlib.resources first (works when installed as package)
    try:
        ref = resources.files("sponge.data").joinpath("pricing.toml")
        if ref.is_file():
            return tomllib.loads(ref.read_text())
    except (ModuleNotFoundError, FileNotFoundError, TypeError):
        pass

    # Fallback: look relative to this file (dev mode)
    candidate = Path(__file__).resolve().parent.parent / "data" / "pricing.toml"
    if candidate.is_file():
        return tomllib.loads(candidate.read_text())

    raise ConfigError("Cannot find pricing.toml. Expected at src/sponge/data/pricing.toml.")


# Cache the parsed data so we only read the file once.
_pricing_cache: dict[str, Any] | None = None


def _get_pricing_data() -> dict[str, Any]:
    global _pricing_cache
    if _pricing_cache is None:
        _pricing_cache = _load_pricing_data()
    return _pricing_cache


def get_model_pricing(provider: str, model: str) -> ModelPricing:
    """Return pricing for a specific provider + model combination.

    Args:
        provider: Provider name (anthropic, openai, deepseek).
        model: Model identifier (claude-sonnet-4, gpt-4o, etc.).

    Returns:
        ModelPricing with per-1k token costs.

    Raises:
        ConfigError: If the provider or model is not found in pricing.toml.
    """
    data = _get_pricing_data()
    providers = data.get("providers", {})

    if provider not in providers:
        raise ConfigError(
            f"Provider '{provider}' not found in pricing.toml. Available: {', '.join(providers)}"
        )

    models = providers[provider].get("models", {})
    if model not in models:
        raise ConfigError(
            f"Model '{model}' not found for provider '{provider}' in "
            f"pricing.toml. Available: {', '.join(models)}"
        )

    p = models[model]
    return ModelPricing(
        input_per_1k=p["input"],
        output_per_1k=p["output"],
        cache_write_per_1k=p.get("cache_write"),
        cache_read_per_1k=p.get("cache_read"),
    )
