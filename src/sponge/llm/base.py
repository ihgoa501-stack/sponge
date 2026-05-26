"""LLM provider abstract base and stream event types."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from sponge.cost.models import Usage


@dataclass
class Message:
    """A single message in a conversation."""

    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class ContentDelta:
    """A chunk of streaming text content."""

    text: str


@dataclass
class UsageEvent:
    """Final token usage reported at the end of a stream."""

    usage: Usage


# Union type for stream events.
StreamEvent = ContentDelta | UsageEvent


class LLMProvider:
    """Base class for LLM providers.

    All providers must implement stream() which yields StreamEvent
    instances as the model generates output.
    """

    async def stream(
        self,
        messages: list[Message],  # noqa: ARG002
        **kwargs: object,  # noqa: ARG002
    ) -> AsyncIterator[StreamEvent]:
        """Stream responses from the model.

        Args:
            messages: Conversation history.
            **kwargs: Provider-specific options (temperature, max_tokens, etc.).

        Yields:
            ContentDelta for text chunks, UsageEvent at stream end.
        """
        raise NotImplementedError("Subclasses must implement stream()")
        yield  # pragma: no cover
