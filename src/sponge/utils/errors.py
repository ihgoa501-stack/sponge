"""Exception hierarchy for Sponge."""


class SpongeError(Exception):
    """Base exception for all Sponge errors."""


class ConfigError(SpongeError):
    """Configuration errors: missing keys, invalid values, bad TOML."""


class ProviderError(SpongeError):
    """LLM provider errors: auth failure, rate limit, API errors, timeout."""


class CacheError(SpongeError):
    """Cache errors: disk full, corruption, invalid key."""


class BudgetExceededError(SpongeError):
    """Circuit breaker tripped — budget limit reached."""
