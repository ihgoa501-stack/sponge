"""LLM provider abstract base and stream event types."""

import base64
import mimetypes
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

from sponge.cost.models import Usage


@dataclass
class Message:
    """A single message in a conversation."""

    role: str  # "system", "user", "assistant"
    content: str
    images: list[str] = field(default_factory=list)  # base64 data URIs


def encode_image(path: str | Path) -> str:
    """Encode an image file as a base64 data URI."""
    p = Path(path)
    mime, _ = mimetypes.guess_type(str(p))
    if mime is None:
        mime = "image/png"
    data = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{data}"


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
