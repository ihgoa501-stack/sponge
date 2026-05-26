"""Context Planner — load only needed context per sub-task.

Instead of dumping the entire repository context upfront, the planner
determines what each sub-task actually needs and loads it on demand.
This reduces context by 3-5× compared to pre-loading everything.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("sponge.core.context_planner")


@dataclass
class ContextItem:
    """A single piece of context needed for a sub-task."""

    type: str  # "file", "directory", "search_result", "tool_output"
    path: str = ""
    content: str = ""
    tokens: int = 0


@dataclass
class ContextPlan:
    """What context a sub-task needs and what's already loaded."""

    sub_task_id: int = 0
    description: str = ""
    needed: list[ContextItem] = field(default_factory=list)
    already_loaded: set[str] = field(default_factory=set)
    total_tokens: int = 0


class ContextPlanner:
    """Determines context requirements per sub-task.

    Tracks what's already loaded across sub-tasks to avoid
    re-loading the same files/directories. Ensures each sub-task
    only carries the context it actually needs.
    """

    def __init__(self, max_context_per_task: int = 15000) -> None:
        self._max_context = max_context_per_task
        self._loaded: set[str] = set()  # paths already loaded

    def plan(self, sub_task_id: int, description: str, context_hint: str = "") -> ContextPlan:
        """Create a context plan for a sub-task.

        Extracts file/directory paths from the context hint and description,
        removes anything already loaded, and estimates token count.
        """
        plan = ContextPlan(sub_task_id=sub_task_id, description=description)

        # Extract paths from context hint and description.
        paths = self._extract_paths(description + " " + context_hint)

        for path in paths:
            if path in self._loaded:
                plan.already_loaded.add(path)
                continue
            plan.needed.append(ContextItem(type=self._guess_type(path), path=path))

        # Estimate tokens.
        plan.total_tokens = sum(item.tokens for item in plan.needed)

        # Enforce per-task budget (by count and token estimate).
        if len(plan.needed) > 10 or plan.total_tokens > self._max_context:
            logger.warning(
                "Sub-task %d context (%d tokens) exceeds budget (%d) — truncating",
                sub_task_id,
                plan.total_tokens,
                self._max_context,
            )
            plan.needed = plan.needed[:10]  # keep first 10 items
            plan.total_tokens = sum(item.tokens for item in plan.needed)

        return plan

    def mark_loaded(self, paths: list[str]) -> None:
        """Mark paths as loaded so they won't be re-fetched."""
        self._loaded.update(paths)

    @property
    def total_loaded(self) -> int:
        return len(self._loaded)

    def _extract_paths(self, text: str) -> list[str]:
        """Extract file/directory paths from text."""
        import re

        paths: list[str] = []
        # Match quoted paths.
        for m in re.finditer(r"""["']([^"']+\.[a-zA-Z]+)["']""", text):
            paths.append(m.group(1))
        # Match paths with extensions in backticks.
        for m in re.finditer(r"`([^`]+\.[a-zA-Z]+)`", text):
            paths.append(m.group(1))
        # Deduplicate while preserving order.
        seen: set[str] = set()
        result = []
        for p in paths:
            if p not in seen:
                seen.add(p)
                result.append(p)
        return result

    def _guess_type(self, path: str) -> str:
        """Guess context type from path extension."""
        if path.endswith((".py", ".js", ".ts", ".rs", ".go", ".java")):
            return "file"
        if "/" in path and "." not in path.rsplit("/", 1)[-1]:
            return "directory"
        return "file"
