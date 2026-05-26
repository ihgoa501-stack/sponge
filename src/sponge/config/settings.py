"""Pydantic settings for Sponge configuration.

Reads from environment variables (SPONGE_*), .env file, and
~/.sponge/config.toml at runtime.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Sponge configuration, loaded from env vars with SPONGE_ prefix."""

    model_config = {"env_prefix": "SPONGE_", "env_file": ".env"}

    # Provider
    provider: str = "anthropic"
    model: str = "claude-sonnet-4"

    # Budget
    budget_per_call: float = 2.00
    budget_per_session: float = 10.00
    max_steps: int = 50

    # Cache
    cache_enabled: bool = True
    cache_ttl_hours: int = 24

    # Context
    context_token_budget: int = 30000

    # Tuning
    tune_window_days: int = 30
    tune_min_samples: int = 10
    tune_confidence_p: float = 0.05
    tune_min_savings_pct: float = 5.0
    tune_shadow_ratio: float = 0.5

    # API keys (loaded from env, never stored in config files)
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    deepseek_api_key: str = ""
