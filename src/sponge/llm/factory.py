"""Provider factory — creates LLM providers from configuration."""

from sponge.config.settings import Settings
from sponge.llm.base import LLMProvider
from sponge.utils.errors import ConfigError


def create_provider(settings: Settings) -> LLMProvider:
    """Create an LLM provider from settings."""
    provider_name = settings.provider.lower()

    if provider_name == "anthropic":
        from sponge.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(settings)

    if provider_name == "openai":
        from sponge.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(settings)

    if provider_name == "deepseek":
        from sponge.llm.deepseek_provider import DeepSeekProvider

        return DeepSeekProvider(settings)

    if provider_name == "openrouter":
        from sponge.llm.openrouter_provider import OpenRouterProvider

        return OpenRouterProvider(settings)

    raise ConfigError(
        f"Unknown provider '{settings.provider}'."
        " Supported: anthropic, openai, deepseek, openrouter"
    )
