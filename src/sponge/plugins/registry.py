"""Plugin registry — discovers and routes tasks to plugins."""

from sponge.plugins.base import Plugin, PluginContext, PluginMatch, PluginResult


class PluginRegistry:
    """Registry of all available plugins."""

    def __init__(self, plugins: list[Plugin] | None = None) -> None:
        self._plugins: list[Plugin] = sorted(
            plugins or [], key=lambda p: p.priority
        )

    def register(self, plugin: Plugin) -> None:
        self._plugins.append(plugin)
        self._plugins.sort(key=lambda p: p.priority)

    def best_match(self, task: str) -> PluginMatch | None:
        """Find the best plugin for a task. Returns None if no match."""
        best: PluginMatch | None = None
        for plugin in self._plugins:
            match = plugin.can_handle(task)
            if match and (best is None or match.confidence > best.confidence):
                best = match
        return best

    async def execute(self, match: PluginMatch, context: PluginContext) -> PluginResult:
        """Execute a matched plugin."""
        return await match.plugin.execute(context)
