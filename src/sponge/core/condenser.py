"""Sub-Agent Condenser — compress exploration into structured summaries.

When a sub-agent explores code (search, read files, run tests), it produces
large amounts of raw output. The condenser compresses this into a structured
summary with source references, reducing 50K tokens to ~500 tokens.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from sponge.llm.base import ContentDelta, LLMProvider, Message

logger = logging.getLogger("sponge.core.condenser")

CONDENSE_PROMPT = """Condense the following exploration output into a structured summary.
Return ONLY valid JSON — no other text.

Format:
{{
  "summary": "one-sentence summary of findings",
  "findings": [
    {{"file": "f.py", "line": 42, "finding": "what", "confidence": "high"}}
  ],
  "key_insight": "the most important takeaway",
  "raw_tokens": {raw_tokens},
  "condensed_tokens_estimate": {condensed_estimate}
}}

Exploration output:
{output}"""


@dataclass
class Finding:
    """A single finding from exploration."""

    file: str
    line: int = 0
    finding: str = ""
    confidence: str = "medium"


@dataclass
class CondensedResult:
    """Structured summary of exploration output."""

    summary: str = ""
    findings: list[Finding] = field(default_factory=list)
    key_insight: str = ""
    raw_tokens: int = 0
    condensed_tokens: int = 0
    compression_ratio: float = 0.0


class SubAgentCondenser:
    """Compresses raw exploration output into structured summaries.

    Uses the LLM to extract findings with file:line references, discarding
    irrelevant output. Target: 10-100× compression.
    """

    def __init__(self, provider: LLMProvider, min_raw_tokens: int = 2000) -> None:
        self._provider = provider
        self._min_raw_tokens = min_raw_tokens  # only condense if above this

    def should_condense(self, raw_output: str) -> bool:
        """Only condense if output is large enough to justify the overhead."""
        return len(raw_output.split()) > self._min_raw_tokens // 4

    async def condense(self, raw_output: str) -> CondensedResult:
        """Compress raw exploration into a structured summary.

        Args:
            raw_output: Raw text from sub-agent exploration.

        Returns:
            CondensedResult with structured findings and compression stats.
        """
        raw_tokens = len(raw_output) // 4  # rough estimate

        if not self.should_condense(raw_output):
            return CondensedResult(
                summary=raw_output[:500],
                raw_tokens=raw_tokens,
                condensed_tokens=min(raw_tokens, 125),
                compression_ratio=1.0,
            )

        prompt = CONDENSE_PROMPT.format(
            output=raw_output[:8000],  # truncate very long output
            raw_tokens=raw_tokens,
            condensed_estimate=max(100, raw_tokens // 20),
        )

        response = await self._call_llm(prompt)

        try:
            data = json.loads(response)
            findings = [
                Finding(
                    file=f.get("file", ""),
                    line=f.get("line", 0),
                    finding=f.get("finding", ""),
                    confidence=f.get("confidence", "medium"),
                )
                for f in data.get("findings", [])
            ]
            result = CondensedResult(
                summary=data.get("summary", ""),
                findings=findings,
                key_insight=data.get("key_insight", ""),
                raw_tokens=raw_tokens,
                condensed_tokens=len(response) // 4,
                compression_ratio=(raw_tokens / max(len(response) // 4, 1)),
            )
            logger.info(
                "Condensed %d → %d tokens (%.0f×)",
                result.raw_tokens,
                result.condensed_tokens,
                result.compression_ratio,
            )
            return result
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Condensation failed: %s", e)
            return CondensedResult(
                summary=raw_output[:500],
                raw_tokens=raw_tokens,
                condensed_tokens=min(raw_tokens, 125),
                compression_ratio=1.0,
            )

    async def _call_llm(self, prompt: str) -> str:
        """Make a short LLM call for condensation."""
        chunks: list[str] = []
        async for event in self._provider.stream([Message(role="user", content=prompt)]):
            if isinstance(event, ContentDelta):
                chunks.append(event.text)
        return "".join(chunks)
