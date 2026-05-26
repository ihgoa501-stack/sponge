"""Context compression — token budget enforcement and LLM summarization.

When conversation history exceeds a token budget, old messages are
compressed into a single summary using the LLM itself, keeping recent
messages intact. This reduces input tokens for every subsequent call.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from sponge.llm.base import LLMProvider, Message

logger = logging.getLogger("sponge.core.context")

SUMMARIZE_PROMPT = """Summarize the conversation so far in 2-3 sentences.
Include key facts, decisions, and context. Be concise.
Conversation:
{history}

Summary:"""


class ContextCompressor:
    """Compresses conversation history to fit within a token budget.

    Strategy:
    1. If total tokens ≤ budget, pass through unchanged.
    2. Otherwise, summarize oldest messages via LLM, keep recent ones.
    3. System messages are always preserved at the top.
    """

    def __init__(
        self,
        provider: LLMProvider,
        token_budget: int = 8000,
        keep_recent: int = 10,
        counter: Callable[[str], int] | None = None,
    ) -> None:
        self._provider = provider
        self._token_budget = token_budget
        self._keep_recent = keep_recent
        self._counter = counter  # token_counter.count_tokens or similar

    async def compress(self, messages: list[Message]) -> list[Message]:
        """Compress messages to fit within the token budget.

        Returns a new list of messages that should consume ≤ token_budget tokens.
        """
        total = self._count_tokens(messages)
        if total <= self._token_budget:
            return messages

        # Split: system + old + recent.
        system = [m for m in messages if m.role == "system"]
        other = [m for m in messages if m.role != "system"]

        if len(other) <= self._keep_recent:
            return messages  # nothing to compress

        recent = other[-self._keep_recent :]
        old = other[: -self._keep_recent]

        # Summarize old messages.
        old_text = "\n".join(f"[{m.role}]: {m.content[:500]}" for m in old)
        summary_prompt = SUMMARIZE_PROMPT.format(history=old_text)

        summary = await self._summarize(summary_prompt)

        summary_msg = Message(
            role="assistant",
            content=f"[Summary of earlier conversation]\n{summary}",
        )
        return system + [summary_msg] + recent

    async def _summarize(self, prompt: str) -> str:
        """Call the provider to generate a summary."""
        chunks: list[str] = []
        async for event in self._provider.stream([Message(role="user", content=prompt)]):
            from sponge.llm.base import ContentDelta

            if isinstance(event, ContentDelta):
                chunks.append(event.text)

        return "".join(chunks)

    def _count_tokens(self, messages: list[Message]) -> int:
        """Estimate total tokens across all messages."""
        if self._counter is not None:
            return sum(self._counter(m.content) for m in messages)

        # Fallback: rough character-based estimate (~4 chars/token).
        return sum(max(1, len(m.content) // 4) for m in messages)
