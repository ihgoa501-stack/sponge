"""Task Decomposer — break complex tasks into focused sub-tasks.

Uses the LLM to split a large task into smaller, independent sub-tasks.
Each sub-task carries only the context it needs, reducing token consumption
by 5-10× per sub-task compared to sending full history.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from sponge.llm.base import ContentDelta, LLMProvider, Message

logger = logging.getLogger("sponge.core.decomposer")

DECOMPOSE_PROMPT = """Break this task into smaller, independent sub-tasks.
Each sub-task should be self-contained with minimal context needs.
Return ONLY valid JSON — no other text.

Task: {task}

Format:
{{"sub_tasks": [
  {{"id": 1, "description": "...", "context_hint": "what files/context this needs"}}
]}}

If this task is already simple (one step, minimal context), return:
{{"sub_tasks": [{{"id": 1, "description": "same as task", "context_hint": "none"}}]}}"""


@dataclass
class SubTask:
    """A single decomposed sub-task."""

    id: int
    description: str
    context_hint: str = ""
    result: str = ""
    tokens_used: int = 0
    cost: float = 0.0


@dataclass
class DecomposeResult:
    """Result of task decomposition."""

    original: str
    sub_tasks: list[SubTask] = field(default_factory=list)
    decomposition_cost: float = 0.0
    was_decomposed: bool = False


class TaskDecomposer:
    """Breaks complex tasks into sub-tasks using the LLM.

    Only decomposes if the task is estimated to be complex enough
    (heuristic: >100 chars or contains keywords like "refactor", "implement",
    "migrate", "add tests for", "fix all").
    """

    COMPLEXITY_KEYWORDS = [
        "refactor",
        "implement",
        "migrate",
        "rewrite",
        "restructure",
        "add tests for",
        "fix all",
        "convert",
        "extract",
        "split",
        "create module",
        "rename across",
        "replace all",
    ]

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def should_decompose(self, task: str) -> bool:
        """Heuristic: decide if a task is complex enough to decompose."""
        if len(task) < 50:
            return False
        task_lower = task.lower()
        return any(kw in task_lower for kw in self.COMPLEXITY_KEYWORDS)

    async def decompose(self, task: str) -> DecomposeResult:
        """Decompose a complex task into sub-tasks.

        Returns a DecomposeResult. If the task is simple or decomposition
        fails, returns the original task as a single sub-task.
        """
        if not self.should_decompose(task):
            return DecomposeResult(
                original=task,
                sub_tasks=[SubTask(id=1, description=task)],
                was_decomposed=False,
            )

        prompt = DECOMPOSE_PROMPT.format(task=task)
        response = await self._call_llm(prompt)

        try:
            data = json.loads(response)
            sub_tasks = [
                SubTask(
                    id=st["id"],
                    description=st["description"],
                    context_hint=st.get("context_hint", ""),
                )
                for st in data.get("sub_tasks", [])
            ]
            if not sub_tasks:
                raise ValueError("No sub_tasks in response")

            logger.info(
                "Decomposed '%s...' into %d sub-tasks",
                task[:40],
                len(sub_tasks),
            )
            return DecomposeResult(
                original=task,
                sub_tasks=sub_tasks,
                was_decomposed=True,
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Decomposition failed: %s — falling back to single task", e)
            return DecomposeResult(
                original=task,
                sub_tasks=[SubTask(id=1, description=task)],
                was_decomposed=False,
            )

    async def _call_llm(self, prompt: str) -> str:
        """Make a short LLM call for decomposition."""
        chunks: list[str] = []
        async for event in self._provider.stream([Message(role="user", content=prompt)]):
            if isinstance(event, ContentDelta):
                chunks.append(event.text)
        return "".join(chunks)
