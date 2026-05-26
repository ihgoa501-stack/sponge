"""Tests for context compression."""

from sponge.core.context import ContextCompressor
from sponge.llm.base import Message
from tests.mock_provider import MockProvider


async def test_no_compression_when_under_budget() -> None:
    """Messages under budget pass through unchanged."""
    provider = MockProvider()
    compressor = ContextCompressor(provider=provider, token_budget=10000, keep_recent=5)

    messages = [
        Message(role="system", content="You are helpful."),
        Message(role="user", content="Hello"),
        Message(role="assistant", content="Hi there"),
        Message(role="user", content="How are you?"),
    ]

    result = await compressor.compress(messages)
    assert len(result) == len(messages)
    assert result == messages


async def test_compression_when_over_budget() -> None:
    """Long history gets summarized when over budget."""
    # Create a long conversation.
    messages = [Message(role="system", content="You are helpful.")]
    for i in range(20):
        messages.append(Message(role="user", content=f"Question {i} " + "x" * 200))
        messages.append(Message(role="assistant", content=f"Answer {i} " + "y" * 200))

    provider = MockProvider(responses=["A summary of the conversation."])
    compressor = ContextCompressor(
        provider=provider,
        token_budget=200,  # Very small budget to force compression
        keep_recent=4,
    )

    result = await compressor.compress(messages)

    # System message preserved at top.
    assert result[0].role == "system"

    # Summary inserted in the middle.
    assert any("Summary" in m.content for m in result)

    # Recent messages preserved.
    assert len(result) < len(messages)


async def test_keep_recent_preserves_last_n() -> None:
    """Recent messages are kept intact after summary."""
    messages = [Message(role="user", content=f"Turn {i}") for i in range(100)]

    provider = MockProvider(responses=["Summary."])
    compressor = ContextCompressor(provider=provider, token_budget=50, keep_recent=3)

    result = await compressor.compress(messages)

    # Last 3 messages should be preserved as-is.
    assert result[-3:] == messages[-3:]
