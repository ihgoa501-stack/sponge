> ⚠️ **Draft** — MCP integration is a Phase 3+ commodity feature. This document will be updated when prioritized. See [project-plan.md](project-plan.md).

# MCP Integration — Ecosystem Compatibility

> Sponge's plugin system is **MCP-native**. The `Plugin ABC` wraps MCP servers as first-class citizens, giving users access to the entire MCP ecosystem without writing adapter code.

---

## Why MCP?

MCP (Model Context Protocol) has become the industry standard for AI tool integration:

| Tool | MCP Support |
|------|-----------|
| Claude Code | ✅ Native |
| Cursor | ✅ Native |
| GitHub Copilot | ✅ Native |
| Continue.dev | ✅ Native |
| **Sponge** | **✅ MCP-native** |

Building a custom plugin protocol would force every third-party tool author to write two integrations. By adopting MCP, Sponge inherits a growing ecosystem of servers:

- `filesystem` — file read/write/search
- `github` — PRs, issues, repos
- `puppeteer` — browser automation
- `memory` — knowledge graph persistence
- `postgres` — database queries
- `slack` — messaging
- And hundreds of community servers

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  PluginRegistry                                                    │
│                                                                   │
│  best_match(task) ───┬── Native Plugin (built-in)                 │
│                      │     file_ops, shell                        │
│                      │     ╰→ direct import, zero overhead        │
│                      │                                            │
│                      └── MCPServerPlugin (adapter)                │
│                            wraps any stdio/SSE MCP server         │
│                            ╰→ spawn → handshake → cache tools     │
│                                   → proxy tool calls              │
└──────────────────────────────────────────────────────────────────┘
```

### MCPServerPlugin — The Adapter

```
┌─ MCPServerPlugin ─────────────────────────────────────┐
│                                                        │
│  Config:                                               │
│    command: "npx"                                      │
│    args: ["-y", "@modelcontextprotocol/server-fs",     │
│           "/allowed/path"]                             │
│    transport: "stdio"    # or "sse" / "streamable-http"│
│    url: "..."            # for SSE transport            │
│    env: {"KEY": "val"}   # additional env vars         │
│                                                        │
│  Lifecycle:                                            │
│    spawn()      → start subprocess / connect SSE        │
│    handshake()  → initialize → list tools               │
│    cache_tools() → cache tool schemas (refresh: 5min)   │
│    call_tool()  → tools/tool_name → return result       │
│    shutdown()   → graceful stop                         │
│                                                        │
│  Tool schema caching:                                   │
│    tools_cached = {                                     │
│      "read_file": {"description": "...",                │
│                    "inputSchema": {...}},                │
│      "write_file": {"description": "...",               │
│                     "inputSchema": {...}},               │
│    }                                                    │
│                                                        │
│  Error handling:                                        │
│    Timeout → retry (configurable, default 3s)           │
│    Server crash → auto-restart (max 3 attempts)         │
│    Non-JSON response → parse error                     │
│    Permission denied → log + return error               │
├────────────────────────────────────────────────────────┤
│  Approval integration:                                  │
│    Each tool inherits its approval tier from config:    │
│      "filesystem.read_file"      → Allow               │
│      "filesystem.write_file"     → Confirm              │
│      "github.create_pull_request" → Confirm             │
└────────────────────────────────────────────────────────┘
```

---

## MCP Server Configuration

MCP servers are declared in `~/.sponge/config.toml`:

```toml
[mcp.servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
transport = "stdio"

[mcp.servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
transport = "stdio"
env = { GITHUB_TOKEN = "${GITHUB_TOKEN}" }

[mcp.servers.puppeteer]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-puppeteer"]
transport = "stdio"

[mcp.servers.postgres]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-postgres", "postgresql://..."]
transport = "stdio"

# Per-server approval overrides
[mcp.servers.filesystem.approval]
write_file = "confirm"
delete_file = "reject"
```

Environment variables (`${VAR}`) are interpolated from the shell environment at startup. This keeps secrets out of config files.

---

## Lifecycle Management

```
sponge run "task"
  │
  ├─ PluginRegistry.init()
  │   ├─ Load native builtins (file_ops, shell, search, review)
  │   ├─ Parse mcp.servers from config.toml
  │   └─ For each MCP server:
  │       ├─ spawn() — start subprocess / open SSE connection
  │       ├─ handshake() — initialize + list tools
  │       ├─ cache_tools() — store tool schemas
  │       └─ register tools in PluginRegistry with "mcp:" prefix
  │
  ├─ Task execution (tools called via registry)
  │
  └─ PluginRegistry.shutdown()
      └─ For each MCP server:
          ├─ Send shutdown notification
          ├─ Close stdin / SSE connection
          └─ Wait for graceful exit (timeout: 5s) → SIGKILL
```

**Startup cost:** MCP server startup is cold. First call to a tool may take 1-3 seconds. Subsequent calls use the already-running server (~1-5ms per call).

**Caching:** Tool schemas are cached in memory and refreshed every 5 minutes. Server processes stay alive for the duration of the Sponge session, then are terminated on shutdown.

---

## Routing Priority

When `PluginRegistry.best_match(task)` is called:

1. **Native builtins first** — zero overhead, no MCP hop
2. **MCP tools second** — by description similarity + input schema match
3. **No match → LLM call** — fall through to best model

This ensures that common operations (file read, shell) are always fastest, while MCP tools are available for everything else.

---

## Security Considerations

| Concern | Mitigation |
|---------|-----------|
| **Arbitrary command execution** | MCP server command is in config, not from user prompt. User must explicitly add a server. |
| **Network access** | MCP servers inherit Sponge's network sandbox. Sensitive servers (database, GitHub) are flagged at registration. |
| **Resource exhaustion** | Per-server timeout (default 30s) and max output size (1MB). Long-running servers are flagged. |
| **Server crash** | Auto-restart with exponential backoff. After 3 failures, server is disabled for the session. |
| **Privilege escalation** | MCP tools go through the same approval gate as native plugins. User can set `confirm` or `reject` per tool. |
| **SSE servers (remote)** | Remote MCP servers are explicitly opt-in. User must approve the URL. No auto-discovery. |

---

## Future: Dynamic MCP Server Registration

Phase 8+ feature: allow the LLM itself to suggest and configure MCP servers:

```
User: "Can you check my PR for issues?"
Agent: "I don't have GitHub access. Add a GitHub MCP server?"
       "Run this command to add it: sponge config add-mcp github"
```

This is intentionally **not automatic** — server registration requires explicit user action as a security boundary.
