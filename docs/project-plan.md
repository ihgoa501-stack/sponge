# Sponge Project Plan

> **Planner role:** This document is the source of truth for project planning. Runtime code should be implemented by worker agents from the task packages below. The planner owns scope, sequencing, acceptance criteria, risk controls, and documentation consistency.

## Planner Mandate

My task is to turn Sponge from a strong idea into an executable project plan:

- Define the product thesis and keep it sharp: same chosen main model, lower paid-token footprint over time.
- Break the project into independently shippable phases.
- Give worker agents clear task packages with files, constraints, tests, and acceptance criteria.
- Keep the planning docs honest: no unsupported pricing, no vague savings claims, no hidden quality trade-offs.
- Enforce [claims.md](claims.md) and [pricing-policy.md](pricing-policy.md) whenever README, roadmap, benchmark, or pricing docs change.
- Move the "uses get cheaper over time" proof as early as possible.
- Do not write runtime implementation code in planner work.

## Product Thesis

Sponge is a cost-learning agent harness. It does not primarily save money by routing the final answer to a cheaper model. It saves money by learning how each project spends tokens, then reusing, compressing, caching, and pre-processing context so the same chosen main model receives fewer paid tokens over time.

Positioning statement:

> Sponge is not a cheaper-model router. It is a cost-learning harness: every run leaves behind a reusable cost fingerprint, so future runs spend fewer paid tokens for the same model-quality outcome.

The strict wording is:

> Sponge keeps the final reasoning model stable unless the user explicitly changes it. Helper executors may be cheaper or local, but they only prepare, retrieve, compress, or validate context. They do not silently replace the configured main model for final reasoning.

This resolves the design tension between "never downgrade" and using local preprocessors or cheaper sub-agents.

## Core Innovation

The current docs already contain the right ingredients: cost tracking, caches, compression, plugin routing, telemetry, and self-tuning. The innovation should be framed as a closed-loop system:

1. **Cost Fingerprint**
   Each run records why it cost money: task class, model, repo state, context size, compression choices, cache state, tool calls, provider capabilities, and final usage.

2. **Savings Ledger**
   Each run reports actual cost against a naive baseline, split by savings source: exact cache, semantic cache, prompt cache, compression, plugins, sub-agent condensation, and preprocessing.

3. **Replay-Based Optimizer**
   Before live A/B tests, Sponge replays historical cost fingerprints through candidate configurations. Only changes that reduce simulated cost without violating safety constraints enter live shadow testing.

4. **Live Feedback Loop**
   Shadow sessions validate promising changes with real usage. Tuning applies only when savings beat testing cost and do not increase known risk signals.

This is stronger than "auto-tune thresholds" because it creates an audit trail and a repeatable optimization lab.

## Critical Self-Assessment (2026-05-24)

The original 12-phase waterfall had fundamental flaws identified during review:

1. **The core value proposition was deferred to Phase 9.** "越用越省钱" required replay optimizer + live self-tuning, both at the end. Before Phase 9, Sponge would be the *most expensive* option because "no silent downgrade" forces every call through the configured premium model with none of the savings infrastructure active.

2. **Phases 3-8 were chasing features competitors already have.** Context compression, semantic cache, sub-agents, multimodal — Claude Code, Cursor, and Copilot already do these. Sponge matching them is not differentiation; it's catch-up. Only cost fingerprint replay is unique.

3. **12-phase waterfall = no pivot point.** If Phase 4 revealed no user interest, Phases 0-3 are sunk cost. No intermediate milestone proves the core hypothesis.

4. **Documentation outpaced code by infinity.** 25+ docs, 10 ADRs, 5 scenarios — all describing a product that cannot run a single agent task. This is analysis paralysis.

### The Fix: Fingerprint-First

Sponge's only moat is the **cost fingerprint → replay → tune** closed loop. Everything else is commodity.

The revised strategy: **prove the unique thing first, then add commodity features.**

| What was cut | Why |
|-------------|-----|
| Phase 3: Context Compression | Useful but not unique. Add after replay is proven. |
| Phase 4: Plugin Routing + Approval | Useful but not unique. Add after replay is proven. |
| Phase 6: Prompt Cache Strategy | Provider-specific. Can fold into Phase 1 cost tracking. |
| Phase 7: Semantic Cache | Premature without real usage data to tune similarity thresholds. |
| Phase 8: Sub-Agent Condensation | No sub-agents until the main agent loop works. |
| Phase 10: Live Self-Tuning | Folded into Phase 2 (replay optimizer already includes gated application). |
| Phase 11: Multimodal | Nice-to-have. Not core. |
| Phase 12: Benchmarks | Benchmarks start in Phase 1 as unit-test fixtures. No separate phase needed. |

## Coding Capability

- After Phase 1, Sponge can answer coding questions through a single model call with cost tracking and fingerprint recording.
- After Phase 2, Sponge can replay historical fingerprints to recommend cost-saving config changes.
- After Phase 3+, Sponge can edit code, route plugins, compress context, and spawn sub-agents — each added only after the core fingerprint loop is proven.

## Planning Corrections

These corrections should guide all future docs and implementation plans:

- **Pricing must be data-driven.** Pricing tables in docs are examples unless generated from a versioned pricing file. Worker agents must not hardcode outdated provider prices into docs or tests.
- **Cache hit targets must be workload-specific.** "80%+ cache hit rate" is plausible for repeated Q&A and stable project instructions, not for every coding task.
- **Semantic cache keys must include state.** A semantic cache answer is valid only under compatible repository state, model version, tool version, and relevant file hashes.
- **Budget ceilings are risk controls, not savings engines.** Lowering a budget may prevent runaway spend, but it does not make an identical successful task cheaper.
- **Compression changes must track quality risk.** Compression ratio alone is not enough. Plans must include at least fixture-based semantic preservation tests and rollback paths.
- **Savings reports must include latency and risk.** A cheaper path is not automatically better if it adds too much delay, stale context risk, or user rework.
- **Prompt caching must be provider-adaptive.** Cache write/read multipliers and TTL semantics differ by provider and can change.
- **Small live A/B tests are not enough.** Use replay first, then live shadow. Twenty sessions with four shadow samples is weak evidence by itself.
- **"No downgrade" applies to final reasoning.** Helper agents can be cheap/local when their outputs are condensed and auditable.

## Phase Strategy

Three phases to prove the core hypothesis. After Phase 2, Sponge has its moat. Everything else is additive.

| Phase | Name | Primary Proof | Why First |
|-------|------|---------------|-----------|
| 0 | Development Foundation | Package installs, CLI starts, tests run | ✅ Done |
| 1 | Agent Loop + Cost Fingerprint | Streamed LLM call + exact cache + savings ledger + fingerprint recording | The accounting spine. Every call from day one produces data that feeds the optimizer. |
| 2 | Replay Optimizer MVP | Historical fingerprints replayed under candidate configs → tuning proposals with cost delta + risk | The moat. No other harness does this. If this doesn't work, nothing else matters. |
| 3+ | Commodity Features | Context compression, plugin routing, approval gates, sub-agents, multimodal | Added one at a time, each measured by whether it improves the replay optimizer's savings proposals. |

## Phase Acceptance Criteria

### Phase 0: Development Foundation ✅

Done. `sponge --version` works. pytest/ruff/mypy pass. CI is configured.

### Phase 1: Agent Loop + Cost Fingerprint

Done when:

- `sponge run "say hello"` streams output from one configured provider.
- Actual usage is recorded from provider response events.
- Exact result cache (SHA256) returns cached responses for identical tasks without a model call.
- Every call writes a **cost fingerprint** to local SQLite: task hash, model, tokens in/out, cache hit/miss, cost, repo state marker, provider capabilities.
- Output includes a **savings ledger**: naive baseline cost vs actual cost, split by source (exact cache, prompt cache).
- Pricing data is read from `src/sponge/data/pricing.toml` — never hardcoded.
- Tests use mock providers; real provider tests are opt-in via `--run-slow`.
- At least 3 benchmark fixtures (simple Q&A, repeated Q&A, code question) pass and report token counts.

Worker agents:

- LLM agent: provider ABC, streaming event types, one provider (Anthropic).
- Cost agent: pricing loader, cost tracker, savings ledger.
- Cache agent: SQLite exact result cache with state-aware keys.
- Telemetry agent: cost fingerprint schema and SQLite persistence.
- CLI agent: `run` command, streaming renderer, cost report, JSON mode.

### Phase 2: Replay Optimizer MVP

Done when:

- `sponge tune --report` reads historical fingerprints from SQLite.
- The replay engine simulates candidate parameter values over stored fingerprints **without calling real LLM APIs**.
- The pattern analyzer detects at minimum: cache gap (TTL too short), budget slack (ceiling too high), and task repeats (cache TTL extension).
- Each tuning proposal includes: parameter, current value, proposed value, estimated cost delta, risk level, and SQL query evidence.
- Proposals are ranked by estimated savings ÷ risk.
- Low-risk proposals (estimated < $0.50/session impact) can auto-apply with `sponge tune --apply`.
- At least 10 fixture fingerprints produce at least 1 non-trivial tuning proposal.

Worker agents:

- Telemetry agent: fingerprint query helpers.
- Optimizer agent: replay engine, pattern analyzer (SQL queries), proposal model.
- CLI agent: `sponge tune --report` and `sponge tune --apply`.

### Phase 3+: Commodity Features

Each feature is added only when:

1. A concrete use case shows it would improve replay optimizer proposals.
2. It can be measured against the benchmark fixtures from Phase 1.

Candidate features, in no fixed order:

- Context compression (5-layer pipeline)
- Plugin routing + approval gates (file ops, shell, search)
- Sub-agent condensation (codebase exploration)
- Semantic cache with state guards
- Multimodal input (images, PDFs)
- MCP server integration
- Session resume and multi-turn persistence
- Provider expansion (OpenAI, DeepSeek)

No separate phase plan exists for these. Each is a standalone mini-project with its own plan file when prioritized.

## Agent Handoff Protocol

Every worker-agent task should include:

- Goal: one sentence.
- Scope: files allowed to create/modify.
- Inputs: docs and prior artifacts to read.
- Tests: exact commands and expected results.
- Acceptance: observable behavior, not intent.
- Non-goals: what must not be changed.
- Commit boundary: one coherent commit per task.

Planner review after each task should check:

- Does this preserve the main-model-stability promise?
- Does it record cost data needed by later phases?
- Does it avoid real LLM calls in normal tests?
- Does it update docs if user-visible behavior changed?
- Does it avoid stale cache or unsafe tool execution paths?

## Immediate Next Planning Work

1. `docs/superpowers/plans/2026-05-24-phase-1-cost-fingerprint.md` — detailed implementation plan for Phase 1.
2. `docs/superpowers/plans/2026-05-24-phase-2-replay-optimizer.md` — after Phase 1 is complete.
3. Keep [claims.md](claims.md) and [pricing-policy.md](pricing-policy.md) current.

Do not create plans for Phase 3+ features until Phase 2 proves the fingerprint→replay→tune loop works.
