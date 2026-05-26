"""Mock LLM provider for testing.

Provides a controllable LLMProvider that returns preset responses
without making real API calls.
"""

from collections.abc import AsyncIterator

from sponge.cost.models import Usage
from sponge.llm.base import ContentDelta, LLMProvider, Message, UsageEvent


class MockProvider(LLMProvider):
    """Fake provider that streams preset responses."""

    def __init__(
        self,
        responses: list[str] | None = None,
        tokens_in: int = 10,
        tokens_out: int = 5,
    ) -> None:
        self.responses = responses or ["Hello from mock!"]
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.call_count = 0

    async def stream(
        self,
        messages: list[Message],  # noqa: ARG002
        **kwargs: object,  # noqa: ARG002
    ) -> AsyncIterator[ContentDelta | UsageEvent]:
        self.call_count += 1
        text = self.responses[min(self.call_count - 1, len(self.responses) - 1)]
        yield ContentDelta(text=text)
        yield UsageEvent(usage=Usage(tokens_in=self.tokens_in, tokens_out=self.tokens_out))
