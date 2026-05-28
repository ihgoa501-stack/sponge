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

Sponge reduces LLM cost to **1/10** through agent architecture alone. Same model, same task quality, one-tenth the tokens.

This is not achieved by bolt-on cache layers or model routing. It is achieved by fundamental architectural decisions: task decomposition, progressive context loading, sub-agent condensation, memory-based reuse, and plugin routing. Every token sent to the model must justify its existence.

Positioning statement:

> Sponge is not a cheaper-model router. It is an architecture-level cost compressor: the agent loop is designed from first principles to minimize token consumption, targeting 1/10 the cost of a naive harness for the same task quality.

## Core Innovation — Architecture as Cost Reduction

The target is **1/10 tokens for the same task quality.** Each architectural layer independently reduces token consumption:

1. **Task Decomposition** — break complex work into focused sub-tasks, each with minimal context.
2. **Progressive Context Loading** — load context on demand, not upfront.
3. **Sub-Agent Condensation** — exploration returns condensed evidence, not raw transcripts.
4. **Memory-Based Reuse** — remember decisions across sessions; don't re-derive.
5. **Cost Fingerprint + Replay** — measure every architectural change against real workload data.
6. **Plugin Routing** — tasks not needing LLM reasoning bypass the model entirely ($0).

7. **Reflexion** — every failure triggers structured self-evaluation. Lessons are extracted and stored in reflective memory, then retrieved when similar tasks appear. The same mistake is never paid for twice. This is the meta-layer: it doesn't save tokens on THIS call — it prevents wasted tokens on ALL FUTURE calls. **越用越省钱** (cheaper over time) through accumulated wisdom, not just caching.

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

Each phase adds an architectural layer that independently reduces token consumption toward the 1/10 target.

| Phase | Layer | What It Saves |
|-------|-------|---------------|
| 0 | Foundation | ✅ Done |
| 1 | Cost Accounting | Fingerprints + ledger — measure every token |
| 2 | Self-Tuning | Auto-detect waste, shadow A/B validate fixes |
| 3 | Task Decomposition | Break complex tasks → small focused sub-tasks |
| 4 | Sub-Agent Condensation | 50K-token exploration → 500-token summary |
| 5 | Progressive Context | Load context on demand, not upfront |
| 6 | Memory Reuse | Remember decisions, don't re-derive |
| 7 | **Reflexion** | Learn from every failure — structured self-evaluation, lesson extraction, reflective memory retrieval |
| 8 | 1/10 Benchmark | Prove the target against naive baselines |

## Phase Acceptance Criteria

### Phase 0: Development Foundation ✅

Done. `sponge --version` works. pytest/ruff/mypy pass. CI is configured.

### Phase 1: Agent Loop + Cost Fingerprint ✅

Done. All acceptance criteria met:

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

### Phase 2: Replay Optimizer MVP ✅

Done. All acceptance criteria met:

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

### Phase 7: Reflexion — Structured Self-Evaluation + Lesson Memory

> 照镜子 → 刻字 → 读柱子 — *mirror → carve → read*

The agent learns from every failure through structured verbal self-critique. Each failed attempt triggers a reflection call that analyzes the trajectory, extracts a compact lesson, and stores it in reflective memory. Before future tasks, relevant lessons are retrieved and injected as decision-guiding context.

**Acceptance Criteria:**
- [ ] On task failure (tool error, user correction, quality flag), a reflection call generates structured self-evaluation.
- [ ] The reflection prompt is Socratic: asks diagnostic questions, does not provide answers.
- [ ] Lessons are extracted in a structured format: condition → action → observed_outcome → lesson.
- [ ] Reflective memory supports query-by-condition retrieval (task type, tool set, failure mode).
- [ ] Before each task, relevant lessons are retrieved and injected into the system prompt.
- [ ] The cost fingerprint records: reflection tokens spent, lessons retrieved, lesson impact flag.
- [ ] Replay optimizer measures whether lessons actually reduce tokens on replay of historical trajectories.
- [ ] At least 5 fixture scenarios demonstrate: failure → reflection → lesson → successful retry.
- [ ] Lessons are stored in `.sponge/reflections/` as structured JSONL, keyed by condition hash.

**Worker agents:**
- Reflection agent: Socratic evaluation prompt, trajectory analysis, lesson extraction.
- Memory agent: reflective memory store with condition-keyed retrieval (extend `src/sponge/memory/`).
- Integration agent: wire reflection into agent loop (`src/sponge/core/agent.py`).
- CLI agent: `sponge reflections [list|show|apply|prune]`.

### Phase 8: 1/10 Benchmark

Prove the cost reduction target against naive baselines, including Reflexion savings measurement.

### Phase 3+: Commodity Features (✅ complete)

All commodity features are implemented (157 tests, 66 source files):

| Feature | Status |
|---------|--------|
| Context compression (5-layer pipeline) | ✅ |
| Plugin routing + approval gates (file ops, shell, search) | ✅ |
| Sub-agent condensation (codebase exploration) | ✅ |
| Task decomposition | ✅ |
| Progressive context loading | ✅ |
| Semantic cache with state guards | ✅ |
| MCP server integration | ✅ |
| Session resume and multi-turn persistence | ✅ |
| Provider expansion (Anthropic, OpenAI, DeepSeek, OpenRouter) | ✅ |
| Desktop server | ✅ |
| Shell sandbox | ✅ |
| Long-term project memory | ✅ |
| Multimodal input (images, PDFs) | ⏳ |
| 1/10 benchmark proof | ⏳ |
| PyPI publication | ⏳ |

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

## Remaining Work

Remaining implementation:

1. **Phase 7: Reflexion** — structured self-evaluation, lesson extraction, reflective memory, pre-task retrieval. The meta-layer that makes every other layer smarter over time.
2. **Multimodal input** — image and PDF attachment support in the agent loop.
3. **Phase 8: 1/10 benchmark** — prove cost reduction target against naive baselines, including Reflexion savings measurement.
4. **PyPI publication** — make `pip install sponge-ai` work.

Keep [claims.md](claims.md) and [pricing-policy.md](pricing-policy.md) current.
