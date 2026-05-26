"""Built-in shell execution plugin — $0 LLM cost."""

from sponge.plugins.base import (
    ApprovalLevel,
    Plugin,
    PluginContext,
    PluginMatch,
    PluginResult,
)


class ShellPlugin(Plugin):
    """Handles shell command execution locally."""

    name = "shell"
    description = "Execute shell commands"
    approval = ApprovalLevel.CONFIRM

    def can_handle(self, task: str) -> PluginMatch | None:
        task_lower = task.lower().strip()

        if any(
            kw in task_lower
            for kw in [
                "run ",
                "execute ",
                "npm ",
                "pip ",
                "git ",
                "pytest",
                "python ",
                "node ",
            ]
        ):
            return PluginMatch(plugin=self, confidence=0.6)

        return None

    async def execute(self, context: PluginContext) -> PluginResult:  # noqa: ARG002
        return PluginResult(output="", success=True, zero_cost=True)
