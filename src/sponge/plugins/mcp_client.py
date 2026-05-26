"""MCP (Model Context Protocol) client.

Spawns an MCP server process and communicates via JSON-RPC over
stdin/stdout. Discovers tools and proxies tool calls.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from dataclasses import dataclass, field

logger = logging.getLogger("sponge.mcp")


@dataclass
class MCPTool:
    """An MCP tool discovered from a server."""

    name: str
    description: str = ""
    input_schema: dict = field(default_factory=dict)


@dataclass
class MCPServerInfo:
    """Info about a connected MCP server."""

    name: str
    tools: list[MCPTool] = field(default_factory=list)


class MCPClient:
    """Manages an MCP server subprocess and proxies tool calls via JSON-RPC."""

    def __init__(self, command: list[str], server_name: str = "") -> None:
        self._command = command
        self._server_name = server_name or command[0]
        self._process: subprocess.Popen | None = None
        self._request_id = 0
        self._tools: list[MCPTool] = []

    @property
    def tools(self) -> list[MCPTool]:
        return list(self._tools)

    @property
    def server_name(self) -> str:
        return self._server_name

    def start(self) -> None:
        """Spawn the MCP server subprocess."""
        if self._process is not None:
            return

        self._process = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logger.info("MCP server '%s' started (pid=%d)", self._server_name, self._process.pid)

    def stop(self) -> None:
        """Terminate the MCP server subprocess."""
        if self._process is None:
            return
        try:
            self._process.terminate()
            self._process.wait(timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            self._process.kill()
        self._process = None
        logger.info("MCP server '%s' stopped", self._server_name)

    def _send_request(self, method: str, params: dict | None = None) -> dict:
        """Send a JSON-RPC request and return the response."""
        if self._process is None or self._process.stdin is None or self._process.stdout is None:
            raise RuntimeError("MCP server not started")

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }

        payload = json.dumps(request) + "\n"
        self._process.stdin.write(payload)
        self._process.stdin.flush()

        response_line = self._process.stdout.readline()
        if not response_line:
            raise RuntimeError(f"MCP server '{self._server_name}' closed stdout")

        response = json.loads(response_line)
        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")
        return response.get("result", {})

    async def discover_tools(self) -> list[MCPTool]:
        """Call tools/list and populate tool definitions."""
        result = await asyncio.to_thread(self._send_request, "tools/list")
        raw_tools = result.get("tools", [])
        self._tools = [
            MCPTool(
                name=t.get("name", ""),
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", {}),
            )
            for t in raw_tools
        ]
        logger.info(
            "MCP '%s': discovered %d tools", self._server_name, len(self._tools)
        )
        return self.tools

    async def call_tool(self, tool_name: str, arguments: dict | None = None) -> str:
        """Call a tool on the MCP server and return its text output."""
        result = await asyncio.to_thread(
            self._send_request,
            "tools/call",
            {"name": tool_name, "arguments": arguments or {}},
        )
        # Extract text from content blocks.
        contents = result.get("content", [])
        texts = [c.get("text", "") for c in contents if c.get("type") == "text"]
        return "\n".join(texts)
