"""Plugin base types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class ApprovalLevel(Enum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    REJECT = "reject"


@dataclass
class PluginContext:
    """Context passed to plugins during execution."""

    task: str
    working_dir: str = "."


@dataclass
class PluginResult:
    """Result from a plugin execution."""

    output: str
    success: bool = True
    zero_cost: bool = True  # No LLM call needed


@dataclass
class PluginMatch:
    """Match result from routing a task to a plugin."""

    plugin: Plugin
    confidence: float  # 0.0–1.0
    args: dict[str, str] = field(default_factory=dict)


class Plugin(ABC):
    """Base class for plugins that handle tasks without LLM calls."""

    name: str = ""
    description: str = ""
    approval: ApprovalLevel = ApprovalLevel.CONFIRM
    priority: int = 0  # Lower = checked first

    @abstractmethod
    def can_handle(self, task: str) -> PluginMatch | None:
        """Return a match if this plugin can handle the task."""

    @abstractmethod
    async def execute(self, context: PluginContext) -> PluginResult:
        """Execute the plugin and return the result."""
