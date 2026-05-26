# Security Model — Approval Gates & Permissions

> Zero-cost plugins (`file_ops`, `shell`) are powerful but dangerous. Sponge's security model ensures that destructive operations always require user consent — without overwhelming the user with unnecessary prompts.

---

## Design Principles

1. **Minimize interruptions, never silently execute destructive operations** — every confirmation dialog breaks flow, but silence on `rm -rf /` is unacceptable.
2. **Least privilege by default** — plugins start locked down; users explicitly grant permissions.
3. **Audit trail** — every approval decision is logged to the event stream.
4. **Session-scoped overrides** — `--auto-approve` is opt-in per session, never persistent.

---

## Three-Tier Approval System

Every tool call passes through an approval chain:

```
Tool call → ApprovalChain.check(tool_name, input)
              │
              ├─ Allow?      → Execute immediately
              ├─ Confirm?    → Show diff/command → User: Y/n/never
              └─ Reject?     → Block + log reason
```

### Tier 1: Allow (auto-execute)

Tools that are read-only or low-risk:

| Tool | Default |
|------|---------|
| `file_read` | ✅ Allow |
| `search_content` | ✅ Allow |
| `list_directory` | ✅ Allow |
| `git log` | ✅ Allow |
| `npm view` | ✅ Allow |

### Tier 2: Confirm (ask before execute)

Tools that modify state:

| Tool | Default | Prompt Shows |
|------|---------|-------------|
| `file_write` | ❓ Confirm | Diff of changes |
| `file_edit` | ❓ Confirm | SEARCH/REPLACE block |
| `shell` (write) | ❓ Confirm | Full command + estimated effect |
| `git commit` | ❓ Confirm | Commit message + diff |
| `npm install` | ❓ Confirm | Package name + version |

### Tier 3: Reject (block unconditionally)

Tools or patterns that are never safe:

| Tool/Pattern | Reason |
|-------------|--------|
| `rm -rf /` | Destructive system operation |
| `sudo` | Privilege escalation |
| Network exfiltration | Data leakage |
| `curl ... | sh` | Remote code execution |

---

## Configuration

### Per-Plugin Defaults

```toml
# ~/.sponge/config.toml

[approval.defaults]
# All plugins inherit these defaults
read = "allow"
write = "confirm"
delete = "confirm"
exec = "confirm"
network = "confirm"

[approval.overrides]
# Plugin-specific overrides
"builtins.file_ops.write_file" = "allow"     # you trust your file ops
"builtins.shell.exec" = "confirm"              # always check shell commands
"mcp:github.create_pr" = "confirm"            # MCP tools also go through approval
"mcp:filesystem.delete_file" = "reject"       # block deletes via MCP filesystem
```

### Interactive Response

When a tool hits a "Confirm" gate, the CLI blocks and prompts:

```
❓ sponge wants to write to src/main.py
   ┌─ Diff ──────────────────────────────────────────┐
   │  - old_function()                                │
   │  + def new_function():                           │
   │  +     return 42                                 │
   └──────────────────────────────────────────────────┘
   Approve? [Y/n] (o)nce / (a)llow always / (n)ever
```

| Response | Meaning |
|----------|---------|
| `Y` / Enter | Approve this one time |
| `n` | Reject this one time |
| `o` | Approve this once |
| `a` | Allow always (adds to config overrides) |
| `N` (capital) | Never allow this tool (adds as `reject` override) |

---

## Session-Level Overrides

Users can escalate or restrict permissions for a single session:

```bash
# Danger zone: auto-approve everything (CI, batch operations)
sponge run "refactor everything" --auto-approve

# Read-only mode: reject all writes
sponge run "find bugs" --read-only

# Custom policy
sponge run "deploy to staging" --approval-policy=deploy-staging
```

**`--auto-approve`** is a session-level escape hatch. It:
- Sets every "confirm" gate to "allow" for the duration of the session
- Logs a prominent warning at session start: `⚠️ Auto-approve enabled`
- Is NOT persistent — next session returns to defaults

**`--read-only`** is the opposite:
- Sets every "confirm" and "allow" write/delete/exec gate to "reject"
- Useful for code review, security audit, or untrusted prompts

---

## Integration with Other Systems

### MCP Server Permissions

MCP tools inherit the same approval system. Server maintainers can declare expected permission tiers in the server manifest:

```json
{
  "tools": [
    {
      "name": "read_file",
      "permissions": {
        "default_tier": "allow"
      }
    },
    {
      "name": "write_file",
      "permissions": {
        "default_tier": "confirm"
      }
    }
  ]
}
```

Users can override these in their Sponge config (see `[approval.overrides]` above).

### Sandbox Integration

Sandbox policies interact with approval gates:

| Sandbox | File Write | Network | Shell Exec |
|---------|-----------|---------|------------|
| **Subprocess** (dev) | Confirm | Confirm | Confirm |
| **Docker** | Allow (container-scoped) | Confirm | Allow (container-scoped) |
| **E2B** | Allow (session-scoped) | Confirm | Allow (session-scoped) |

Docker and E2B sandboxes provide stronger isolation, so some gates are relaxed within the sandbox boundary. But network access is always confirmed.

### Telemetry Integration

Every approval decision is logged:

```sql
-- Event stream entry for approval decisions
{
  "event_type": "approval",
  "data": {
    "tool": "builtins.file_ops.write_file",
    "input_summary": "write to src/main.py (42 lines changed)",
    "verdict": "approved",
    "mode": "interactive",
    "latency_ms": 3400  // time user took to respond
  }
}
```

The self-tuning system can analyze:
- **Approval fatigue**: If user always types "a" (allow always), prompt to update config
- **Threshold calibration**: If user approves everything in a session, suggest `--auto-approve` next time
- **Blocked workflows**: If a gate consistently blocks legitimate use, suggest reclassification

---

## Security Boundaries

```
┌─────────────────────────────────────────────────────────┐
│  User                                                        │
│    │                                                         │
│    ▼ CLI                                                     │
│    │                                                         │
│    ▼ ApprovalChain ← config.toml + session overrides      │
│    │                                                         │
│    ├──► Native Plugin (builtins) ──── Sandbox ──── OS     │
│    │       file_ops, shell                     │            │
│    │                                          │            │
│    └──► MCPServerPlugin ──── Sandbox ──── Subprocess     │
│            MCP stdio/SSE                       │            │
│                                                 │            │
│    ▼ Event Stream (audit log)                              │
└─────────────────────────────────────────────────────────┘
```

| Layer | Security Boundary | Bypassed By |
|-------|------------------|-------------|
| **Approval Chain** | User consent | `--auto-approve` |
| **Plugin Isolation** | Plugin can't read other plugin's memory | Implementation |
| **Sandbox** | OS-level isolation (container, VM) | `--sandbox=subprocess` (dev only) |
| **Rate Limit** | Prevent runaway tool calls | Overridable via config |

---

## Anti-Patterns

| Anti-Pattern | Why Sponge Avoids It |
|-------------|---------------------|
| **Auto-approve as default** | Silent `rm -rf /` is one hallucinated prompt away |
| **Always confirm everything** | Every dialog breaks flow; user learns to mash "y" |
| **Stored passwords in config** | `${VAR}` interpolation keeps secrets in environment |
| **MCP auto-discovery** | Dynamic server registration = remote code execution vector |
| **Per-tool auth in plugin code** | Centralized approval chain means one audit point |
