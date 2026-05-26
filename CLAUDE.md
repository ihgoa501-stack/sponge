# Sponge — CLAUDE.md

## Project Identity

- **Mission**: Reduce LLM cost to **1/10 of the original** through agent engineering architecture alone — same model, same task quality, one-tenth the tokens.
- **Status**: Phase 0-3 components implemented. Agent loop, cost fingerprint, self-tuning closed loop, 4 providers, plugin routing, context compression, semantic cache, task decomposition, sub-agent condensation, progressive context loading, memory-based reuse. 106 tests, 59 source files. Some Phase 3 modules need additional test coverage (desktop, MCP, memory store).
- **Core principle**: The agent architecture itself is the cost-reduction engine. Not bolt-on cache layers. Not model downgrading. Every design decision — how tasks are decomposed, how context is loaded, how sub-agents return results, how memory is structured — exists to slash token consumption. The target is 1/10.
- **Name metaphor**: Like a sponge — absorb maximum context, squeeze out maximum value. Every token sent to the model must justify its existence.
- **Key differentiator**: Not features — architecture. Competitors add caching and compression as afterthoughts. Sponge designs the agent loop from first principles around token minimization. Task decomposition, progressive context loading, sub-agent condensation, and memory-based reuse are not features on a roadmap — they are the roadmap. Everything else is secondary.

## Current Agent Instructions

If you are an implementation agent, do not infer the build order from this file alone.

Read these files first, in order:

1. `docs/project-plan.md` — planning source of truth and revised phase order.
2. `docs/worker-agent-guide.md` — implementation rules for worker agents.
3. The specific phase plan assigned to you under `docs/superpowers/plans/`.

Current implementation target:

```text
docs/superpowers/plans/2026-05-24-phase-1-cost-fingerprint.md
```

Phase 1 includes: agent loop, streaming LLM calls, exact result cache, savings ledger, and cost fingerprint recording. Do not implement context compression, plugin routing, semantic cache, sub-agents, or multimodal — those are Phase 3+ commodity features.

Local development environment:

```bash
/Users/lc/.local/bin/python3.12 --version
/Users/lc/Library/Python/3.9/bin/uv --version
```

Use `uv` with Python 3.12 for local development. The system `python3` is 3.9 and is not suitable for this project.

## Core Innovation — Architecture as Cost Reduction

The target: **same model, same task quality, 1/10 the tokens.** This is not achieved by adding caching and compression as afterthoughts. It is achieved by designing the agent architecture from first principles around token minimization:

1. **Task Decomposition** — complex tasks are broken into small, focused sub-tasks. Each sub-task carries only the context it needs, not the entire conversation history. A 10-step refactor doesn't send all 10 steps' context to every call.

2. **Progressive Context Loading** — context is loaded incrementally, not dumped upfront. The model sees only what's relevant to the current step. Repository structure, file contents, and tool outputs are fetched on demand, not pre-loaded.

3. **Sub-Agent Condensation** — exploration (code search, file reading, test running) happens in isolated sub-agents. The main model receives condensed results with source references, not raw transcripts. A 50,000-token exploration becomes a 500-token summary.

4. **Memory-Based Reuse** — the agent remembers decisions, patterns, and project conventions across sessions. It doesn't re-derive the same conclusions. Project-level memory eliminates repeated context.

5. **Cost Fingerprint + Replay** — every call records why it cost money. Historical fingerprints are replayed to measure the impact of architectural changes on real workloads. The self-tuning loop closes the gap between "should save tokens" and "does save tokens."

6. **Plugin Routing** — tasks that don't need LLM reasoning (file ops, shell commands, search) bypass the model entirely. $0 cost, 0 tokens.

The savings ledger tracks each mechanism independently, so the 1/10 claim is auditable per workload.

## Coding Capability Status

- **Phase 0-2 (complete, tested):** single/multi-turn conversations, cost tracking, self-tuning, context compression, plugin routing, 4 LLM providers, exact + semantic cache, savings ledger, CLI.
- **Phase 3 (implemented, needs test coverage):** task decomposition, sub-agent condensation, progressive context loading (ContextPlanner), memory-based reuse (ProjectMemory), desktop server, MCP plugin.
- **Phase 4 (planned):** approval gates & permissions (stub at `src/sponge/approval/`).

## What is an Agent Harness

The LangChain team defines three distinct layers in the agent stack:

| Layer | What it provides | Examples |
|-------|-----------------|----------|
| **Framework** | Abstractions + Integrations (models, tools, agent loop, middleware) | LangChain, CrewAI, Vercel AI SDK, OpenAI Agents SDK, Google ADK |
| **Runtime** | Durable execution, streaming, human-in-the-loop, persistence, low-level orchestration | LangGraph, Temporal, Inngest |
| **Harness** | Predefined tools, prompts, subagents, planning, filesystem, context management | Deep Agents SDK, Claude Agent SDK, Manus |

A **harness** is an opinionated, batteries-included layer above the runtime — it provides the agent loop, tool execution, context management, sub-agent spawning, memory, sandboxing, and planning infrastructure. The harness should be **as thin as possible** — Claude Code's core loop is ~30 lines. 95% of complexity lives in infrastructure (tools, context, permissions, sandboxing), not in the agent loop itself.

Sponge is a harness whose infrastructure is **cost-first by architecture**. Unlike other harnesses where cost is an afterthought, every layer in Sponge is designed to slash the token footprint of calls to the user's chosen model.

## Correct Positioning

**What Sponge is NOT**: a model router that picks a cheaper model for simpler tasks.

**What Sponge IS**: a cost-compression harness that makes whatever model you choose cheaper to run. The infrastructure ensures each call consumes as few tokens as possible:

- **80%+ cache hit rate** via prompt caching + result caching + semantic caching
- **40-50% token reduction** via context compression (masking, pruning, compaction)
- **Zero-token tasks** via plugin routing (file_ops, shell, MCP servers)
- **Condensed sub-agent results** → model only sees summaries, not raw exploration
- **Local preprocessing** → compress prompts before they hit the cloud
- **Streaming by default** → characters appear in real-time, not a 30s freeze
- **Approval gates** → three-tier permissions, never silently destructive
- **Long-term memory** → project-level `.sponge/memory.toml` avoids repeating mistakes
- **Multimodal input** → images, PDFs, and diagrams alongside text

The benchmark Sponge targets: **top-tier model quality at substantially lower cost** purely through infrastructure savings — no model downgrade.

## Project Structure

```
src/sponge/
├── __init__.py / __main__.py      # Package entry points
├── cli/                           # CLI layer (typer)
│   ├── app.py                     # Top-level app + command registration
│   ├── run.py                     # sponge run <task>
│   ├── session.py                 # sponge session [start|resume|list]
│   ├── config_cmd.py              # sponge config [show|init|set]
│   └── cost_cmd.py                # sponge cost [--task|--session|--export]
├── core/                          # Core agent orchestrator
│   ├── agent.py                   # Agent class — main orchestrator (~30 line while loop)
│   ├── task.py                    # Task / TaskResult models
│   ├── session.py                 # Session lifecycle, persistence
│   ├── context.py                 # 5-layer context pipeline (mask→prune→summarize→slide)
│   └── event_stream.py            # Append-only event log (audit, debug, crash recovery)
├── llm/                           # Provider-agnostic LLM layer
│   ├── base.py                    # LLMProvider ABC, Message, ChatResponse, Usage
│   ├── anthropic_provider.py      # Anthropic Claude provider
│   ├── openai_provider.py         # OpenAI provider
│   ├── factory.py                 # ProviderFactory
│   ├── cost_estimator.py          # Pre-call cost estimator (tiktoken + pricing table)
│   └── token_counter.py           # Token counting helpers
├── cost/                          # Token/cost accounting
│   ├── models.py                  # CostEntry, CostSummary, ModelPricing
│   ├── tracker.py                 # CostTracker — per-call/task/session
│   ├── reporter.py                # Formatted reports + exports
│   └── budget.py                  # Budget ceiling enforcement
├── cache/                         # Multi-level caching
│   ├── base.py                    # Cache ABC
│   ├── result_cache.py            # Exact-match result cache (SQLite)
│   ├── prompt_cache.py            # Provider-agnostic prompt caching manager
│   ├── semantic_cache.py          # Embedding-similarity cache
│   └── disk_store.py              # SQLite key-value store
├── sandbox/                       # Isolated code execution
│   ├── base.py                    # Sandbox ABC
│   ├── docker_sandbox.py          # Docker container sandbox
│   ├── e2b_sandbox.py             # E2B sandbox-as-a-service (Firecracker)
│   └── subprocess_sandbox.py      # Local subprocess (development only)
├── plugins/                       # Plugin & pre-processor system
│   ├── base.py                    # Plugin ABC, PluginContext, PluginResult
│   ├── registry.py                # PluginRegistry — discovery & routing
│   ├── mcp_server.py              # MCPServerPlugin — MCP server lifecycle & tool proxy
│   ├── sub_agent.py               # SubAgentPlugin — isolated execution, condensed results
│   ├── preprocessor.py            # Local preprocessing pipeline (before cloud call)
│   └── builtins/                  # Bundled plugins
│       ├── file_ops.py            # File operations (zero LLM cost)
│       ├── shell.py               # Shell execution (zero LLM cost)
│       ├── search.py              # Code search (sub-agent, condensed output)
│       └── review.py              # Code review (sub-agent, condensed output)
├── config/                        # Configuration management
│   ├── settings.py                # Pydantic Settings model
│   └── loader.py                  # TOML config loading + env var interpolation
├── memory/                        # Long-term memory
│   ├── base.py                    # MemoryStore ABC
│   ├── project_memory.py          # Project-level memory (.sponge/memory.toml)
│   ├── user_preferences.py        # User-level preferences (~/.sponge/prefs.toml)
│   └── injector.py                # Memory → system prompt injection
├── approval/                      # Approval gates & permissions
│   ├── base.py                    # ApprovalPolicy ABC
│   ├── chain.py                   # Approval chain (allow → confirm → reject)
│   ├── policies.py                # Built-in policies
│   └── session_overrides.py       # Per-session overrides (--auto-approve)
├── telemetry/                      # Self-optimizing cost intelligence
│   ├── collector.py                # TelemetryCollector — per-call metrics
│   ├── models.py                   # TelemetryEntry, UsagePattern, TuningResult
│   ├── analyzer.py                 # PatternAnalyzer — detect optimization opportunities
│   ├── tuner.py                    # ParameterTuner — auto-adjust thresholds & TTLs
│   └── feedback.py                 # FeedbackLoop — measure impact, reinforce/discard
└── utils/                         # Shared utilities
    ├── logging.py                 # Structured logging
    ├── errors.py                  # Exception hierarchy
    └── retry.py                   # Async retry with exponential backoff
```

## Architecture Overview

### Design Philosophy — One Model, Declining Cost

Sponge uses whatever model the user configures for every call.
The infrastructure's sole purpose is to minimize the token footprint of those calls.

Every layer of the harness answers the same question:
**"What would a naive implementation send to the model, and how can Sponge send less?"**

### Core Loop

The agent core is intentionally tiny — a **~30 line while loop** modeled after
Claude Code's proven architecture:

```
while not done:
    messages = context_pipeline.compress(messages)   # prune + mask before call
    cost = cost_estimator.estimate(messages)         # pre-call cost prediction
    circuit_breaker.check(cost)                      # enforce budget

    async for event in llm.stream(messages):          # streaming by default
        match event:
            case ContentDelta(text=text):
                render(text)                         # incremental display
            case ToolCallEvent(name=name, input=input):
                if approval_gate.ok(name, input):     # approval check
                    result = await execute_tool(name, input)
                    messages.append(result)
                else:
                    log(f"Rejected: {name}")
            case UsageEvent(tokens_in, tokens_out, ...):
                cost_tracker.record(tokens_in, tokens_out)  # final tally
# 95% of complexity lives in infrastructure, not this loop
```

### Data Flow (Full Cost-Aware Pipeline)

```
sponge run "task"
  │
  ▼
[Event Stream] TaskStarted (audit & crash recovery)
  │
  ▼
[Cache Check] SHA256(task + system + tools) → Multi-level lookup
  ├─ Exact HIT (SQLite) → return cached (cost: $0)
  ├─ Semantic HIT (cosine ≥ 0.95) → return cached (cost: $0.0001)
  └─ MISS
       │
       ▼
  [TaskClassifier] (<1ms, zero-cost keyword matching)
   └─ Determine task type for context construction (not model routing)
       │
       ▼
  [Memory Injection] Project + user memory → system prompt
   └─ .sponge/memory.toml + ~/.sponge/preferences.toml
       │
       ▼
  [Plugin Route] PluginRegistry.best_match()
   ├── Plugin match → [Approval Gate] check policy
   │   ├── ✅ Allow → Plugin.execute()
   │   │   ├── Native (file_ops, shell) → Cost: $0, no LLM call
   │   │   ├── MCP server → MCPServerPlugin proxy → tool call
   │   │   └── SubAgent → isolated execution → condensed result returned
   │   ├── ❓ Confirm → prompt user → execute / cancel
   │   └── 🚫 Reject → log + skip
   │
   └── No plugin → Requires LLM
       │
       ▼
  [Preprocessor] Local model (Ollama, optional)
   ├─ Prompt compression: long prompts shortened locally
   ├─ Scaffolding: draft generated locally → model polishes
   └─ Fail-open: if unavailable, pass through directly
       │
       ▼
  [Cost Estimator] Pre-call cost prediction
   └─ tiktoken scan + pricing table → exact $ estimate (<1ms)
       │
       ▼
  [Circuit Breaker] 3-axis budget check
   ├─ Single call ≤ per-call limit? → pass
   ├─ Cumulative ≤ 80% budget? → warn; ≤ 100%? → block
   └─ Steps ≤ max? → pass (else force-end)
   │
   NOTE: Budget exceeded = stop.
       │
       ▼
  [Context Compressor] 5-layer pipeline
   └─ mask → prune → compact → slide → messages for model
       │
       ▼
  [LLMProvider.stream()] → Streaming call to Opus 4.7 / GPT-5.5
   ├─ ContentDelta → CLI render (characters appear in real time)
   ├─ ToolCallEvent → Approval Gate → execute_tool
   └─ UsageEvent → incremental cost tally
       │
       ▼
  [Memory Update] Agent may suggest memory.toml edits → user confirms
       │
       ▼
  [CostTracker.record()] → [Cache.write()] → [EventStream: TaskCompleted]
       │
       ▼
  [TelemetryCollector.log()] ← every decision, every metric    ◀───┐
       │                                                          │
       ▼                                                          │
  Return TaskResult + CostSummary + SavingsReport                 │
                                                                  │
  ┌──────────────────────────────────────────────────────────────┘
  │
  ▼  (background, after session)
  [PatternAnalyzer] → detect optimization opportunities
  [FeedbackLoop] → test parameter changes, measure impact
  [ParameterTuner] → auto-apply winning configurations
  │
  ▼  (next session)
  The harness is now 2-5% cheaper than last time.
```

### Cost Optimization Strategy — How Any Model Becomes Affordable

Every token sent to the model is scrutinized:

| Layer | What it does | Expected Savings |
|-------|-------------|-----------------|
| **Result Cache** | SHA256 exact-match → $0 for repeat tasks | 100% on cached hits |
| **Prompt Cache** | System prompt + tool defs + history at 10% input cost | 90% on cached reads |
| **Semantic Cache** | Cosine ≥ 0.95 → reuse similar result | ~99.9% on cached hits |
| **Context Compression** | Mask old tool outputs, prune low-signal turns, compact history | 40-60% token reduction |
| **Sub-Agent Summaries** | Deep work in isolated context, only condensed result to model | 5-20x compression on exploration |
| **Local Preprocessing** | Ollama compresses prompts / generates drafts before cloud call | 45-79% on compressed prompts |
| **Plugin Routing** | File ops, shell, code search → executed locally, $0 | 100% on plugin tasks |
| **Circuit Breaker** | Hard budget stops prevent runaway costs | Catches infinite loops |

Target outcome: deliver the same reasoning quality at an effective
cost per task comparable to one tier down — purely through infrastructure savings.

### Adaptive Optimization — Self-Tuning Infrastructure (越用越省钱)

Sponge's most radical feature: the harness **watches its own data and optimizes itself**.
Every call, cache hit, compression decision, and budget event feeds into a local
telemetry store. A background optimization engine analyzes this data to find
patterns, test parameter changes, and auto-apply winning configurations.

The net effect: **the more you use Sponge, the more it saves.** Each session
leaves the harness 2-5% cheaper than the last session found it.

#### Telemetry Collection (Always-On, Local-First)

The `TelemetryCollector` records every decision point as structured telemetry:

| Event | Fields Captured | Purpose |
|-------|----------------|---------|
| **LLM call** | tokens_in, tokens_out, cache_hit/miss, cost, latency, model | Track spend patterns |
| **Cache decision** | key_hash, cache_level (result/semantic/prompt), hit/miss, ttl_used | Tune cache strategy |
| **Compression** | pre/post token counts, layer used (1-5), compression ratio | Optimize thresholds |
| **Sub-agent** | task_type, tokens_consumed, tokens_returned, compression_ratio | Tune delegation |
| **Circuit breaker** | trigger axis, budget consumed, limit value | Calibrate thresholds |
| **Plugin** | plugin_name, zero_cost (yes/no), latency | Track routing efficiency |

All telemetry is stored locally in `~/.sponge/telemetry/` as append-only SQLite.
No data leaves the machine. Offline analysis, full privacy.

#### Pattern Analysis — What Gets Optimized

The `PatternAnalyzer` runs after each session on background threads. It looks for:

| Signal | Optimization | Example |
|--------|-------------|---------|
| **Cache gap** | Session cadence >5 min → switch to 1h TTL for system prompt | "User takes coffee breaks between prompts" |
| **Compression waste** | Compression ratio <1.2x → raise masking threshold | "Masking isn't saving much, be more aggressive" |
| **Budget slack** | Sessions end at 42% budget → lower ceiling (P50→P75) | "Budget is too generous, tighten it" |
| **Task repeat** | SHA256 repeats cluster → bump result cache TTL | "User asks the same question every morning" |
| **Sub-agent waste** | Sub-agent returns >10K tokens → enable summarization | "Sub-agent giving back too much raw data" |
| **Preprocessor gap** | Long prompts (>5K tokens) bypass local preprocessor → suggest enabling | "These could be compressed locally first" |
| **Provider price change** | Pricing delta detected → recalculate break-even for all cache strategies | "Opus 4.7 cache write price changed" |

#### Adaptive Parameters — What Self-Tunes

All parameters start with sensible defaults but **auto-adjust** from telemetry:

| Parameter | Default | Tuned By | What It Changes |
|-----------|---------|----------|-----------------|
| `prompt_cache_ttl` | 5 min | Request cadence analysis | Choose 5m vs 1h per cache point |
| `masking_threshold` | 2000 tokens | Compression efficiency data | Raise/lower observation masking trigger |
| `pruning_min_turns` | 5 | Context window utilization | Keep more/less history before pruning |
| `budget_ceiling` | P95 | Historical task cost distribution | Auto-calibrate budget limit |
| `result_cache_ttl` | 24 hours | Repeat task frequency | Extend/shorten exact-match cache life |
| `semantic_threshold` | 0.95 cosine | False positive tracking | Relax/tighten semantic match threshold |
| `subagent_condensation` | Enabled | Sub-agent output token analysis | Force/enlarge condensation on summary |
| `preprocessor_trigger` | Prompt >2K tokens | Compression ratio data | When to route through local preprocessor |
| `circuit_breaker_single` | $2.00 | Per-call cost distribution | Per-call budget limit |

#### Feedback Loop — Measure Before Committing

The `FeedbackLoop` never blindly applies changes. Each candidate optimization goes
through a **3-stage validation pipeline**:

```
1. PROPOSE — Telemetry Pattern detected
   "Prompt cache TTL at 5 min, but request cadence is 8.2 min median.
    Switch system prompt cache to 1h TTL? Estimated savings: $0.04/session."

2. TEST — A/B shadow run
   Run N sessions with proposed change (shadow mode, costs tracked but not committed).
   Compare against baseline. Must show ≥5% improvement at ≥95% confidence.

3. COMMIT — Auto-apply or human gate
   Low-risk changes (<$0.50 estimated impact): auto-apply.
   High-risk changes: stage in config and notify user via `sponge tune --review`.
   Every change logged with before/after metrics in `~/.sponge/tuning_history.json`.
```

Changes that fail the A/B test are **discarded with prejudice** — the same
pattern won't be re-proposed until telemetry shifts significantly.

#### Savings Dashboard

```
$ sponge tune --report
═══════════════════════════════════════════════════════════════
  Sponge Self-Optimization Report
═══════════════════════════════════════════════════════════════
  Sessions analyzed:        247
  Parameters auto-tuned:      3   (2 auto-applied, 1 pending)
  Savings from tuning:    $1.87   (12.1% of total spend)

  ┌─ Recent Changes ─────────────────────────────────────────┐
  │ ✔ prompt_cache_ttl    5m → 1h    +$0.31/session (3 days)  │
  │ ✔ masking_threshold 2000 → 3500  +$0.12/session (1 week)  │
  │ ⏳ budget_ceiling   P95 → P80     -$0.05/session (pending) │
  └──────────────────────────────────────────────────────────┘

  Projected annual savings at current rate: $42.50
═══════════════════════════════════════════════════════════════
```

#### Why No Other Harness Does This

| Reason | Explanation |
|--------|-------------|
| **No cost tracking** | Most harnesses don't even track cost, let alone optimize it |
| **Static configs** | Claude Code, Cursor, Copilot all ship with hardcoded thresholds |
| **Provider opacity** | Hard to self-tune when you don't control the model or caching layer |
| **User friction** | Without auto-tuning, optimization burden falls on user (`/effort` slider, manual model switching) |

Sponge is the first harness whose **cost optimization is a closed loop**:
usage generates data, data generates insights, insights tune parameters,
tuned parameters reduce cost — and the cycle repeats.

#### Implementation — How Self-Tuning Works

The system has four components operating in sequence:

```
┌─────────────────────────────────────────────────────────────┐
│  1. COLLECT    →    2. ANALYZE    →    3. VALIDATE    →    4. APPLY  │
│  Telemetry          Pattern            Feedback              Parameter │
│  Collector          Analyzer           Loop                  Tuner     │
│                                                                       │
│  (every call)       (post-session)     (shadow A/B)         (commit)  │
└─────────────────────────────────────────────────────────────┘
```

**Component 1 — Telemetry Collector** (runs inline, <0.1ms overhead)

A thin wrapper around the SQLite store. Every cost-significant operation
calls `collector.log(event)` which queues an async write:

```
# collector.py
class TelemetryCollector:
    def log(self, event: TelemetryEntry):
        """Queue this event for async write. Returns immediately."""
        self._queue.put_nowait(event)  # non-blocking

    async def _flush_loop(self):
        """Background task: batch-write queued events to SQLite."""
        while True:
            batch = await self._drain_queue(timeout=5.0)
            if batch:
                async with self._db.execute_many(
                    "INSERT INTO events VALUES (?,?,?,?)", batch
                ):
                    pass  # commit on context exit
```

SQLite schema (append-only, ~20 bytes per event):

```
CREATE TABLE events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    event_type  TEXT NOT NULL,  -- 'llm_call','cache','compress','subagent',...
    timestamp   REAL NOT NULL,  -- unix epoch, monotonic
    data        TEXT NOT NULL   -- JSON blob, no schema lock-in
);
CREATE INDEX idx_events_session ON events(session_id);
CREATE INDEX idx_events_type ON events(event_type);
```

JSON `data` field examples:

```
// llm_call
{"tokens_in":3420,"tokens_out":812,"cache_hit":true,"cache_write":true,
 "cost":0.018,"latency_ms":420,"model":"claude-opus-4-7"}

// cache_decision
{"level":"result","key_hash":"a3f2b1c...","hit":false,"ttl_hours":24}

// compress
{"pre_tokens":12800,"post_tokens":5100,"layer":2,"ratio":0.40,"method":"masking"}
```

**Component 2 — Pattern Analyzer** (runs post-session, ~50ms)

Runs SQL queries over recent telemetry. No ML needed — the patterns are
simple statistical signals:

```
# analyzer.py
class PatternAnalyzer:
    async def analyze(self, db: aiosqlite.Connection):
        proposals = []

        # Signal 1: request cadence → cache TTL
        gaps = await db.execute("""
            SELECT (julianday(t2.timestamp) - julianday(t1.timestamp)) * 86400 AS gap_sec
            FROM events t1, events t2
            WHERE t1.event_type='llm_call' AND t2.event_type='llm_call'
              AND t2.id = t1.id + 1
              AND t2.timestamp > datetime('now', '-7 days')
        """)
        median_gap = percentile(await gaps.fetchall(), 50)
        if median_gap > 300:  # >5 min
            proposals.append(TuningProposal(
                param="prompt_cache_ttl", from_val="5m", to_val="1h",
                reason=f"Median request gap {median_gap:.0f}s exceeds 5-min TTL",
                estimated_savings=self._estimate_ttl_savings(median_gap),
            ))

        # Signal 2: compression ratio → masking threshold
        ratios = await db.execute(
            "SELECT json_extract(data,'$.ratio') FROM events "
            "WHERE event_type='compress' AND json_extract(data,'$.layer')='2'"
            "  AND timestamp > datetime('now', '-7 days')"
        )
        median_ratio = percentile(await ratios.fetchall(), 50)
        if median_ratio > 0.85:  # barely compressing
            proposals.append(TuningProposal(
                param="masking_threshold", from_val=2000, to_val=3500,
                reason=f"Masking ratio {median_ratio:.0%} too low",
            ))

        # Signal 3: budget slack → budget ceiling
        usages = await db.execute(
            "SELECT json_extract(data,'$.budget_pct') FROM events "
            "WHERE event_type='circuit_breaker' "
            "  AND timestamp > datetime('now', '-30 days')"
        )
        p50 = percentile(await usages.fetchall(), 50)
        if p50 < 0.50:  # median session uses <50% of budget
            proposals.append(TuningProposal(
                param="budget_ceiling", from_val="P95", to_val="P75",
                reason=f"Median usage {p50:.0%} far below budget",
            ))

        # Signal 4: task repeats → result cache TTL
        repeats = await db.execute("""
            SELECT json_extract(data,'$.key_hash') as kh, COUNT(*) as cnt
            FROM events WHERE event_type='cache' AND json_extract(data,'$.level')='result'
              AND json_extract(data,'$.hit')='true'
              AND timestamp > datetime('now', '-7 days')
            GROUP BY kh HAVING cnt >= 3
        """)
        repeat_count = len(await repeats.fetchall())
        if repeat_count >= 5:
            proposals.append(TuningProposal(
                param="result_cache_ttl", from_val=24, to_val=72,
                reason=f"{repeat_count} tasks repeated ≥3x this week",
            ))

        return proposals
```

Each `TuningProposal` is a lightweight dataclass:

```
@dataclass
class TuningProposal:
    param: str            # which knob to turn
    from_val: Any         # current value
    to_val: Any           # proposed value
    reason: str           # human-readable explanation
    estimated_savings: float  # $ per session
    risk: Literal["low","medium","high"]  # auto/or/human
```

**Component 3 — Feedback Loop** (shadow A/B, runs over N sessions)

The key mechanism: **shadow config injection**. When a proposal enters testing,
a fraction of sessions (default 20%) get the new parameter value. Both baseline
and experimental run normally, but the experimental group has a "shadow" flag:

```
# feedback.py
class FeedbackLoop:
    def __init__(self, db: aiosqlite.Connection):
        self.experiments: dict[str, ActiveExperiment] = {}

    async def should_use_shadow(self, exp_id: str) -> bool:
        """20% of sessions get the experimental config."""
        return hash(exp_id + str(datetime.now().date())) % 100 < 20

    async def evaluate(self, exp: ActiveExperiment) -> TuningResult:
        """After N shadow sessions, run statistical test."""
        baseline_costs = await self._fetch_costs(
            exp.param, val=exp.from_val, shadow=False
        )
        shadow_costs = await self._fetch_costs(
            exp.param, val=exp.to_val, shadow=True
        )

        # Mann-Whitney U test (non-parametric, safe for cost data)
        stat, p_value = mannwhitneyu(shadow_costs, baseline_costs, alternative='less')

        savings_pct = (baseline_costs.mean() - shadow_costs.mean()) / baseline_costs.mean()

        if savings_pct >= 0.05 and p_value < 0.05:
            return TuningResult(verdict="commit", savings_pct=savings_pct, p_value=p_value)
        else:
            return TuningResult(verdict="discard", savings_pct=savings_pct, p_value=p_value)
```

The `mannwhitneyu` function uses Python's `scipy.stats` if available, otherwise
falls back to a simplified implementation (~30 lines, no dependency).

**Component 4 — Parameter Tuner** (applies winning configs)

```
# tuner.py
class ParameterTuner:
    async def apply(self, result: TuningResult, proposal: TuningProposal):
        async with aiosqlite.connect(self.tuning_db) as db:
            await db.execute("""
                INSERT INTO tuning_history (param, from_val, to_val, savings_pct,
                    p_value, verdict, applied_at)
                VALUES (?,?,?,?,?,?,datetime('now'))
            """, (proposal.param, str(proposal.from_val), str(proposal.to_val),
                  result.savings_pct, result.p_value, result.verdict))

        if result.verdict == "commit":
            await self.config.set(proposal.param, proposal.to_val)
            logger.info(f"Auto-tuned {proposal.param}: {proposal.from_val} → "
                        f"{proposal.to_val} (saves {result.savings_pct:.1%})")
```

**Config Layer — Plugpoint for All Parameters**

Every tunable parameter is wired through a central config system that supports
per-parameter overrides without restart. This is the key enabler: the analyzer
proposes, the feedback loop tests, the tuner commits — and the running harness
picks up the new value immediately from the config layer.

```
# config/settings.py
class SpongeConfig(BaseSettings):
    # All self-tuning parameters with defaults
    prompt_cache_ttl: Literal["5m","1h"] = "5m"
    masking_threshold: int = 2000
    pruning_min_turns: int = 5
    budget_ceiling: str = "P95"       # or "P75","P50","manual:$N"
    result_cache_ttl: int = 24        # hours
    semantic_threshold: float = 0.95  # cosine
    subagent_condensation: bool = True
    preprocessor_trigger: int = 2000  # token threshold
    circuit_breaker_single: float = 2.00  # dollars

    class Config:
        env_prefix = "SPONGE_"
        # Reads from ~/.sponge/config.toml, overridable by env vars
```

**End-to-End Flow (What Happens When)**

```
Session 1-10 (baseline collection, no tuning):
  └─ Collector silently logs every event to SQLite
  └─ Analyzer runs post-session, finds nothing yet (not enough data)

Session 11 (analyzer triggers):
  └─ Analyzer: "Median request gap = 8.2 min, but cache TTL = 5 min"
  └─ Proposal: prompt_cache_ttl → 1h, estimated $0.04/session
  └─ FeedbackLoop: Start A/B experiment

Session 12-31 (20 sessions, 20% shadow):
  └─ 4 sessions get 1h TTL (shadow), 16 sessions keep 5m TTL (baseline)
  └─ All costs tracked separately

Session 32 (evaluation):
  └─ FeedbackLoop: Shadow mean $0.14, baseline mean $0.18
  └─ Savings = 22.2%, p = 0.012
  └─ Tuner: COMMIT → config.toml now has prompt_cache_ttl = "1h"

Session 33+ (benefit realized):
  └─ Every session now uses 1h TTL for system prompt cache
  └─ $0.04 saved per session, automatically, no user action
```

**Simplicity as a Design Constraint**

- No external ML framework. Pure SQL + simple stats.
- No server. SQLite in `~/.sponge/telemetry/`.
- No data leaving the machine. Privacy by architecture.
- Total code footprint for all four components: ~500 lines.
- Each component independently testable with mock DB fixtures.

### Context Pipeline — Minimizing Tokens Before Every Call

The context pipeline runs **before every call to the model**, not just at
92% threshold. It asks: "How few tokens can we send and still get the same quality?"

```
Layer 1: Server-Side Tool Result Clearing (Anthropic API)
   clear_tool_uses_20250919 + clear_thinking_20251015
   Removes server-side token cost for old tool results and thinking blocks.
   Context awareness gives model explicit <budget> + <system_warning> tokens.

Layer 2: Observation Masking (primary token reduction)
   Replace old tool outputs with "[...N tokens omitted...]"
   Claimed: 52% cost reduction, +2.6% solve rate (JetBrains Research)
   NOTE: This claim is cited in agent design literature but we have not
   yet independently verified the original paper or reproduced the results.
   Rules:
   - ONLY mask tool and user messages
   - NEVER mask assistant reasoning content
   - Keep last 3 tool results intact (model needs current context)

Layer 3: Message Pruning (importance scoring)
   Score each turn: recent > old, errors > clean, reasoning > observation
   Keep minimum 5 turns. Drop low-scoring old ones first.

Layer 4: LLM Summarization (last resort)
   Only if masking + pruning insufficient AND turns ≥ 10 AND ≥ 3 turns remaining.
   Prefer server-side compaction (Anthropic beta) where available.
   Use DeepSeek V4-Flash ($0.14/MTok) or local Ollama for summary into <300 tokens.
    The model sees the summary, not the raw history.

Layer 5: Sliding Window (hard floor)
   Always keep system prompt + last N turns within limit.
   Combine with Anthropic's prompt_cache_retention for extended context.
```

**Server-side compaction** (Anthropic beta, `compact-2026-01-12`) handles
summarization at the API level — the API detects a configurable threshold
(default 150K tokens), generates a summary, and server-side discards all
content before the compaction point. Supports custom instructions,
`pause_after_compaction`, and budget enforcement via compaction counter.

**Context awareness** (Sonnet 4.6, Haiku 4.5, 2026): models receive explicit
`<budget:token_budget>` and `<system_warning>Token usage: N/M</system_warning>`
to persist until the very end rather than guessing remaining budget.

**Session as context object** (Anthropic Managed Agents pattern): the session
log lives outside the context window. The harness can `getEvents()` to retrieve
positional slices, rewind, or interrogate context programmatically. Different
compression strategies for different access patterns.

### Prompt Caching — Make the Best Model's Reads Cheap

The primary lever for making expensive model calls affordable: **90% off cached reads**.
The goal is to maximize cache hit rate so most input tokens are billed at cache-read
prices, not full input prices.

#### Provider Comparison (Mid-2026)

| | Anthropic | OpenAI | DeepSeek |
|---|---|---|---|
| **Default TTL** | 5 min | 5-10 min (in-memory) | Hours-days (disk) |
| **Extended TTL** | 1h (2x write cost) | 24h (extended retention) | N/A (automatic) |
| **Write premium** | 25% (5m) / 100% (1h) | None | None |
| **Read discount** | 90% | up to 90% | ~98% |
| **Cache control** | API (`cache_control`) | `prompt_cache_key` | None (auto) |
| **Pre-warming** | Yes (`max_tokens: 0`) | No | N/A |
| **Storage cost** | None | None (in-memory) | None |

#### Anthropic Caching

Default: `cache_control: {"type": "ephemeral"}`. Supports `{"type": "ephemeral", "ttl": "1h"}`.
Automatic caching: single breakpoint declaration auto-moves forward as conversation grows.

| Cache Point | Placement | TTL | Condition |
|-------------|-----------|-----|-----------|
| System prompt | Breakpoint #1 | 1h | Always (if >1K tokens) |
| Tool definitions | Breakpoint #2 | 1h | Always |
| Large file content | Breakpoint #3 | 5m or 1h | Content >4K tokens (varies by model) |
| Conversation history | Breakpoint #4 | 5m | History only, not current turn |
| Dynamic tool results | ❌ Never | — | Changes each call; wastes write premium |

**Break-even analysis**: Cache write costs 25% premium, cache read costs 10%.
Need ≥1.3 reads per write to break even. If <2 requests per 5 min, caching
costs MORE than not caching.

**Keep-alive strategies** (for long-running agent sessions):
- 5-min TTL: no-op ping every 4 min with `max_tokens: 1`. Costs ~$0.001/ping.
  Over 1 hour: ~$0.015 (Opus 4.7).
- 1-hour TTL: one write at 2x base ($10/MTok vs $5.00). For 10K token system prompt:
  extra ~$0.05/hour. Wins for systems idle >50% of time.
- Pre-warming: send `max_tokens: 0` request before first real user request to
  populate cache. Only works with 5-min TTL.

**Cycle detection**: `response.usage.cache_read_input_tokens > 0` means cache hit.
`response.usage.cache_creation_input_tokens` tracks cache writes.

#### DeepSeek Caching (Reference)

Always-on disk-based cache. Cache hit discount: ~98% ($0.0028/MTok vs $0.14 input
on V4-Flash). TTL: "hours to days". Best-effort, no hit rate guarantee. Differs
from Anthropic in that it requires no API changes — the Prefix-Cache First design
pattern (as used by Reasonix) locks byte-prefix stability for maximal hit rates.

#### OpenAI Caching (Reference)

Automatic, no write premium. `prompt_cache_retention`: `"in_memory"` (5-10 min)
or `"24h"` (GPT-5.x). `prompt_cache_key` for routing control. Cache overflow at
~15 requests/minute per prefix+key combo.

### Cost System

| Metric | Purpose |
|--------|---------|
| Median task cost | Typical spend |
| **P95 task cost** | **Budget ceiling** (can be 35x median!) |
| Cost per successful outcome | ROI measurement |
| Savings vs naive | How much the infrastructure saved |
| Circuit breaker | 3-axis check before every LLM call |

The **Cost Circuit Breaker** checks before every LLM call:
1. **Single call cost** ≤ per-call limit? (estimated via token counter + pricing table, <1ms)
2. **Cumulative cost** ≤ 80% budget? → warn; ≤ 100%? → **block (stop)**
3. **Step count** ≤ max steps? → prevent infinite loops

**Budget enforcement rule**: If budget is exceeded,
the task is paused for user approval or terminated.

### Cost Optimization Levers (Ordered by Impact)

| Lever | Impact | Method |
|-------|--------|--------|
| Result caching | 最高 | Exact-match repeat tasks = $0 |
| Prompt caching | 最高 | 90% off cached reads; 80%+ hit rate target |
| Context compression | 高 | 40-60% fewer tokens via masking + pruning + compaction |
| Plugin routing | 高 | No-LLM tasks remove model calls entirely |
| Sub-agent architecture | 高 | Condensed summaries → model sees ~5% of raw data |
| Local preprocessing | 中 | Ollama compresses prompts, generates drafts (45-79% savings) |
| Semantic caching | 中 | Similar-threshold reuse (cosine ≥ 0.95) |
| Circuit breaker | 中 | Catch runaway loops, enforce budget |

### Mid-2026 Model Pricing Reference

Official API prices (USD per million tokens):

| Model | Input | Output | Cache Read | Notes |
|-------|-------|--------|------------|-------|
| **Claude Opus 4.7** | $5.00 | $25.00 | $0.50 | New tokenizer: +35% tokens |
| **GPT-5.5** | $5.00 | $30.00 | $0.50 | Default 24h cache retention |
| **Claude Sonnet 4.6** | $3.00 | $15.00 | $0.30 | Context awareness built-in |
| **GPT-5.4** | $2.50 | $15.00 | $0.25 | Strong code-gen |
| **Claude Haiku 4.5** | $1.00 | $5.00 | $0.10 | Context awareness built-in |
| **DeepSeek V4-Flash** | $0.14 | $0.28 | $0.0028 | 98% cache discount |
| **DeepSeek V4-Pro** | $0.435* | $0.87* | $0.0036* | *Promo through May 2026 |
| **Gemini 3.5 Flash** | $1.50 | $9.00 | — | Frontier agent/coding |

**Sponge's default model**: Claude Opus 4.7 ($5/$25 per MTok) or GPT-5.5 ($5/$30 per MTok).

**The question Sponge answers**: Can the harness make any model cost significantly less
than naive usage? Example: Opus 4.7 effective cost approaching Sonnet 4.6 pricing —
purely through infrastructure savings (cache + compression + preprocessing).

### Task Classifier (Zero-Cost)

Pure-Python keyword classifier, <1ms, no API call. 3 layers:
- Exact phrase match → highest weight
- Keyword match → medium weight
- Levenshtein fuzzy match (≤2) → low weight

~80-85% accuracy. Used for context construction and plugin routing — NOT for
model selection. The model never changes; the task type determines which
context templates and plugins are engaged.

### Local Triage (Optional)

Local Ollama (or other on-device model) as preprocessing layer before cloud calls:
- **Prompt Compression**: long user prompts shortened locally (45-79% savings before hitting cloud)
- **Draft Scaffolding**: local model generates rough draft → cloud model polishes and refines
- **Context Summarization**: raw exploration data condensed locally before model sees it
- Fail-open: if local model unavailable, pass through to cloud directly. No quality loss.

## Sub-Agent Architecture — Cheap Context for Expensive Models

Sub-agents are the most powerful cost compression pattern in Sponge: deep work
happens in isolated, cheap context windows; only condensed results reach the
model.

### The Cost Argument

A sub-agent can burn 100K tokens on exploration at DeepSeek V4-Flash prices
($0.014 total input), then return a 1K-token summary. The model sees 1K
tokens instead of 100K — a 100x reduction in expensive tokens. The saved 99K
tokens on Opus 4.7 would have cost $0.50.

### Coordination Patterns

| Pattern | Description | Where Main Model Sits |
|---------|-------------|----------------------|
| **Dispatch-Condense** | Sub-agents explore in parallel → main model synthesizes condensed results | Main model as synthesizer |
| **Draft-Review** | Local/cheap model drafts → main model polishes | Main model as editor |
| **Generator-Validator** | Sub-agent generates → main model quality-checks | Main model as gatekeeper |
| **Lead-Worker** | Main model decomposes → workers execute → main model integrates | Main model as orchestrator |

### Design Rules (from Claude Code's proven patterns)

1. **No nested sub-agents**: prevents infinite recursion and context explosion.
   Chain from main conversation instead.
2. **Fresh context**: non-fork subagents start with clean context (system prompt
   + delegation message only).
3. **Tool restriction as security boundary**: Read-only agents can't write;
   sandboxed agents only access specific directories.
4. **Git worktree isolation**: subagent runs in temporary worktree. Clean copy,
   changes merged back. Lighter than full VM isolation.
5. **Condensed outputs**: sub-agent returns structured summary, not raw logs.
   The harness forces condensation before results reach the main model.

## Sandbox Strategies

Multiple isolation levels to match trust requirements:

| Level | Technology | Use Case |
|-------|-----------|----------|
| **Process** | Subprocess (local) | Development/debugging only |
| **Filesystem** | Git worktree | Code-gen sub-agents, safe but not true isolation |
| **Container** | Docker | Standard production sandbox |
| **MicroVM** | E2B (Firecracker) | Untrusted code, stronger isolation |
| **Pluggable** | Modal, Daytona, Deno | Swap without changing agent code |
| **Managed** | Anthropic Managed Agents | No infrastructure to manage |

## MCP Integration — Ecosystem Compatibility

Sponge's plugin system is **MCP-native**. The `Plugin ABC` wraps MCP servers as first-class citizens via `MCPServerPlugin`.

**Why MCP?** MCP (Model Context Protocol) is the industry standard — Claude Code, Cursor, Copilot all support it. Building a custom protocol forces every tool author to write two integrations.

**Architecture:**
- Native builtins (`file_ops`, `shell`) are implemented directly for zero overhead
- Third-party tools go through MCP: `MCPServerPlugin` handles spawn → handshake → tool cache → call → shutdown
- Tool schemas are cached in memory (refresh: 5min)
- MCP servers configured in `~/.sponge/config.toml` with per-tool approval overrides

**Startup:** MCP servers are cold-started on first use (1-3s). They persist for the session.
**Security:** MCP tools go through the same approval gate as native plugins. Remote SSE servers are opt-in only.

### Configuration

```toml
[mcp.servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]

[mcp.servers.filesystem.approval]
write_file = "confirm"
delete_file = "reject"
```

**Tool routing priority:** Native builtins → MCP tools → LLM fallback. Fastest path wins.

---

## Streaming Responses

Sponge streams by default. The core loop uses `async for event in llm.stream(messages)` rather than a blocking `llm.chat()`.

**Two-level pipeline:**
- **Level 1 (hot path):** LLM stream → SSE → CLI render. Characters appear in real-time.
- **Level 2 (cool path):** Sub-agent streams → parent consolidates → single user-facing output.

**Stream event types:**
- `ContentDelta` — incremental text output
- `ToolCallEvent` — tool invocation (goes through approval gate)
- `UsageEvent` — final token/cost tally

**Impact on cost model:**
- Input cost: still estimated pre-call via tiktoken
- Output cost: accrued incrementally mid-stream
- Circuit breaker gains mid-stream abort capability (80% budget warning → terminate early)

**Blocking fallback:** `--no-stream` buffers all events and emits as a single block. Same provider interface.

---

## Approval Gates & Permissions

Every tool call passes through a three-tier approval chain: **Allow** → **Confirm** → **Reject**.

| Tier | Behavior | Example |
|------|----------|---------|
| **Allow** | Auto-execute, no prompt | `file_read`, `search_content` |
| **Confirm** | Show diff/command, ask Y/n | `file_write`, `shell cmd` |
| **Reject** | Block unconditionally | `rm -rf /`, network exfiltration |

**Session overrides:**
- `--auto-approve`: promote all Confirm gates to Allow for the session
- `--read-only`: demote all write/exec gates to Reject
- `--approval-policy=<name>`: load a named policy

**Interactive prompts** show a diff/command preview and accept Y/n/o/a/N responses.
Every decision is logged to the event stream for audit. Config overrides allow per-plugin and per-MCP-tool customization.

---

## Long-Term Memory

Three-layer memory model prevents repeating mistakes across sessions:

| Layer | Scope | Storage | Injected Into System Prompt? |
|-------|-------|---------|------------------------------|
| **Session** | Single conversation | `~/.sponge/sessions/<id>.jsonl` | No (turn history) |
| **Project** | Current project | `<project>/.sponge/memory.toml` | Yes |
| **User** | All projects | `~/.sponge/preferences.toml` | Yes |

**Project memory (`.sponge/memory.toml`)** acts like Claude Code's `CLAUDE.md` or Cursor's `.cursorrules`:

```toml
[rules]
no_touch = "Never modify test/fixtures/ directory"
http_lib = "Use httpx, not requests"
```

Injected into the system prompt at session start. Agent can suggest additions (with confirmation). User can edit directly.

**Conflict resolution:** Project > User > Session override.

---

## Multimodal Input

The `ContentBlock` model supports `text`, `image`, `pdf`, `tool_use`, and `tool_result` types.

```python
@dataclass
class ContentBlock:
    type: Literal["text", "image", "pdf", "tool_use", "tool_result"]
    text: str | None = None
    image_url: str | None = None        # base64 data URI
    pdf_url: str | None = None
    source: FileSource | None = None
```

**CLI usage:** `sponge run "what's wrong?" --image screenshot.png --file spec.pdf`

**Cost:** Images are token-expensive (~800-1600 tokens per 1080p screenshot). The context pipeline gains a "multimodal budget": images are dropped first under compression, replaced with `[image omitted — N tokens saved]`.

**Provider support:** Anthropic (image + PDF), OpenAI (image + PDF), DeepSeek (text only → images routed to sub-agent).

---

## Documentation Index

The complete design documentation lives in `docs/`. Each document covers a specific concern:

| Document | What it covers |
|----------|---------------|
| [architecture.md](docs/architecture.md) | Module map, data flow, key design decisions, anti-patterns |
| [context-pipeline.md](docs/context-pipeline.md) | 5-layer compression pipeline: clear → mask → prune → summarize → slide |
| [cost-model.md](docs/cost-model.md) | Pricing tables, compound savings math, break-even analysis |
| [self-tuning.md](docs/self-tuning.md) | Telemetry collector, pattern analyzer, feedback loop, parameter tuner |
| [mcp-integration.md](docs/mcp-integration.md) | MCP protocol adapter, server lifecycle, tool caching, security |
| [streaming.md](docs/streaming.md) | Two-level streaming pipeline, incremental cost tracking, CLI rendering |
| [security.md](docs/security.md) | Three-tier approval gates, permissions model, session overrides |
| [memory.md](docs/memory.md) | Three-layer memory model, multimodal input (images/PDFs) |
| [risk-assessment.md](docs/risk-assessment.md) | 8 known risks: cold start, feedback drift, provider fallback, etc. |
| [decisions.md](docs/decisions.md) | 10 Architecture Decision Records with context, options, rationale |
| [glossary.md](docs/glossary.md) | A-Z term definitions |
| [cli-reference.md](docs/cli-reference.md) | All commands, subcommands, options |
| [configuration.md](docs/configuration.md) | Full config.toml template + environment variable reference |
| [test-plan.md](docs/test-plan.md) | Three-layer test strategy, mock strategy, benchmark assertions |
| [faq.md](docs/faq.md) | Common questions about usage, cost, privacy |
| [scenarios/](docs/scenarios/) | 5 usage scenarios: Q&A, code review, refactor, bug fix, CI/CD |

---

## Competitive Landscape (Mid-2026)

| Tool | Strengths | Weakness for Sponge to exploit |
|------|-----------|------|
| **Claude Code** | Proven architecture, context awareness, sub-agents, Agent SDK | No built-in cost optimization; users manually choose cheaper models |
| **GitHub Copilot** | HyDRA routing (routes to cheaper models), 3rd-party agent support | Degrades quality for cost; no cache-first architecture |
| **Reasonix** | Cache-first design, 99.8% cache hit rate on DeepSeek, 93.9% cheaper than Claude | DeepSeek-only; quality ceiling lower than Opus |
| **Claude Agent SDK** | Same engine as Claude Code, library form | No built-in cost optimization; Anthropic-only |
| **Cursor** | Excellent UX, codebase indexing | Proprietary; no cost tracking; model switching is manual |
| **OpenHands** | Open-source, Docker sandbox, LangGraph durability | No cost optimization at all |
| **Deep Agents SDK** | Virtual filesystem, pluggable backends, LangGraph runtime | Focused on capabilities, not cost |
| **CrewAI** | Multi-agent orchestration, visual builder | Cost optimization is an afterthought |

Sponge's differentiation: **cost-compression harness with self-tuning** — the only
agent harness that slashes cost through infrastructure
(cache-first, context compression, sub-agent condensation, local preprocessing) AND
automatically optimizes those infrastructure parameters from its own telemetry data.
Competitors either ignore cost, save by using worse models, or require manual tuning.

## Implementation Roadmap (10 Phases)

| Phase | Scope | Deliverable |
|-------|-------|-------------|
| 0 | Project infrastructure | pyproject.toml, dirs, .gitignore, base tools |
| 1 | Core loop + single LLM call | `sponge run "hello"` returns answer + cost |
| 2 | Context pipeline | 5-layer compression, token budget monitoring |
| 3 | Cost visualization + budget | `sponge cost --detailed` incl. savings vs naive, P95 budget, circuit breaker |
| 4 | Result caching | SQLite cache, semantic cache, repeat tasks = $0 |
| 5 | Plugin system | Plugin ABC + Registry, file_ops($0), shell($0) |
| 6 | Sub-agents + sandbox | Dispatch-Condense pattern, Docker/E2B sandbox |
| 7 | Session system | Event stream (Anthropic Managed Agents pattern), multi-turn, save/resume |
| 8 | Multi-provider LLM support | Anthropic, OpenAI, DeepSeek as sub-agent backends |
| 9 | Advanced caching | Prompt cache mgmt (keep-alive, break-even), provider-adaptive strategy |
| 10 | Preprocessor pipeline + benchmarks | Local compression, draft-review, cost-per-task benchmarks vs competitors |
| 11 | **Self-tuning infrastructure** | Telemetry collection, pattern analysis, A/B feedback loop, auto-tuning |

## Development Guidelines

### Cost-First Mindset
- Cost reduction is the harness's core job — every layer must contribute.
- Calculate "savings vs naive" for every optimization — show users what Sponge saved them.
- Aggressive caching (prompt, result, semantic) to minimize billable tokens.
- Log and monitor token usage per operation; surface cost + savings metrics in the UX.
- Every decision feeds telemetry; telemetry feeds optimization; optimization feeds lower costs.

### Tech Stack (defaults)
- Language: Python 3.12+
- Runtime: asyncio for concurrent operations
- LLM SDK: anthropic (for Claude), openai, with provider-agnostic abstraction layer
- CLI framework: typer
- Testing: pytest with asyncio support
- Sandbox: Docker for local dev, E2B for production

### Code Style
- Type hints everywhere.
- Async-first; avoid blocking I/O in hot paths.
- Keep dependencies minimal — every dependency adds attack surface and bloat.
- Prefer stdlib over third-party packages where feasible.

### Architecture
- Provider-agnostic LLM interface with **capability declarations**: provider declares what it supports (server-side clearing, images, PDFs, cache discount rate), pipeline adapts automatically.
- **Streaming by default**: `async for event in llm.stream()` — characters appear in real-time. Output cost accrued incrementally. Circuit breaker gains mid-stream abort capability.
- **MCP-native plugin system**: `MCPServerPlugin` adapter wraps MCP servers as first-class citizens. Built-in plugins (file_ops, shell) bypass MCP for zero overhead.
- **Three-tier approval gates**: Allow (auto-execute) / Confirm (show diff, ask Y/n) / Reject (block). Every tool call passes through the chain. `--auto-approve` and `--read-only` session overrides.
- **Three-layer memory model**: Session (turn history) / Project (`.sponge/memory.toml`) / User (`~/.sponge/preferences.toml`). Project rules injected into system prompt.
- **Multimodal input**: `ContentBlock` supports text, image (base64), and PDF. Images have compression budget — dropped first under pruning.
- Token accounting: track and report cost per run, per task, per session, and savings vs naive.
- Sandboxed execution: run untrusted code in isolated sandboxes (Docker, E2B, or subprocess for dev).
- Plugin system: zero-cost native operations + sub-agents with condensed output.
- Event stream: append-only log for audit, debugging, and crash recovery (Anthropic Managed Agents pattern).
- Context pipeline: 5-layer compression (mask → prune → summarize → slide) runs before every call.
- Telemetry: always-on, local-only collection of every cost decision; feeds self-tuning.
- Anti-self-deception: review/validation plugins must show actual command output, not "looks correct" assertions.

### Testing
- Unit test token/cost accounting logic.
- Integration tests should mock LLM endpoints (don't waste money on test calls).
- Benchmark tests comparing cost-per-task against Claude Code, Copilot, and Cursor.
- "Savings vs naive" assertion in benchmarks: verify that Sponge's infrastructure saves money vs raw API calls.

### Git Conventions
- Commits should be atomic and have descriptive messages in English.
- Branch from main, PR back to main.
- Keep CI fast — slow CI burns money too.
