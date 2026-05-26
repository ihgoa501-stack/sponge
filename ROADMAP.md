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

## Phase 1 — Agent Loop + Cost Fingerprint

**Goal:** Every call produces a cost fingerprint that feeds the optimizer.
Merges old Phase 1 (agent loop), Phase 2 (exact cache + ledger), and Phase 5 (fingerprints).

- [ ] `llm/base.py` — `LLMProvider` ABC with `stream()` method, `StreamEvent` types
- [ ] `llm/anthropic_provider.py` — working Claude integration (streaming)
- [ ] `llm/factory.py` — provider selection from config
- [ ] `llm/token_counter.py` — token counting (tiktoken)
- [ ] `cost/models.py` — `CostEntry`, `CostSummary`, `ModelPricing`
- [ ] `cost/pricing.py` — loader for `src/sponge/data/pricing.toml`
- [ ] `cost/tracker.py` — per-call cost accounting (incremental for streaming)
- [ ] `cost/ledger.py` — savings ledger: naive baseline vs actual, split by source
- [ ] `cost/reporter.py` — cost report output (text + JSON)
- [ ] `cache/disk_store.py` — SQLite key-value store
- [ ] `cache/result_cache.py` — SHA256 exact-match cache with state-aware keys
- [ ] `telemetry/collector.py` — cost fingerprint → SQLite on every call
- [ ] `telemetry/models.py` — fingerprint schema
- [ ] `core/agent.py` — ~30-line async loop with streaming
- [ ] `core/task.py` — `Task` / `TaskResult` models
- [ ] `cli/run.py` — `sponge run <task>` command
- [ ] `cli/config_cmd.py` — `sponge config [show|set]`
- [ ] `utils/logging.py` — structured logging
- [ ] `utils/errors.py` — exception hierarchy
- [ ] Benchmark fixtures: 3+ JSON fixtures (simple Q&A, repeated Q&A, code question)
- [ ] Tests use mock providers; real provider tests opt-in via `--run-slow`

**Deliverable:** `sponge run "hello"` streams output + `Cost: $0.0123 (saved $0.0000)`.
Repeating the same task returns from exact cache: `Cost: $0.0000 (saved $0.0123)`.

---

## Phase 2 — Replay Optimizer MVP

**Goal:** Historical fingerprints feed a replay engine that proposes config changes.
This is Sponge's moat — no other harness does it.

- [ ] `telemetry/analyzer.py` — SQL pattern queries over fingerprint store
  - Cache gap detection (TTL too short for request cadence)
  - Budget slack detection (ceiling too high for actual spend)
  - Task repeat detection (extend exact cache TTL)
- [ ] `telemetry/replay.py` — replay engine: simulate candidate params over stored fingerprints (no LLM calls)
- [ ] `telemetry/tuner.py` — proposal model + auto-apply low-risk changes
- [ ] `cli/tune_cmd.py` — `sponge tune --report` and `sponge tune --apply`
- [ ] Fixture fingerprints: 10+ pre-recorded fingerprints that exercise all signal types
- [ ] Tests verify: at least 1 non-trivial proposal from fixture data

**Deliverable:** After ≥10 sessions, `sponge tune --report` shows ranked tuning proposals
with estimated savings, risk level, and SQL evidence.

---

## Phase 3+ — Commodity Features

Added one at a time, each measured by whether it improves replay optimizer proposals.
No fixed order. No separate phase plan until prioritized.

- [ ] Context compression (5-layer pipeline)
- [ ] Plugin routing + approval gates (file ops, shell, search)
- [ ] Sub-agent condensation (codebase exploration)
- [ ] Semantic cache with state guards
- [ ] Multimodal input (images, PDFs)
- [ ] MCP server integration
- [ ] Session resume and multi-turn persistence
- [ ] Provider expansion (OpenAI, DeepSeek)
- [ ] Long-term memory (project + user preferences)

---

## Summary

```
Phase 0  ████████  Done — installable, testable, lintable
Phase 1  ░░░░░░░░  Agent loop + cost fingerprint + savings ledger
Phase 2  ░░░░░░░░  Replay optimizer MVP (the moat)
Phase 3+ ░░░░░░░░  Commodity features, one at a time
```

> **Current status:** Phase 0 ✅. Phase 1 implementation plan next.
> See [docs/project-plan.md](docs/project-plan.md) for rationale behind the restructured roadmap.
