# Sponge 🧽 — Cost-Learning AI Agent Harness

**Use your chosen model. Spend fewer paid tokens on repeated project work.**

Sponge is an AI agent **harness** (not a framework, not a runtime) that learns how a project spends tokens, then reuses, compresses, caches, and preprocesses context so the configured final reasoning model receives fewer paid tokens over time.

Sponge is not a cheaper-model router. The final reasoning model stays stable unless the user explicitly changes it. Helper executors may be local or cheaper when they only prepare, retrieve, compress, or validate context.

> The name: like a sponge — absorb maximum context efficiently, squeeze out maximum value per token.

---

## Why Sponge?

Many agent tools treat cost as a routing decision or a manual setting. Sponge treats cost as an accounting and infrastructure problem:

| Problem | Typical approach | Sponge's approach |
|---------|-----------------|-------------------|
| **Cost** | Route simpler tasks to cheaper models → quality may change | Reduce paid tokens before the chosen final model is called |
| **Caching** | Stateless; every call is paid in full | Exact, semantic, and prompt-cache strategies with state guards |
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
