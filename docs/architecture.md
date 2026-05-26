# Sponge Architecture

> **Use the best model, pay the least.** Every layer exists to minimize the token footprint of calls to the top-tier model — never by downgrading the model, always by compressing what gets sent to it.

---

## Design Philosophy

Sponge is a **harness**, not a framework or runtime. Borrowing the LangChain team's three-layer model:

| Layer | What it provides | Sponge's role |
|-------|-----------------|---------------|
| **Framework** | Abstractions + integrations | Sponge uses none — direct SDK calls |
| **Runtime** | Durable execution, streaming | External (LangGraph if needed) |
| **Harness** | Predefined tools, prompts, subagents, planning, context management | **This is Sponge** |

A harness is an opinionated, batteries-included layer. Sponge's opinion: **cost compression is the infrastructure**.

---

## Core Loop

The agent loop is intentionally tiny (~30 lines). 95% of complexity lives in the infrastructure that feeds it:

```python
while not done:
    messages = context_pipeline.compress(messages)   # prune + mask before call
    cost = cost_estimator.estimate(messages)         # pre-call cost prediction
    circuit_breaker.check(cost)                      # enforce budget, never downgrade

    async for event in llm.stream(messages):          # streaming by default
        match event:
            case ContentDelta(text=text):
                render(text)                         # incremental display
            case ToolCall(name=name, input=input):
                if approval_gate.ok(name, input):     # approval check
                    result = await execute_tool(name, input)
                    messages.append(result)
            case Usage(tokens_in=in_, tokens_out=out):
                cost_tracker.record(in_, out)         # incremental cost tracking
```

---

## Module Map

```
src/sponge/
├── __init__.py / __main__.py      # Package entry points
│
├── cli/                           # Typer CLI
│   ├── app.py                     # Top-level app + command registration
│   ├── run.py                     # sponge run <task>
│   ├── session.py                 # sponge session [start|resume|list]
│   ├── config_cmd.py              # sponge config [show|init|set]
│   └── cost_cmd.py                # sponge cost [--task|--session|--export]
│
├── core/                          # Agent orchestrator
│   ├── agent.py                   # ~30 line while loop
│   ├── task.py                    # Task / TaskResult models
│   ├── session.py                 # Session lifecycle, persistence
│   ├── context.py                 # 5-layer context pipeline
│   └── event_stream.py            # Append-only event log
│
├── llm/                           # Provider-agnostic LLM layer
│   ├── base.py                    # LLMProvider ABC
│   ├── anthropic_provider.py      # Claude integration
│   ├── openai_provider.py         # OpenAI integration
│   ├── factory.py                 # Provider selection
│   ├── cost_estimator.py          # Pre-call cost prediction
│   └── token_counter.py           # Token counting helpers
│
├── cost/                          # Cost accounting
│   ├── models.py                  # CostEntry, CostSummary, ModelPricing
│   ├── tracker.py                 # Per-call/task/session tracking
│   ├── reporter.py                # Formatted reports + exports
│   └── budget.py                  # Circuit breaker + budget ceilings
│
├── cache/                         # Multi-level caching
│   ├── base.py                    # Cache ABC
│   ├── result_cache.py            # Exact-match result cache (SQLite)
│   ├── prompt_cache.py            # Prompt cache retention management
│   ├── semantic_cache.py          # Embedding-similarity cache
│   └── disk_store.py              # SQLite key-value store
│
├── plugins/                       # Plugin system
│   ├── base.py                    # Plugin ABC, PluginContext, PluginResult
│   ├── registry.py                # Plugin discovery & routing
│   ├── mcp_server.py              # MCP server lifecycle & tool proxy
│   ├── sub_agent.py               # Sub-agent dispatch + condensation
│   ├── preprocessor.py            # Local preprocessing pipeline
│   └── builtins/                  # Bundled plugins
│       ├── file_ops.py            # File operations ($0)
│       ├── shell.py               # Shell execution ($0)
│       ├── search.py              # Code search (sub-agent)
│       └── review.py              # Code review (sub-agent)
│
├── sandbox/                       # Isolated execution
│   ├── base.py                    # Sandbox ABC
│   ├── docker_sandbox.py          # Docker container
│   ├── e2b_sandbox.py             # E2B sandbox-as-a-service
│   └── subprocess_sandbox.py      # Local subprocess (dev only)
│
├── config/                        # Configuration
│   ├── settings.py                # Pydantic Settings model
│   └── loader.py                  # TOML + env var loading
│
├── telemetry/                     # Self-tuning
│   ├── collector.py               # Per-call metrics → SQLite
│   ├── models.py                  # TelemetryEntry, UsagePattern
│   ├── analyzer.py                # SQL pattern queries
│   ├── tuner.py                   # Auto-apply winning configs
│   └── feedback.py                # Shadow A/B testing
│
├── memory/                        # Long-term memory
│   ├── base.py                    # MemoryStore ABC
│   ├── project_memory.py          # Project-level (.sponge/memory.toml)
│   ├── user_preferences.py        # User-level (~/.sponge/prefs.toml)
│   └── injector.py                # Memory → system prompt injection
│
├── approval/                      # Approval gates
│   ├── base.py                    # ApprovalPolicy ABC
│   ├── chain.py                   # Approval chain (allow → confirm → reject)
│   ├── policies.py                # Built-in policies
│   └── session_overrides.py       # Per-session overrides
│
└── utils/                         # Shared
    ├── logging.py                 # Structured logging
    ├── errors.py                  # Exception hierarchy
    └── retry.py                   # Async retry with backoff
```

---

## Data Flow

```
sponge run "task"
  │
  ▼
[Event Stream] TaskStarted
  │
  ▼
[Cache Check] SHA256(task + system + tools)
  ├─ Exact HIT → return cached (cost: $0)
  ├─ Semantic HIT (cosine ≥ 0.95) → return cached (cost: ~$0.0001)
  └─ MISS
       │
       ▼
  [Plugin Route] PluginRegistry.best_match()
   ├─ Plugin match → [Approval Gate] check policy
   │   ├─ ✅ Allow → Plugin.execute()
   │   │   ├─ Native plugin → Cost: $0, no LLM call
   │   │   └─ Sub-agent → isolated exec → condensed result
   │   ├─ ❓ Confirm → prompt user → execute / cancel
   │   └─ 🚫 Reject → log + skip
   │
   └─ No plugin → Requires LLM
       │
       ▼
  [Preprocessor] (optional) Local model compresses prompt
  [Cost Estimator] tiktoken → exact $ estimate
  [Circuit Breaker] per-call + cumulative + step budget
  [Context Compressor] 5-layer pipeline
  [LLM.chat()] → Best model
       │
       ▼
  [CostTracker.record()] → [Cache.write()] → [EventStream: TaskCompleted]
       │
       ▼
  Return TaskResult + CostSummary + SavingsReport
```

---

## Key Design Decisions

### Why Not Route to Cheaper Models?

Routing trades quality for cost. Sponge's premise: **you should never have to choose**. Instead of paying less for worse answers, Sponge pays less for the same answer through infrastructure savings (caching, compression, local preprocessing, plugin routing).

### Why a Harness, Not a Framework?

Frameworks (LangChain, Vercel AI SDK) provide abstractions you compose. Harnesses (Claude Code, Deep Agents SDK) provide an opinionated end-to-end experience. Sponge is a harness because the cost optimization is cross-cutting — it can't be a composable layer; it must own the entire pipeline.

### Why Python?

- Universal glue language for the AI ecosystem
- Rich async support for concurrent operations
- Direct access to tokenizers (tiktoken), SQLite, and subprocess management
- Lowest barrier to contribution for the open-source AI community

### Why SQLite for Telemetry?

- Zero infrastructure — no server, no daemon, no cloud dependency
- ACID guarantees for crash-safe telemetry logging
- SQL queries for pattern analysis = no ML framework needed
- Append-only design means no write contention in hot paths

### Why MCP Compatibility, Not a Custom Protocol?

[MCP (Model Context Protocol)](https://modelcontextprotocol.io) has become the industry standard for tool integration — Claude Code, Cursor, GitHub Copilot all support it. Building a custom plugin protocol would force every tool author to write two integrations.

Sponge's plugin system is **MCP-native**: the `Plugin ABC` wraps MCP servers as first-class citizens. A `MCPServerPlugin` adapter handles lifecycle (spawn → handshake → list tools → call tool → shutdown), tool discovery caching, and error translation. Built-in plugins (`file_ops`, `shell`) are still implemented natively for zero-overhead, but any third-party tool goes through MCP.

**Trade-off:** MCP adds a stdio/SSE hop per tool call (~1-5ms latency). For latency-sensitive operations (shell, file read) the native path bypasses MCP. The registry prefers native plugins when available, falls back to MCP.

### Why Streaming Responses?

Users expect interactive feel — characters appearing as the model generates them, not a 30-second freeze followed by a wall of text. A blocking `llm.chat()` architecture hides latency and feels broken.

The streaming architecture is a **two-level pipeline**:

```
Level 1 (hot path, required):
  LLM stream → SSE → CLI/TUI render
  Cost tracker accrues output tokens incrementally
  Stream-aware compression: don't compress, but do estimate remaining budget

Level 2 (cool path, optional):
  Long-running sub-agent → its own SSE stream → parent agent consolidates
  Multiple sub-agent streams are merged into a single user-facing stream
```

**Impact on cost model:** With streaming, output token count is unknown until the stream ends. The cost estimator can only predict input cost pre-call; output cost accrues incrementally. The circuit breaker switches from "check before call" to "check during stream" — if output runs away mid-stream, it can terminate early.

### Why Approval Gates?

Zero-cost plugins (`file_ops`, `shell`) are powerful but dangerous. Without user confirmation, a misaligned prompt could delete files, install packages, or exfiltrate data before the user can react.

The approval system has three tiers:

| Tier | Behavior | Example |
|------|----------|---------|
| **Allow** | Auto-execute, no prompt | `file_read`, `search_content` |
| **Confirm** | Show diff/command, ask Y/n | `file_write`, `shell cmd` |
| **Reject** | Block unconditionally | `rm -rf /`, network exfiltration |

Users can configure per-plugin defaults, override per-session with `--dangerously-auto-approve`, and set workload-specific policies (e.g., "never confirm read, always confirm write"). Each decision is logged to the event stream for audit.

**Why not always confirm?** Every confirmation dialog breaks flow. Sponge's cost ethos applies to human attention too — minimize interruptions, but never silently execute destructive operations.

### Why Multimodal Input?

Real development workflows involve screenshots, PDFs, and diagrams. A text-only harness is blind to half the information a developer works with.

The LLM layer's `Message` model includes a `content_blocks` field supporting multiple types:

```python
@dataclass
class ContentBlock:
    type: Literal["text", "image", "pdf", "tool_use", "tool_result"]
    text: str | None = None
    image_url: str | None = None        # base64 data URI or URL
    pdf_url: str | None = None          # for providers that support PDF
    source: FileSource | None = None    # file path → auto-encode
```

**Cost impact:** Image tokens are expensive (~800-1600 tokens per 1080p image). The context pipeline gains a "multimodal budget" — images dropped from history first under compression, with a placeholder: `[image omitted — N tokens saved]`.

### Why Long-Term Memory?

Session persistence saves/resumes conversations. But Sponge also needs **cross-session memory** — user preferences, project conventions, recurring patterns — to avoid repeating mistakes.

| Memory Layer | Scope | Persistence | Example Content |
|-------------|-------|-------------|----------------|
| **Session** | Single conversation | `~/.sponge/sessions/` | Turn history, cost data |
| **Project** | Current project | `<project>/.sponge/memory.toml` | "Never touch test/fixtures/", "Use httpx not requests" |
| **User** | All projects | `~/.sponge/preferences.toml` | "Default model = Opus 4.7", "Budget ceiling = $5/session" |

The project memory file (`.sponge/memory.toml`) acts like Claude Code's `CLAUDE.md` or Cursor's `.cursorrules` — injected into the system prompt at session start, editable by the user or by the agent itself (with confirmation).

---

## Anti-Patterns

| Anti-Pattern | Why Sponge Avoids It |
|-------------|---------------------|
| **Model routing** | Degrades quality; violates "best model always" principle |
| **Synchronous I/O in hot path** | Blocks event loop; increases wall-clock time per call |
| **Hardcoded cache TTLs** | Static configs miss optimization opportunities |
| **Sending full history every turn** | Maximizes token burn; compression is always cheaper |
| **Expensive sub-agent results** | Sub-agent should condense; best model shouldn't read raw exploration |
| **"Looks correct" validation** | Plugins must show actual command output, not assertions |
| **Custom tool protocol instead of MCP** | Forces third-party tool authors to write two integrations; ecosystem lock-in |
| **Blocking/request-response only** | Hides latency; feels broken for anything longer than a sentence |
| **Silent destructive operations** | No approval gate = `rm -rf /` is one hallucinated command away |
| **No long-term memory** | Repeats same user corrections every session; wastes tokens and patience |
| **Text-only message model** | Blind to screenshots, diagrams, PDFs — half the information in a dev workflow |
| **Provider-specific features without fallback** | Layer 1 compression (Anthropic server-side clearing) silently no-ops on OpenAI |
