"""MCPPlugin — wraps an MCP server as a Sponge Plugin.

Discovers tools from the MCP server and routes tasks that mention
tool names. Each tool call costs $0 in LLM fees.
"""

from __future__ import annotations

import logging

from sponge.plugins.base import (
    ApprovalLevel,
    Plugin,
    PluginContext,
    PluginMatch,
    PluginResult,
)
from sponge.plugins.mcp_client import MCPClient

logger = logging.getLogger("sponge.plugins.mcp")


class MCPPlugin(Plugin):
    """Wraps an MCP server so its tools become $0 Sponge plugin calls.

    Usage:
        client = MCPClient(["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"])
        client.start()
        plugin = MCPPlugin(client)
        await plugin.discover()  # call once after start
    """

    name = "mcp"
    description = "MCP server tools — $0 LLM cost."
    approval = ApprovalLevel.CONFIRM

    def __init__(self, client: MCPClient, priority: int = 50) -> None:
        self._client = client
        self.name = f"mcp:{client.server_name}"
        self.description = f"MCP server '{client.server_name}' tools"
        self.priority = priority

    async def discover(self) -> None:
        """Discover tools from the MCP server. Call after start()."""
        await self._client.discover_tools()

    def can_handle(self, task: str) -> PluginMatch | None:
        """Match if the task mentions an MCP tool name."""
        task_lower = task.lower()
        for tool in self._client.tools:
            if tool.name.lower() in task_lower:
                return PluginMatch(
                    plugin=self,
                    confidence=0.8,
                    args={"tool": tool.name},
                )
        return None

    async def execute(self, context: PluginContext) -> PluginResult:
        """Execute the matched MCP tool."""
        # Find which tool was matched.
        task_lower = context.task.lower()
        tool_name = ""
        for tool in self._client.tools:
            if tool.name.lower() in task_lower:
                tool_name = tool.name
                break

        if not tool_name:
            return PluginResult(output="Could not determine which tool to call.", success=False)

        try:
            output = await self._client.call_tool(tool_name)
            return PluginResult(output=output)
        except Exception as e:
            return PluginResult(output=f"MCP tool error: {e}", success=False)
