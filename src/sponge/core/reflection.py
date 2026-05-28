"""Reflection — the bronze mirror that asks questions, not gives answers.

Core philosophy: when the agent fails, it doesn't just retry blindly. It looks
into the mirror (a separate LLM call with a Socratic evaluation prompt), extracts
a lesson from the failure, and stores it for next time. The same mistake is never
paid for twice.

The mirror metaphor: the LLM reflecting on its own trajectory is the same LLM that
ran it. What changes is the *prompt* (from "solve this task" to "diagnose why you
failed") and the *output* (from an action to a lesson).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from sponge.llm.base import ContentDelta, LLMProvider, Message, UsageEvent
from sponge.llm.token_counter import count_tokens

logger = logging.getLogger("sponge.core.reflection")

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ReflectionResult:
    """Structured self-evaluation produced by the bronze mirror."""

    root_cause: str
    """What specifically went wrong — the proximate cause."""

    contributing_factors: list[str] = field(default_factory=list)
    """Other factors that contributed to the failure."""

    novel_pattern: bool = True
    """Is this a new class of mistake, or a recurrence of a known pattern?"""

    preventive_rule: str = ""
    """One compact rule that would have prevented this failure."""

    severity: str = "medium"
    """low | medium | high — how costly was this failure?"""

    confidence: float = 0.0
    """How confident is the reflection in its diagnosis? (0.0–1.0)"""


@dataclass
class Lesson:
    """A compact, retrievable rule extracted from a failure.

    This is the "carving on the wooden pillar" — stored in ReflectiveMemory
    and retrieved before similar future tasks.
    """

    condition: str
    """When does this lesson apply? (task type, tool, context pattern)."""

    action: str
    """What was attempted that led to the failure?"""

    observed_outcome: str
    """What went wrong?"""

    lesson: str
    """What rule should be followed to prevent recurrence?"""

    severity: str = "medium"
    """low | medium | high."""

    id: str = ""
    """Unique identifier, assigned on storage."""

    def to_context_line(self) -> str:
        """Render as a single line for system prompt injection."""
        return f"[{self.id}] {self.lesson}"


# ---------------------------------------------------------------------------
# Socratic reflection prompt
# ---------------------------------------------------------------------------

_REFLECTION_SYSTEM_PROMPT = """You are a diagnostic evaluator — a bronze mirror for an AI agent. Your role is NOT to solve
tasks or provide answers. Your role is to ask questions that help locate the root cause
of a failure.

You will receive the trajectory of a failed task attempt:
- The original task
- What the agent did (tool calls, reasoning)
- What went wrong (the failure signal)

Analyze the trajectory and produce a JSON response with these fields:

{
  "root_cause": "One sentence describing what specifically went wrong.",
  "contributing_factors": ["Factor 1", "Factor 2"],
  "novel_pattern": true,
  "preventive_rule": "One compact rule that would have prevented this. 20-80 chars.",
  "severity": "low",
  "confidence": 0.85
}

Rules:
- root_cause: be specific. Not 'the agent made a mistake' but 'the agent edited
  test_auth.py without first reading the file, so it missed the existing mock setup.'
- contributing_factors: list environmental or contextual factors (wrong assumptions,
  missing context, tool misuse, insufficient exploration).
- novel_pattern: true if this is a fundamentally new kind of error; false if it's a
  variation of a pattern the agent has seen before (even if the agent doesn't remember).
- preventive_rule: a single, actionable sentence the agent can follow next time.
  Like A-Jiu carving one lesson per failure onto his wooden pillar. Max 80 chars.
- severity: low (cosmetic, no rework needed), medium (required rework but no data loss),
  high (caused data loss, test breakage, or user had to intervene).
- confidence: 0.0–1.0 how certain you are in the diagnosis. Below 0.5 means 'uncertain'
  and the lesson should not be stored.

Do NOT include any text outside the JSON. Do NOT apologize. Do NOT suggest fixes —
just diagnose what went wrong and extract the lesson."""


def _build_reflection_messages(
    task_prompt: str,
    messages: list[Message],
    response: str,
    failure_reason: str,
) -> list[Message]:
    """Build the messages for a reflection call."""

    # Truncate long responses to keep reflection cheap.
    messages_summary = _summarize_messages(messages)
    response_truncated = response[:2000] if len(response) > 2000 else response

    user_content = f"""## Original Task
{task_prompt}

## Agent-Agent Conversation
{messages_summary}

## Agent's Final Response
{response_truncated}

## Failure Signal
{failure_reason}

Diagnose what went wrong and extract a lesson. Output ONLY the JSON."""

    return [
        Message(role="system", content=_REFLECTION_SYSTEM_PROMPT),
        Message(role="user", content=user_content),
    ]


def _summarize_messages(messages: list[Message], max_chars: int = 3000) -> str:
    """Compress a message list into a compact summary for the reflection prompt."""
    parts: list[str] = []
    total = 0
    for m in messages:
        role = m.role
        content = m.content[:500] if len(m.content) > 500 else m.content
        parts.append(f"[{role}] {content}")
        total += len(content)
        if total > max_chars:
            parts.append("... [remaining messages truncated]")
            break
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Reflection module
# ---------------------------------------------------------------------------


class ReflectionModule:
    """The bronze mirror — generates structured self-evaluation after failure.

    Uses a separate LLM call with a Socratic evaluation prompt. Does not give
    answers; asks questions that force the agent to locate the root cause.
    """

    # Approximate token cost of a reflection call.
    # System prompt ~300 tokens + trajectory ~800 tokens + output ~150 tokens.
    ESTIMATED_TOKENS = 500

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def reflect(
        self,
        task_prompt: str,
        messages: list[Message],
        response: str,
        failure_reason: str,
        model: str | None = None,
    ) -> ReflectionResult | None:
        """Run the bronze mirror on a failed trajectory.

        Args:
            task_prompt: The original task the agent was trying to do.
            messages: The conversation messages sent to the agent.
            response: The agent's final response.
            failure_reason: Why we consider this a failure (user correction,
                            tool error, quality flag, etc.).
            model: Optional model override for the reflection call.

        Returns:
            A ReflectionResult with diagnosis and lesson, or None if reflection
            failed (parse error, provider error, low confidence).
        """
        reflection_messages = _build_reflection_messages(
            task_prompt, messages, response, failure_reason
        )

        try:
            chunks: list[str] = []
            async for event in self._provider.stream(
                reflection_messages, model=model
            ):
                match event:
                    case ContentDelta(text=text):
                        chunks.append(text)
                    case UsageEvent():  # noqa
                        pass

            raw = "".join(chunks).strip()

            # Extract JSON from the response (may have markdown fences).
            result = _parse_reflection_json(raw)
            if result is None:
                logger.warning("Failed to parse reflection JSON: %s", raw[:200])
                return None

            if result.confidence < 0.5:
                logger.info(
                    "Reflection confidence too low (%.2f), discarding", result.confidence
                )
                return None

            return result

        except Exception:
            logger.warning("Reflection call failed", exc_info=True)
            return None


def _parse_reflection_json(raw: str) -> ReflectionResult | None:
    """Parse the LLM's JSON response into a ReflectionResult.

    Handles markdown code fences and common LLM formatting quirks.
    """
    # Strip markdown fences.
    text = raw.strip()
    if text.startswith("```"):
        # Find the first newline after the opening fence.
        nl = text.find("\n")
        if nl != -1:
            text = text[nl + 1 :]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find a JSON object in the text.
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None

    return ReflectionResult(
        root_cause=data.get("root_cause", ""),
        contributing_factors=data.get("contributing_factors", []),
        novel_pattern=data.get("novel_pattern", True),
        preventive_rule=data.get("preventive_rule", ""),
        severity=data.get("severity", "medium"),
        confidence=data.get("confidence", 0.0),
    )


# ---------------------------------------------------------------------------
# Lesson extraction
# ---------------------------------------------------------------------------


def extract_lesson(
    reflection: ReflectionResult,
    task_prompt: str,
    condition_tags: list[str] | None = None,
) -> Lesson:
    """Extract a compact, retrievable Lesson from a ReflectionResult.

    The lesson format is: condition → action → observed_outcome → lesson.
    This is the "carving on the pillar" — immutable once written.

    Args:
        reflection: The structured self-evaluation.
        task_prompt: The original task (used to build condition context).
        condition_tags: Optional tags for condition-keyed retrieval
                        (e.g. ["file_edit", "test_breakage"]).

    Returns:
        A Lesson ready for storage in ReflectiveMemory.
    """
    # Derive condition from task prompt + tags.
    condition_parts: list[str] = []
    if condition_tags:
        condition_parts.extend(condition_tags)
    # Use first ~80 chars of task as context.
    context = task_prompt[:80].strip()
    if context:
        condition_parts.append(context)
    condition = " | ".join(condition_parts) if condition_parts else "general"

    return Lesson(
        condition=condition,
        action=task_prompt[:200],
        observed_outcome=reflection.root_cause,
        lesson=reflection.preventive_rule,
        severity=reflection.severity,
    )
