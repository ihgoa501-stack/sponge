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


@dataclass
class TaskResult:
    """Result of executing a task through the agent."""

    task: Task
    response: str
    cost_entry: CostEntry
    fingerprint: CostFingerprint
    cache_hit: bool
