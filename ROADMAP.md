# Sponge Roadmap

> **Use your chosen model, spend fewer paid tokens on repeated project work.**
> Each phase delivers a working, testable increment.
>
> The planning source of truth is [docs/project-plan.md](docs/project-plan.md).
> This file is the implementation checklist.

---

## Phase 0 — Development Foundation ✅

**Goal:** Repo is ready for development.

- [x] `pyproject.toml` — project metadata, Python 3.12+, core dependencies
- [x] `.gitignore` — Python standard ignores + `.sponge/` data dir
- [x] `src/sponge/` package skeleton
- [x] `cli/app.py` — typer app skeleton (`sponge --version`)
- [x] `pytest` + `pytest-asyncio` wired up
- [x] Pre-commit hooks (ruff format, ruff check, mypy)
- [x] CI (GitHub Actions — lint + typecheck + test)
- [x] `src/sponge/data/pricing.toml` — provider pricing data file

**Deliverable:** ✅ `pip install -e .` works; `sponge --version` prints `0.1.0-dev`.

---

## Phase 1 — Agent Loop + Cost Fingerprint ✅

**Goal:** Every call produces a cost fingerprint that feeds the optimizer.

- [x] `llm/base.py` — `LLMProvider` ABC with `stream()` method, `StreamEvent` types
- [x] `llm/anthropic_provider.py` — working Claude integration (streaming)
- [x] `llm/openai_provider.py` — OpenAI GPT-4o integration
- [x] `llm/deepseek_provider.py` — DeepSeek V3/R1 integration
- [x] `llm/factory.py` — provider selection from config
- [x] `llm/token_counter.py` — token counting (tiktoken)
- [x] `cost/models.py` — `CostEntry`, `CostSummary`, `ModelPricing`
- [x] `cost/pricing.py` — loader for `src/sponge/data/pricing.toml`
- [x] `cost/tracker.py` — per-call cost accounting (incremental for streaming)
- [x] `cost/ledger.py` — savings ledger: naive baseline vs actual
- [x] `cache/disk_store.py` — SQLite key-value store
- [x] `cache/result_cache.py` — SHA256 exact-match cache with state-aware keys
- [x] `telemetry/collector.py` — cost fingerprint → SQLite on every call
- [x] `telemetry/models.py` — fingerprint schema
- [x] `core/agent.py` — ~30-line async loop with streaming + retry
- [x] `core/task.py` — `Task` / `TaskResult` models
- [x] `cli/run.py` — `sponge run <task>` command
- [x] `cli/config_cmd.py` — `sponge config [show|set]`
- [x] `utils/logging.py` — structured logging (wired in CLI)
- [x] `utils/errors.py` — exception hierarchy
- [x] `utils/retry.py` — exponential backoff for LLM calls
- [x] Benchmark fixtures: 3 JSON fixtures (simple Q&A, repeated Q&A, code question)
- [x] Tests use mock providers; 157 tests, zero real API calls

**Deliverable:** ✅ `sponge run "hello"` streams output + cost report. Cache hits return $0.

---

## Phase 2 — Replay Optimizer MVP ✅

**Goal:** Historical fingerprints feed a replay engine that proposes config changes.

- [x] `telemetry/analyzer.py` — 3 signal detectors:
  - Cache gap detection (TTL too short for request cadence)
  - Budget slack detection (ceiling too high for actual spend)
  - Task repeat detection (extend exact cache TTL)
- [x] `telemetry/tuner.py` — proposal model + Mann-Whitney U evaluation + auto-apply
- [x] `cli/tune_cmd.py` — `sponge tune report|apply|review|history`
- [x] Shadow A/B injection in `sponge run` (deterministic MD5 bucket assignment)

**Deliverable:** ✅ `sponge tune --report` shows ranked tuning proposals with SQL evidence.

---

## Phase 3+ — Commodity Features ✅ (all implemented)

- [x] Context compression (5-layer pipeline: mask → prune → summarize → slide)
- [x] Plugin routing + approval gates (3 built-in plugins + MCP adapter)
- [x] Sub-agent condensation (exploration → structured JSON summary)
- [x] Task decomposition (LLM-driven complex → sub-tasks)
- [x] Progressive context loading (per-subtask planning with deduplication)
- [x] Semantic cache with state guards (Jaccard + SQLite persistence + LRU)
- [x] MCP server integration (JSON-RPC stdio client + Plugin adapter)
- [x] Session system with save/resume (JSONL persistence)
- [x] Multi-turn conversation with history compression
- [x] Long-term project memory (`.sponge/memory.toml` → system prompt)
- [x] Shell sandbox (subprocess timeout, output cap, cwd restriction)
- [x] Cost CLI (`sponge cost session|total|stats` with cache hit rates)
- [x] Provider expansion (Anthropic, OpenAI, DeepSeek)

### Not yet implemented
- [ ] Multimodal input (images, PDFs)
- [ ] 1/10 benchmark (prove target against naive baselines)
- [ ] PyPI publication

---

## Summary

```
Phase 0  ████████  Done — installable, testable, lintable
Phase 1  ████████  Done — agent loop + cost fingerprint + savings ledger
Phase 2  ████████  Done — replay optimizer MVP (the moat)
Phase 3+ ████████  Done — all commodity features implemented
           ░░      Two items remaining: multimodal + 1/10 benchmark
```

> **Current status:** 157 tests, 66 source files, 8 CLI commands. Feature-complete.
