# Sponge Roadmap

> **Use your chosen model, spend fewer paid tokens on repeated project work.** Each phase delivers a working, testable increment.
> Phases are ordered by dependency — later phases build on earlier infrastructure.

This roadmap is the historical delivery checklist. The planning source of truth
is [docs/project-plan.md](docs/project-plan.md), which defines the planner role,
revised phase strategy, innovation model, acceptance criteria, and worker-agent
handoff protocol. Use the phase order in `docs/project-plan.md` for execution
sequencing and use the checklist below only as implementation inventory until it
is fully renumbered.

## Planning Update — Cost Proof Moves Earlier

The original roadmap placed self-tuning near the end. That is still where the
full closed loop lands, but the proof of lower repeated-work paid-token spend
must start earlier:

1. Phase 1 establishes real usage and cost accounting.
2. Phase 2 adds the savings ledger and exact result cache, so repeat tasks show
   zero model spend immediately.
3. Phase 5 records replayable cost fingerprints.
4. Phase 9 adds replay-based optimization before live A/B tests.
5. The full live self-tuning loop remains later-stage work, after replay-based
   optimization proves that candidate changes are worth testing.

This keeps the MVP aligned with the product promise without claiming that every
individual task or session will be cheaper.

---

## Phase 0 — Project Infrastructure

**Goal:** Repo is ready for development. No runtime code yet.

- [ ] `pyproject.toml` — project metadata, Python 3.12+, core dependencies
- [ ] `.gitignore` — Python standard ignores + `~/.sponge/` data dir
- [ ] `src/sponge/` package skeleton with `__init__.py` / `__main__.py`
- [ ] `cli/app.py` — typer app skeleton (`sponge --version`)
- [ ] `pytest` + `pytest-asyncio` wired up
- [ ] Pre-commit hooks (ruff format, ruff check, mypy)
- [ ] Initial CI (GitHub Actions — lint + typecheck + test)

**Deliverable:** `pip install -e .` works; `sponge --version` prints `0.1.0-dev`.

---

## Phase 1 — Core Loop + Single LLM Call

**Goal:** `sponge run "hello"` returns an answer with a cost breakdown. Streaming by default.

- [ ] `core/agent.py` — ~30-line async loop with streaming (`async for event in llm.stream()`)
- [ ] `llm/base.py` — `LLMProvider` ABC with `stream()` method, `StreamEvent` types (`ContentDelta`, `ToolCallEvent`, `UsageEvent`)
- [ ] `llm/anthropic_provider.py` — working Claude integration (streaming)
- [ ] `cli/run.py` — `sponge run <task>` command with `--stream` / `--no-stream` flags
- [ ] CLI rendering: incremental text output + inline tool call display
- [ ] `cost/tracker.py` — per-call cost accounting (incremental for streaming)
- [ ] `cost/models.py` — `CostEntry`, `CostSummary`, `ModelPricing`
- [ ] `cost/reporter.py` — simple cost report output
- [ ] `utils/logging.py` — structured logging
- [ ] `utils/errors.py` — exception hierarchy

**Deliverable:** `sponge run "say hello"` streams response characters as they're generated + `Cost: $0.0123`.

---

## Phase 2 — Context Pipeline

**Goal:** Token consumption drops on fixture-backed multi-turn tasks without losing answer-critical information.

- [ ] `core/context.py` — 5-layer compression pipeline
  - Layer 1: Server-side tool result clearing (Anthropic beta headers)
  - Layer 2: Observation masking — replace old tool outputs with `[...N tokens omitted...]`
  - Layer 3: Message pruning — importance scoring, keep min 5 turns
  - Layer 4: LLM summarization — external cheap model for history compaction
  - Layer 5: Sliding window — hard context limit
- [ ] `core/task.py` — `Task` / `TaskResult` models (needed to track turns)
- [ ] Token budget monitoring — warn before 90% context window
- [ ] Integration test: verify compression ratio improves on realistic conversations
- [ ] Preservation test: verify answer-critical facts remain available after compression

**Deliverable:** Multi-turn fixture conversations use measurably fewer tokens per turn while preserving required facts. `--verbose` shows compression stats per call.

---

## Phase 3 — Cost Visualization + Budget Enforcement

**Goal:** Users see exactly where money goes; budgets prevent runaway costs.

- [ ] `cli/cost_cmd.py` — `sponge cost [--task|--session|--export]`
- [ ] `cost/budget.py` — 3-axis circuit breaker (per-call, cumulative %, max steps)
- [ ] `cost/cost_estimator.py` — pre-call tiktoken-based cost prediction
- [ ] `cost/reporter.py` — rich formatted reports with savings-vs-naive column
- [ ] Savings vs naive baseline calculation

**Deliverable:** `sponge cost --session` shows total spend, savings vs naive, budget utilization %. Circuit breaker stops runaway sessions.

---

## Phase 4 — Result Caching

**Goal:** Compatible repeat tasks can avoid model calls through exact cache; semantic cache is state-guarded and opt-in until proven safe.

- [ ] `cache/base.py` — `Cache` ABC
- [ ] `cache/disk_store.py` — SQLite key-value store
- [ ] `cache/result_cache.py` — SHA256 exact-match cache
- [ ] `cache/semantic_cache.py` — cosine similarity (embedding) cache
- [ ] Integration: cache checked before LLM call, written after
- [ ] TTL management, cache invalidation, size limits

**Deliverable:** Run the same compatible task twice — the second call returns from exact cache with model spend `$0.00`.

---

## Phase 5 — Plugin System + MCP + Approval Gates

**Goal:** File operations and shell commands execute locally at \$0 LLM cost. MCP servers are first-class citizens. Every tool call goes through an approval chain.

- [ ] `plugins/base.py` — `Plugin` ABC, `PluginContext`, `PluginResult`
- [ ] `plugins/registry.py` — `PluginRegistry` with `best_match()` routing
- [ ] `plugins/builtins/file_ops.py` — read/write/list files (zero LLM cost)
- [ ] `plugins/builtins/shell.py` — execute shell commands (zero LLM cost)
- [ ] Plugin integration into agent loop — bypass LLM for plugin-routable tasks
- [ ] Plugin metrics: zero_cost flag, latency tracking
- [ ] `plugins/mcp_server.py` — `MCPServerPlugin` adapter: spawn → handshake → tool cache → call → shutdown
- [ ] MCP server config in TOML: command, args, env, transport (stdio/SSE), per-server approval overrides
- [ ] MCP server lifecycle: graceful start, crash recovery (max 3 restarts), graceful shutdown
- [ ] Tool schema caching from MCP `listTools` response
- [ ] `approval/base.py` — `ApprovalPolicy` ABC, `ApprovalChain` (allow → confirm → reject)
- [ ] `approval/policies.py` — built-in policies (read-only, diff-review, deploy-staging)
- [ ] `approval/session_overrides.py` — `--auto-approve`, `--read-only`
- [ ] Approval chain integration: every tool call (native + MCP) goes through chain
- [ ] Interactive CLI prompt for "Confirm" tier: diff/command display, Y/n/o/a/N responses
- [ ] Approval event logging to event stream

**Deliverable:** `sponge run "list files"` executes via plugin, \$0 LLM cost. `sponge run "delete /etc"` prompts for confirmation. MCP servers (filesystem, github, puppeteer) work via config.

---

## Phase 6 — Sub-Agents + Sandbox

**Goal:** Complex tasks dispatch to isolated sub-agents; only condensed results reach the main model.

- [ ] `plugins/builtins/search.py` — code search via sub-agent, condensed output
- [ ] `plugins/builtins/review.py` — code review via sub-agent, condensed output
- [ ] `plugins/sub_agent.py` — generic sub-agent dispatch with result condensation
- [ ] `sandbox/base.py` — `Sandbox` ABC
- [ ] `sandbox/subprocess_sandbox.py` — local subprocess (dev only)
- [ ] `sandbox/docker_sandbox.py` — Docker container sandbox
- [ ] `sandbox/e2b_sandbox.py` — E2B sandbox-as-a-service

**Deliverable:** `sponge run "find all TODO comments"` spawns a sub-agent, returns condensed result. Sandboxed execution available.

---

## Phase 7 — Session System + Memory

**Goal:** Multi-turn conversations with save/resume, crash recovery. Long-term memory prevents repeating mistakes across sessions.

- [ ] `core/session.py` — session lifecycle, persistence to `~/.sponge/sessions/`
- [ ] `core/event_stream.py` — append-only event log (Anthropic Managed Agents pattern)
- [ ] `cli/session.py` — `sponge session [start|resume|list]` commands
- [ ] Crash recovery — replay event stream to restore state
- [ ] Session cost aggregation
- [ ] `memory/base.py` — `MemoryStore` ABC
- [ ] `memory/project_memory.py` — `<project>/.sponge/memory.toml` read/write
- [ ] `memory/injector.py` — inject project memory + user preferences into system prompt
- [ ] Agent-initiated memory writes (with user confirmation)
- [ ] `memory/user_preferences.py` — `~/.sponge/preferences.toml` (cross-project defaults)
- [ ] Conflict resolution: project > user > session override

**Deliverable:** `sponge run "refactor this"` → Ctrl+C → `sponge session resume` picks up. "Never touch test/fixtures/" in `.sponge/memory.toml` is respected across sessions.

---

## Phase 8 — Multi-Provider LLM Support + Multimodal

**Goal:** Use Anthropic, OpenAI, or DeepSeek as the user's configured model or as sub-agent backend. Support images and PDFs as input.

- [ ] `llm/openai_provider.py` — OpenAI provider (GPT-5.5, GPT-4.7) with streaming
- [ ] `llm/deepseek_provider.py` — DeepSeek provider (OpenAI-compatible)
- [ ] `llm/factory.py` — `ProviderFactory` for provider selection
- [ ] `cli/config_cmd.py` — `sponge config set model=openai/gpt-5.5`
- [ ] Provider-specific token counting and pricing tables
- [ ] Sub-agent can use different (cheaper) provider than the main agent
- [ ] Cross-provider prompt cache adaptation
- [ ] `llm/base.py` — `ContentBlock` model extended: `image`, `pdf` types
- [ ] Anthropic provider: image (base64) + PDF support
- [ ] OpenAI provider: image (URL/base64) + PDF (file parameter) support
- [ ] CLI: `--image`, `--file` flags for passing multimodal input
- [ ] Multimodal compression rules in context pipeline (image budget, drop order)
- [ ] SHA256 content-addressed caching for image/PDF inputs

**Deliverable:** `sponge config set model=openai/gpt-5.5` switches the main model; sub-agents default to DeepSeek V4-Flash. `sponge run "what's wrong?" --image bug.png` includes the screenshot in context.

---

## Phase 9 — Advanced Caching

**Goal:** Prompt cache management with keep-alive, break-even analysis, cross-provider adaptation.

- [ ] `cache/prompt_cache.py` — prompt cache retention management
- [ ] Keep-alive strategy: refresh cache before TTL expiry if session is active
- [ ] Break-even analysis: cache write cost vs projected read savings
- [ ] Provider-adaptive strategy (Anthropic vs OpenAI vs DeepSeek cache semantics differ)
- [ ] Cache statistics dashboard: hit rate, savings, TTL efficiency

**Deliverable:** Prompt cache decisions are visible in the savings ledger, and workload-specific hit-rate reports distinguish repeated stable-prefix work from general coding tasks.

---

## Phase 10 — Preprocessor Pipeline + Benchmarks

**Goal:** Local preprocessing compresses prompts before cloud calls; benchmarks prove savings.

- [ ] `plugins/preprocessor.py` — local preprocessing pipeline
- [ ] Ollama integration for prompt compression
- [ ] Draft-scaffolding: local model drafts → main model polishes
- [ ] Fail-open: if local model unavailable, pass through untouched
- [ ] Benchmark suite:
  - Cost-per-task vs Claude Code, Copilot, Cursor, Reasonix
  - Compression ratio measurements per layer
  - Savings-vs-naive assertion in CI

**Deliverable:** `sponge run --benchmark` compares Sponge against naive same-model baselines. Public competitor comparisons require published methodology and current pricing data.

---

## Phase 11 — Self-Tuning Infrastructure

**Goal:** The harness watches its own cost data and proposes optimizations that replay evidence supports before live testing.

- [ ] `telemetry/collector.py` — per-call metrics → SQLite
- [ ] `telemetry/models.py` — `TelemetryEntry`, `UsagePattern`, `TuningResult`
- [ ] `telemetry/analyzer.py` — SQL pattern queries (request cadence, compression ratio, budget slack, task repeats)
- [ ] `telemetry/feedback.py` — shadow A/B testing, Mann-Whitney U evaluation
- [ ] `telemetry/tuner.py` — auto-apply winning config changes
- [ ] `cli/tune_cmd.py` — `sponge tune --report` savings dashboard
- [ ] Self-tuning closed loop: collect → replay → analyze → validate → apply → repeat
- [ ] Quality-risk signals: rollback, repeated user correction, fixture preservation, and failed-task markers

**Deliverable:** After enough compatible cost fingerprints, `sponge tune --report` shows proposed and applied changes with measured cost delta, latency delta, risk level, and rollback path.

---

## Summary

```
Phase 0  ████████░░░░░░░░░░  Project infra
Phase 1  ████████░░░░░░░░░░  Core loop + streaming
Phase 2  ░░░░░░░░░░░░░░░░░░  Context pipeline
Phase 3  ░░░░░░░░░░░░░░░░░░  Cost viz + budget
Phase 4  ░░░░░░░░░░░░░░░░░░  Result caching
Phase 5  ░░░░░░░░░░░░░░░░░░  Plugin system + MCP + approval gates
Phase 6  ░░░░░░░░░░░░░░░░░░  Sub-agents + sandbox
Phase 7  ░░░░░░░░░░░░░░░░░░  Session system + memory
Phase 8  ░░░░░░░░░░░░░░░░░░  Multi-provider + multimodal
Phase 9  ░░░░░░░░░░░░░░░░░░  Advanced caching
Phase 10 ░░░░░░░░░░░░░░░░░░  Preprocessor + benchmarks
Phase 11 ░░░░░░░░░░░░░░░░░░  Self-tuning infrastructure
```

> **Current status:** Phase 0 foundation. The package skeleton and planning docs exist, but the runtime agent loop is not implemented yet. Use [docs/project-plan.md](docs/project-plan.md) as the execution source of truth.
