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

A harness is an opinionated, batteries-included layer. Sponge has two opinions:

1. **Cost compression is the infrastructure.** Every architectural decision exists to slash token consumption.
2. **The agent must learn from failure.** Every mistake is an investment — extract a lesson, store it, and never pay for that class of mistake again. This is Reflexion: the meta-layer that makes every other layer smarter over time.

---

## Core Loop

The agent loop is intentionally tiny (~30 lines). 95% of complexity lives in the infrastructure that feeds it:

```python
while not done:
    # Before the call: retrieve relevant lessons from reflective memory
    lessons = reflective_memory.query(task)           # "what did I learn last time?"
    messages = context_pipeline.compress(messages)    # prune + mask before call
    messages = inject_lessons(messages, lessons)      # prepend relevant past lessons
    cost = cost_estimator.estimate(messages)          # pre-call cost prediction
    circuit_breaker.check(cost)                       # enforce budget, never downgrade

    async for event in llm.stream(messages):           # streaming by default
        match event:
            case ContentDelta(text=text):
                render(text)                          # incremental display
            case ToolCall(name=name, input=input):
                if approval_gate.ok(name, input):      # approval check
                    result = await execute_tool(name, input)
                    messages.append(result)
            case Usage(tokens_in=in_, tokens_out=out):
                cost_tracker.record(in_, out)          # incremental cost tracking

    # After the call: if it failed, reflect
    if task.failed:
        reflection = await reflect(task, trajectory)  # structured self-evaluation
        lesson = extract_lesson(reflection)            # compress into a rule
        reflective_memory.store(lesson)                # carve it into the pillar
```

## Reflexion Loop

> 照镜子 → 刻字 → 读柱子 — *mirror → carve → read*

Sponge's core philosophy is **Reflexion**: the agent learns from every failure by generating structured self-critique, extracting reusable lessons, and storing them for future retrieval. This is not a bolt-on feature — it is the meta-layer that makes every other cost-reduction mechanism smarter over time.

### The Cycle

```
                    ┌──────────────────────────┐
                    │     REFLECTIVE MEMORY     │
                    │  (lessons carved in stone)│
                    └──────────┬───────────────┘
                               │
            ┌─ RETRIEVE ──────┴───── STORE ───┐
            │  "what did I                   │
            │   learn last                    │
            │   time this                     │
            │   happened?"                    │
            ▼                                 ▲
    ┌───────────────┐                 ┌───────────────┐
    │   ATTEMPT     │                 │   EXTRACT     │
    │   the task    │                 │   LESSON      │
    │   with        │                 │   compress    │
    │   lessons     │                 │   failure →   │
    │   in context  │                 │   rule        │
    └───────┬───────┘                 └───────┬───────┘
            │                                 ▲
            ▼                                 │
    ┌───────────────┐                 ┌───────────────┐
    │   FAIL /      │                 │   REFLECT     │
    │   SUCCEED     │                 │   structured  │
    │   observe     │                 │   self-       │
    │   outcome     │────────────────▶│   evaluation  │
    └───────────────┘                 └───────────────┘
```

### How It Works

1. **Retrieve** — Before attempting a task, Sponge queries reflective memory for lessons whose conditions match the current context (task type, tool set, project state). Matching lessons are injected into the system prompt as decision-guiding context.

2. **Attempt** — The agent executes the task with lessons in context. The lessons don't constrain the agent; they inform it — like A-Jiu reading his pillar before firing the next kiln.

3. **Observe** — The task either succeeds or fails. Failure is detected through: explicit error signals, tool call failures, user corrections, or LLM self-assessment of output quality.

4. **Reflect** — On failure, a separate LLM call (the "bronze mirror") reviews the full trajectory and generates structured self-evaluation. The reflection prompt is Socratic: it asks questions that force the agent to locate the root cause, rather than providing answers. Key questions:
   - What was different about this attempt compared to previous ones?
   - Which specific action (or inaction) led to the failure?
   - Is this a new class of mistake, or a recurrence of a known pattern?
   - What one rule, if followed, would have prevented this?

5. **Extract** — The reflection is compressed into a compact, retrievable lesson:
   ```
   condition: {when does this apply?}
   action: {what was attempted?}
   observed_outcome: {what went wrong?}
   lesson: {what rule should be followed?}
   ```

6. **Store** — The lesson is written to reflective memory, keyed by condition for future retrieval. Like A-Jiu's pillar carvings, lessons are immutable once written (they can be superseded but never deleted — the history of mistakes is itself valuable).

### Why It's Cost-First Architecture

Every failed attempt costs real tokens. A naive agent retries blindly — same context, same mistake, same cost. A Reflexion-equipped agent pays for the failure ONCE:

| Scenario | Naive Agent | Reflexion Agent |
|---|---|---|
| First attempt (failure) | 5,000 tokens | 5,000 tokens + 500 tokens (reflection) |
| Second attempt (retry) | 5,000 tokens (same mistake) | 5,000 tokens (with lesson — succeeds) |
| Third similar task | 5,000 tokens (same mistake again) | 4,000 tokens (lesson in context → fewer iterations) |
| After 10 similar tasks | 50,000 tokens (learns nothing) | ~30,000 tokens (cumulative lessons reduce iterations) |

The reflection call itself costs tokens (~500 for structured evaluation), but this is an investment: it prevents the same 5,000-token failure from recurring. Break-even is typically 1-2 avoided failures.

### Interaction with Existing Layers

| Layer | How Reflexion Amplifies It |
|---|---|
| **Memory-Based Reuse** | Reflective memory is the highest-value memory tier — lessons are more actionable than conventions |
| **Cost Fingerprint + Replay** | Replay measures whether lessons actually reduce tokens on historical trajectories — closes the "should save → does save" gap |
| **Task Decomposition** | Lessons about sub-task boundaries prevent over-decomposition ("don't split X from Y — they share state") |
| **Sub-Agent Condensation** | Lessons about what to search for make exploration more targeted and condensation more efficient |
| **Plugin Routing** | Lessons about plugin reliability inform routing confidence thresholds |
| **Context Compression** | Lessons are immune to compression — they're already maximally compressed (one rule ≈ 20-50 tokens) |

---

## Module Map

```
src/sponge/
├── __init__.py / __main__.py      # Package entry points
│
├── cli/                           # Typer CLI
│   ├── app.py                     # Top-level app + command registration
│   ├── run.py                     # sponge run <task>
│   ├── session_cmd.py             # sponge session [start|resume|chat|list]
│   ├── config_cmd.py              # sponge config [show|set]
│   ├── cost_cmd.py                # sponge cost [session|total|stats]
│   ├── tune_cmd.py                # sponge tune [report|apply|review|history]
│   ├── memory_cmd.py              # sponge memory [list|add|remove]
│   ├── benchmark_cmd.py           # sponge benchmark
│   └── desktop_cmd.py             # sponge desktop
│
├── core/                          # Agent orchestrator
│   ├── agent.py                   # ~30 line while loop
│   ├── task.py                    # Task / TaskResult models
│   ├── session.py                 # Session lifecycle, persistence
│   ├── context.py                 # 5-layer context pipeline
│   ├── context_planner.py         # Per-subtask context planning
│   ├── decomposer.py              # LLM-driven task decomposition
│   └── condenser.py               # Sub-agent result condensation
│
├── llm/                           # Provider-agnostic LLM layer
│   ├── base.py                    # LLMProvider ABC, StreamEvent types
│   ├── anthropic_provider.py      # Claude integration
│   ├── openai_provider.py         # OpenAI integration
│   ├── deepseek_provider.py       # DeepSeek integration
│   ├── openrouter_provider.py     # OpenRouter integration
│   ├── factory.py                 # Provider selection
│   └── token_counter.py           # Token counting (tiktoken)
│
├── cost/                          # Cost accounting
│   ├── models.py                  # CostEntry, Usage, ModelPricing
│   ├── pricing.py                 # Pricing loader
│   ├── tracker.py                 # Per-call cost tracking
│   └── ledger.py                  # Savings ledger
│
├── cache/                         # Multi-level caching
│   ├── disk_store.py              # SQLite key-value store
│   ├── result_cache.py            # SHA256 exact-match cache
│   ├── semantic_cache.py          # Jaccard-similarity cache
│   └── repo_state.py              # Git HEAD state marker
│
├── plugins/                       # Plugin system
│   ├── base.py                    # Plugin ABC, PluginContext, PluginResult
│   ├── registry.py                # Plugin discovery & routing
│   ├── mcp_client.py              # MCP JSON-RPC stdio client
│   ├── mcp_plugin.py              # MCP server → Plugin adapter
│   └── builtins/                  # Zero-cost built-in plugins
│       ├── file_ops.py            # File operations
│       ├── shell.py               # Shell execution
│       └── search.py              # Code search (grep)
│
├── sandbox/                       # Isolated execution
│   └── subprocess_sandbox.py      # Local subprocess sandbox
│
├── config/                        # Configuration
│   └── settings.py                # Pydantic Settings (env + TOML)
│
├── telemetry/                     # Self-tuning
│   ├── collector.py               # Cost fingerprint → SQLite
│   ├── models.py                  # CostFingerprint, TuningProposal
│   ├── analyzer.py                # 3 signal detectors
│   └── tuner.py                   # Proposal store + shadow A/B
│
├── memory/                        # Long-term memory
│   └── store.py                   # Project memory (.sponge/memory.toml)
│
├── approval/                      # Approval gates
│   └── __init__.py                # Approval level constants
│
├── desktop/                       # Desktop UI
│   └── server.py                  # HTTP server for browser chat
│
├── data/                          # Static data
│   └── pricing.toml               # Provider pricing table
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

### Why Reflexion?

Most agent harnesses are amnesiacs. They execute task after task with the same default behavior, never learning from mistakes. Users repeat the same corrections. Tokens are burned re-deriving the same conclusions. This is architecturally wasteful: every repeated mistake is a tax on the user's API bill.

Reflexion (Shinn et al., 2023) showed that language agents can learn from verbal self-critique — no weight updates, no RL, just structured reflection stored as memory. Sponge adopts this as its core philosophy because it aligns perfectly with the 1/10 cost target:

- **Caching avoids re-computation.** Reflexion avoids re-failure.
- **Compression reduces tokens per call.** Reflexion reduces the NUMBER of calls.
- **Both are multiplicative.** A call that is both cached AND informed by lessons is the cheapest possible call.

The bronze mirror metaphor captures the key insight: the mirror isn't magic — it's just a structured way of asking yourself questions. The LLM reflecting on its own trajectory is the same LLM that ran it; what changes is the *prompt* (from "solve this task" to "diagnose why you failed") and the *output* (from an action to a lesson).

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
