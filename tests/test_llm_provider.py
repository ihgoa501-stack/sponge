"""Tests for LLM provider layer."""

import pytest

from sponge.config.settings import Settings
from sponge.llm.base import ContentDelta, LLMProvider, Message, UsageEvent
from sponge.llm.factory import create_provider
from sponge.utils.errors import ConfigError
from tests.mock_provider import MockProvider


async def test_mock_provider_streams_content() -> None:
    """MockProvider yields ContentDelta then UsageEvent."""
    provider = MockProvider(responses=["Hello world"])
    events = [e async for e in provider.stream([Message(role="user", content="hi")])]
    assert len(events) == 2
    assert isinstance(events[0], ContentDelta)
    assert events[0].text == "Hello world"
    assert isinstance(events[1], UsageEvent)
    assert events[1].usage.tokens_in == 10
    assert events[1].usage.tokens_out == 5


async def test_mock_provider_call_count() -> None:
    """MockProvider tracks call count."""
    provider = MockProvider(responses=["A", "B"])
    assert provider.call_count == 0
    _ = [e async for e in provider.stream([])]
    assert provider.call_count == 1
    _ = [e async for e in provider.stream([])]
    assert provider.call_count == 2


async def test_llm_provider_raises_not_implemented() -> None:
    """LLMProvider.stream() raises NotImplementedError."""
    provider = LLMProvider()
    with pytest.raises(NotImplementedError):
        async for _ in provider.stream([]):
            pass


def test_create_provider_unknown() -> None:
    """Unknown provider raises ConfigError."""
    settings = Settings(provider="unknown")
    with pytest.raises(ConfigError, match="Unknown provider"):
        create_provider(settings)


def test_create_provider_anthropic_without_key() -> None:
    """Anthropic provider is created but stream fails without API key."""
    settings = Settings(provider="anthropic", anthropic_api_key="")
    provider = create_provider(settings)
    assert provider is not None
