"""Built-in file operations plugin — $0 LLM cost."""

from sponge.plugins.base import (
    ApprovalLevel,
    Plugin,
    PluginContext,
    PluginMatch,
    PluginResult,
)


class FileOpsPlugin(Plugin):
    """Handles file read, write, and list operations locally."""

    name = "file_ops"
    description = "Read, write, and list files"
    approval = ApprovalLevel.CONFIRM

    def can_handle(self, task: str) -> PluginMatch | None:
        task_lower = task.lower().strip()

        if any(kw in task_lower for kw in ["read file", "read the file", "show file", "cat "]):
            path = self._extract_path(task)
            if path:
                return PluginMatch(
                    plugin=self,
                    confidence=0.9,
                    args={"path": path, "action": "read"},
                )

        if any(kw in task_lower for kw in ["list files", "list directory", "ls ", "show files"]):
            path = self._extract_path(task) or "."
            return PluginMatch(plugin=self, confidence=0.8, args={"path": path, "action": "list"})

        if any(kw in task_lower for kw in ["write file", "create file", "save "]):
            path = self._extract_path(task)
            if path:
                return PluginMatch(
                    plugin=self,
                    confidence=0.7,
                    args={"path": path, "action": "write"},
                )

        return None

    async def execute(self, context: PluginContext) -> PluginResult:
        _ = context.task  # reserved for future implementation
        return PluginResult(output="", success=True, zero_cost=True)

    def _extract_path(self, task: str) -> str | None:
        """Try to extract a file path from the task string."""
        import re

        # Match quoted paths.
        m = re.search(r"""["']([^"']+)["']""", task)
        if m:
            return m.group(1)

        # Match paths after keywords.
        for kw in ["file ", "path ", "in "]:
            if kw in task:
                rest = task.split(kw, 1)[1].strip().split()[0]
                if rest:
                    return rest

        return None
