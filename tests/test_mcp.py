"""Tests for MCP plugin and client."""

import json
import subprocess
from unittest import mock

import pytest

from sponge.plugins.base import PluginContext
from sponge.plugins.mcp_client import MCPClient, MCPTool
from sponge.plugins.mcp_plugin import MCPPlugin


# ---------------------------------------------------------------------------
# MCPClient tests (with mocked subprocess)
# ---------------------------------------------------------------------------


class _FakePopen:
    """A fake subprocess.Popen that speaks enough JSON-RPC for testing."""

    def __init__(self, *args, **kwargs) -> None:  # noqa: ARG002
        # Pre-load canned responses (one per request).
        self._responses: list[dict] = []
        self.stdin = _FakeStdin()
        self.stdout = _FakeStdout(self._responses)
        self.stderr = _FakeStderr()
        self.pid = 12345
        # Track whether terminate/kill was called.
        self.terminated = False
        self.killed = False

    def set_responses(self, responses: list[dict]) -> None:
        self.stdout.set_responses(responses)

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def wait(self, timeout: float | None = None) -> None:  # noqa: ARG002
        pass

    def poll(self) -> None:
        return None


class _FakeStdin:
    def __init__(self) -> None:
        self.writes: list[str] = []

    def write(self, data: str) -> None:
        self.writes.append(data)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass


class _FakeStdout:
    def __init__(self, responses: list[dict]) -> None:
        self._responses = responses
        self._idx = 0

    def set_responses(self, responses: list[dict]) -> None:
        self._responses = responses
        self._idx = 0

    def readline(self) -> str:
        if self._idx >= len(self._responses):
            return ""
        resp = self._responses[self._idx]
        self._idx += 1
        return json.dumps(resp) + "\n"

    def close(self) -> None:
        pass


class _FakeStderr:
    def read(self) -> str:
        return ""

    def close(self) -> None:
        pass


def _build_tools_list_response() -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {
                    "name": "read_file",
                    "description": "Read a file from the filesystem",
                    "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}},
                },
                {
                    "name": "list_directory",
                    "description": "List directory contents",
                    "inputSchema": {"type": "object"},
                },
            ]
        },
    }


def _build_tool_call_response(text: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {
            "content": [
                {"type": "text", "text": text},
            ],
        },
    }


def _build_error_response() -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"code": -32601, "message": "Method not found"},
    }


@pytest.mark.asyncio
async def test_discover_tools_parses_response() -> None:
    """discover_tools() parses tool definitions from a tools/list response."""
    client = MCPClient(["fake-server"])
    client._process = _FakePopen()
    client._process.set_responses([_build_tools_list_response()])

    tools = await client.discover_tools()

    assert len(tools) == 2
    assert tools[0].name == "read_file"
    assert tools[0].description == "Read a file from the filesystem"
    assert tools[1].name == "list_directory"


@pytest.mark.asyncio
async def test_call_tool_returns_text() -> None:
    """call_tool() returns concatenated text from content blocks."""
    client = MCPClient(["fake-server"])
    client._process = _FakePopen()
    # First call is tools/list, second is tools/call.
    client._process.set_responses([
        _build_tools_list_response(),
        _build_tool_call_response("Hello from MCP"),
    ])
    await client.discover_tools()

    result = await client.call_tool("read_file", {"path": "/tmp/test.txt"})
    assert result == "Hello from MCP"


def test_start_spawns_process() -> None:
    """start() spawns a subprocess via Popen."""
    client = MCPClient(["echo", "hello"], server_name="echo")
    with mock.patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = _FakePopen()
        client.start()
        mock_popen.assert_called_once()


def test_stop_terminates_and_waits() -> None:
    """stop() calls terminate() then wait()."""
    client = MCPClient(["fake-server"])
    fake = _FakePopen()
    client._process = fake
    client.stop()
    assert fake.terminated is True


def test_server_name_defaults_to_command() -> None:
    """When server_name is empty, it defaults to command[0]."""
    client = MCPClient(["my-mcp-server", "--port", "8080"])
    assert client.server_name == "my-mcp-server"


def test_tools_returns_copy() -> None:
    """tools property returns a copy, not the internal list."""
    client = MCPClient(["fake-server"])
    client._tools = [MCPTool(name="t1"), MCPTool(name="t2")]
    tools = client.tools
    assert len(tools) == 2
    tools.pop()
    assert len(client.tools) == 2  # internal list unchanged


# ---------------------------------------------------------------------------
# MCPPlugin tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_can_handle_matches_tool_name() -> None:
    """can_handle() returns a match when the task mentions a known tool."""
    client = MCPClient(["fake-server"])
    client._tools = [
        MCPTool(name="read_file", description="Read a file"),
        MCPTool(name="list_directory", description="List dir"),
    ]
    plugin = MCPPlugin(client)

    match = plugin.can_handle("please read_file the config")
    assert match is not None
    assert match.confidence == 0.8
    assert match.args["tool"] == "read_file"


def test_can_handle_no_match() -> None:
    """can_handle() returns None when no tool is mentioned."""
    client = MCPClient(["fake-server"])
    client._tools = [MCPTool(name="read_file", description="Read a file")]
    plugin = MCPPlugin(client)

    match = plugin.can_handle("what is the capital of France?")
    assert match is None


def test_can_handle_case_insensitive() -> None:
    """can_handle() is case-insensitive."""
    client = MCPClient(["fake-server"])
    client._tools = [MCPTool(name="Read_File", description="Read a file")]
    plugin = MCPPlugin(client)

    match = plugin.can_handle("please read_file the config")
    assert match is not None


@pytest.mark.asyncio
async def test_execute_calls_matched_tool() -> None:
    """execute() finds the matched tool and calls it via the client."""
    client = MCPClient(["fake-server"])
    client._tools = [MCPTool(name="read_file", description="Read a file")]
    client._process = _FakePopen()
    client._process.set_responses([_build_tool_call_response("file contents")])
    plugin = MCPPlugin(client)

    context = PluginContext(task="please read_file /tmp/config.toml")
    result = await plugin.execute(context)

    assert result.success is True
    assert result.output == "file contents"


@pytest.mark.asyncio
async def test_execute_no_tool_match_returns_error() -> None:
    """execute() returns an error result when no tool matches the task."""
    client = MCPClient(["fake-server"])
    client._tools = []  # No tools discovered
    plugin = MCPPlugin(client)

    context = PluginContext(task="do something unrelated")
    result = await plugin.execute(context)

    assert result.success is False
    assert "Could not determine" in result.output


@pytest.mark.asyncio
async def test_execute_handles_client_error() -> None:
    """execute() catches errors from the MCP client and returns them."""
    client = MCPClient(["fake-server"])
    client._tools = [MCPTool(name="failing_tool", description="Always fails")]
    client._process = _FakePopen()
    client._process.set_responses([_build_error_response()])
    plugin = MCPPlugin(client)

    context = PluginContext(task="run failing_tool now")
    result = await plugin.execute(context)

    assert result.success is False
    assert "MCP tool error" in result.output


def test_plugin_name_includes_server_name() -> None:
    """MCPPlugin.name includes the server name for identification."""
    client = MCPClient(["my-server"], server_name="my-server")
    plugin = MCPPlugin(client)
    assert plugin.name == "mcp:my-server"
