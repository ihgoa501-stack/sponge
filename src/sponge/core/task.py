"""Task and TaskResult models for the agent loop."""

from dataclasses import dataclass

from sponge.cost.models import CostEntry
from sponge.telemetry.models import CostFingerprint


@dataclass
class Task:
    """A task to be executed by the agent."""

    prompt: str
    model: str | None = None
    system_prompt: str = ""
    images: list[str] | None = None
    failed: bool = False
    """Set by caller to indicate this is a retry after a known failure."""
    failure_reason: str = ""
    """Human-readable reason for the failure, used as input to reflection."""


@dataclass
class TaskResult:
    """Result of executing a task through the agent."""

    task: Task
    response: str
    cost_entry: CostEntry
    fingerprint: CostFingerprint
    cache_hit: bool
    cache_source: str = ""  # "exact", "semantic", or ""
    failed: bool = False
    """Whether the task failed (user correction, tool error, quality flag)."""
    failure_reason: str = ""
    """Human-readable reason for failure, used as input to reflection."""
    lesson_stored: str = ""
    """ID of the lesson stored from this failure, if any."""
