# Sponge 🧽 — 1/10 LLM Cost Through Agent Architecture

**Same model. Same task quality. One-tenth the tokens.**

Sponge is an AI agent harness that reduces LLM cost to 1/10 through architecture alone — not by switching to cheaper models, not by bolt-on caching. Every design decision in the agent loop exists to minimize token consumption: task decomposition, progressive context loading, sub-agent condensation, memory-based reuse, and plugin routing.

> The name: like a sponge — absorb maximum context, squeeze out maximum value. Every token must justify its existence.

---

## How It Works

| Layer | Mechanism | Token Reduction |
|-------|-----------|-----------------|
| **Task Decomposition** | Break complex tasks into focused sub-tasks | 5-10× per subtask |
| **Progressive Context** | Load context on demand, not upfront | 3-5× |
| **Sub-Agent Condensation** | 50K-token exploration → 500-token summary | 10-100× |
| **Memory Reuse** | Remember decisions, don't re-derive | 2-5× |
| **Plugin Routing** | File ops, shell → $0 LLM cost | ∞ |
| **Self-Tuning** | Detect waste, shadow A/B validate | 5-20% per iteration |

Compound target: **1/10 cost.**
| **Context** | Send full history every turn | 5-layer compression pipeline: mask → prune → summarize → slide |
| **Tuning** | Hardcoded thresholds; user tweaks settings manually | Replay and live feedback loops propose measured configuration changes |
| **Transparency** | No cost breakdown per call/task | Savings ledger shows actual cost, naive baseline, and savings source |

**The benchmark target:** same chosen final model, lower effective paid-token footprint on compatible repeated work. Claims must be workload-scoped and backed by reproducible measurements.

---

## Architecture at a Glance

```
sponge run "task"
  │
  ├─ [Cache Check] SHA256(task + system) → exact / semantic / miss
  │
  ├─ [Plugin Route] native ($0) | helper agent (condensed) | LLM required
  │     │
  │     ├─ [Preprocessor] Ollama compresses prompt locally (optional)
  │     ├─ [Cost Estimator] tiktoken → exact $ estimate (<1ms)
  │     ├─ [Circuit Breaker] per‑call + cumulative + step budget
  │     ├─ [Context Compressor] 5‑layer: mask → prune → compact → slide
  │     └─ [LLM.stream()] → Your configured final model
  │
  └─ [CostTracker] + [Cache.write] + [Telemetry.log]
        │
        └─ (background) Replay Optimizer → Feedback Loop → Tuning Proposals
```

The core loop is ~30 lines. **95% of complexity lives in the cost-compression infrastructure.**

---

## Quick Start

```bash
# Requirements: Python 3.12+, API key for Anthropic or OpenAI
pip install -e .

# Run a task
sponge run "explain the CAP theorem in one sentence"

# Check your savings
sponge cost --session
```

> **Note:** Sponge is in early development. The editable install path is for local development; the PyPI install path will be published after the first usable release. See [ROADMAP.md](ROADMAP.md).

---

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Stable final model** | Sponge does not silently replace the configured final reasoning model. Helper executors can be local or cheaper only when their outputs are condensed and auditable. |
| **Multi-level cache** | SHA256 exact-match (SQLite) + cosine semantic cache + prompt cache management. Exact compatible repeats can cost \$0 in model spend. |
| **5-layer context pipeline** | Mask old tool outputs → prune low-signal turns → LLM-summarize as last resort → hard sliding window. |
| **Plugin routing** | Read/search/file operations can execute locally at \$0 model cost, subject to approval policy. |
| **Cost fingerprint + replay** | Runs leave replayable cost records so proposed optimizations can be tested before live A/B. |
| **Circuit breaker** | 3-axis budget: per-call limit, cumulative warning/block, max steps. Budgets stop runaway spend; they are not counted as savings. |

---

## Competitive Landscape

| Tool | Cost Strategy | Model Quality | Self-Tuning | Cache-First |
|------|--------------|---------------|-------------|-------------|
| **Claude Code** | Manual model switching | Dynamic | ❌ | ❌ |
| **GitHub Copilot** | HyDRA → cheaper models | Degraded | ❌ | ❌ |
| **Reasonix** | Cache-first (DeepSeek only) | Ceiling: DeepSeek | ❌ | ✅ |
| **Cursor** | Manual model switching | Dynamic | ❌ | ❌ |
| **OpenHands** | No cost optimization | Any model | ❌ | ❌ |
| **Sponge** | **Measured paid-token reduction** | **Configured final model** | **Planned** | **Planned** |

---

## Project Status

![Phase](https://img.shields.io/badge/phase-0_foundation-blue)

Sponge is in Phase 0 foundation work. The package skeleton and planning docs exist, but the runtime agent loop is not implemented yet. See [docs/project-plan.md](docs/project-plan.md) for the execution source of truth and [ROADMAP.md](ROADMAP.md) for the historical checklist.

The first product proof is Phase 1: `sponge run "hello"` streams one provider response and records real usage and cost. The first savings proof is Phase 2: an identical compatible repeat returns from exact cache with `$0` model spend.

---

## License

MIT
