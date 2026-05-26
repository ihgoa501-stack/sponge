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

## Coding Capability

Sponge is intended to become a coding-capable agent harness. It should be able to answer coding questions, inspect repositories, run tests, edit files under approval, resume interrupted work, and condense large codebase exploration through sub-agents.

The important boundary is timing:

- Before Phase 1, Sponge cannot run useful agent tasks.
- After Phase 1, Sponge can answer coding questions through a single model call.
- After Phase 4, Sponge can safely inspect and edit code through approved local tools.
- After Phase 5, Sponge can resume coding sessions and record replayable cost fingerprints.
- After Phase 8, Sponge can handle larger codebase tasks through sub-agent condensation.

So the answer is yes: Sponge can be used to write code once the tool, approval, and session phases exist. At the current skeleton stage, it is not yet a code-writing agent.

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

The old roadmap placed self-tuning near the end. That delays the product promise. The revised strategy brings the evidence loop forward:

| Phase | Name | Primary Proof | Why It Exists |
|-------|------|---------------|---------------|
| 0 | Development Foundation | Package installs, CLI starts, tests run | Make worker agents productive |
| 1 | Cost-Aware Hello | One streamed model call with real usage and cost | Establish the accounting spine |
| 2 | Savings Ledger + Exact Cache | Repeating the same task costs $0 model spend | Prove the user can see savings immediately |
| 3 | Context Compression MVP | Multi-turn fixtures show fewer input tokens | Prove same model sees less context |
| 4 | Plugin Routing + Approval | Local file/search tasks bypass LLM safely | Prove zero-token work path |
| 5 | Session + Cost Fingerprints | Runs produce replayable cost records | Prepare optimization from real data |
| 6 | Prompt Cache Strategy | Provider-specific prompt cache decisions are visible | Capture major recurring-prefix savings |
| 7 | Semantic Cache with State Guards | Similar stable tasks can reuse answers safely | Add near-repeat savings without stale-code bugs |
| 8 | Sub-Agent Condensation | Exploration returns condensed evidence | Reduce large search/review contexts |
| 9 | Replay-Based Optimizer | Historical runs recommend config changes | Make "越用越省钱" measurable before live A/B |
| 10 | Live Self-Tuning | Winning configs apply through gated feedback | Complete the closed loop |
| 11 | Multimodal + Advanced Providers | Images/PDFs enter the same cost discipline | Extend value without breaking economics |
| 12 | Benchmarks + Public Proof | Published savings suite vs naive baselines | Support launch claims |

## Phase Acceptance Criteria

### Phase 0: Development Foundation

Done when:

- `pip install -e .` works in a fresh checkout.
- `sponge --version` prints the project version.
- `pytest`, `ruff`, and `mypy` run locally.
- CI runs lint, typecheck, and tests.
- No runtime feature claims are added without tests.

Worker agents:

- Infra agent: packaging, CI, lint/typecheck.
- Docs agent: align README, ROADMAP, and CLI docs with Phase 0 status.

### Phase 1: Cost-Aware Hello

Done when:

- `sponge run "say hello"` streams output from one configured provider.
- Actual usage is recorded from provider response events.
- Output includes total estimated or actual cost with model ID.
- Tests use mock providers by default; real provider tests are opt-in.

Worker agents:

- LLM agent: provider ABC, streaming event types, one provider.
- Cost agent: pricing model, usage model, cost tracker.
- CLI agent: `run` command, streaming renderer, JSON mode.

### Phase 2: Savings Ledger + Exact Cache

Done when:

- Identical task + compatible context returns from exact cache without a model call.
- Report includes actual cost, naive baseline, and savings by source.
- Cache keys include prompt, model, relevant config, and project state marker.
- `--no-cache` bypasses caches for debugging.

Worker agents:

- Cache agent: SQLite store and exact result cache.
- Cost agent: naive baseline and savings ledger.
- CLI agent: cost report display.

### Phase 3: Context Compression MVP

Done when:

- Tool outputs above threshold can be masked.
- Message pruning preserves first user request and recent turns.
- Fixture tests show lower token count and preserved answerability.
- Compression reports pre/post tokens and layer decisions.

Worker agents:

- Context agent: masking and pruning only.
- Test agent: realistic fixture conversations and preservation checks.

### Phase 4: Plugin Routing + Approval

Done when:

- Read-only file listing/search can execute locally with zero model cost.
- Writes and shell execution pass through approval policy.
- Tool decisions are logged to cost ledger and event stream.
- Native plugins are preferred before MCP.

Worker agents:

- Plugin agent: plugin ABC, registry, read-only builtins.
- Approval agent: allow/confirm/reject policy chain.
- Security agent: dangerous command/file operation tests.

### Phase 5: Session + Cost Fingerprints

Done when:

- Each run emits a cost fingerprint JSON record.
- Sessions can be listed and resumed from persisted state.
- Fingerprints include repo state, provider capabilities, cache decisions, compression decisions, and usage.
- Fingerprints are stable enough for replay simulation.

Worker agents:

- Session agent: event stream, session lifecycle.
- Telemetry agent: fingerprint schema and SQLite persistence.

### Phase 6: Prompt Cache Strategy

Done when:

- Provider capabilities declare prompt cache support, TTLs, and multipliers.
- Prompt cache decisions are recorded in the savings ledger.
- Break-even logic avoids cache writes that are likely more expensive than misses.
- Provider changes warn about changed cache economics.

Worker agents:

- Provider agent: capability model.
- Cache agent: prompt cache policy and accounting.

### Phase 7: Semantic Cache with State Guards

Done when:

- Semantic cache can return near-repeat answers only under compatible state.
- Embedding model ID is locked into cache metadata.
- False-positive risk is handled with high default threshold and traceable reasons.
- Stale repository state causes a cache miss.

Worker agents:

- Semantic cache agent: embeddings, similarity, metadata.
- Safety agent: stale-cache and false-positive fixtures.

### Phase 8: Sub-Agent Condensation

Done when:

- Search/review sub-agents return structured condensed findings, not raw transcript dumps.
- Parent model receives evidence summaries with source references.
- Savings ledger compares raw exploration tokens against condensed tokens.
- Sub-agent model use is documented as helper execution, not final-model downgrade.

Worker agents:

- Sub-agent agent: dispatch and result schema.
- Review/search agent: first built-in sub-agent tasks.

### Phase 9: Replay-Based Optimizer

Done when:

- Historical cost fingerprints can be replayed under alternative config values.
- Optimizer produces proposals with estimated cost delta and risk.
- Proposals include rejection reasons, not just winners.
- Replay does not call real LLM APIs.

Worker agents:

- Optimizer agent: replay engine and proposal model.
- Telemetry agent: query helpers over fingerprint store.

### Phase 10: Live Self-Tuning

Done when:

- Low-risk proposals can enter shadow testing.
- Shadow testing tracks cost, latency, cache rate, compression ratio, and rollback signals.
- Winning changes are applied to config with history.
- High-risk changes require user review.

Worker agents:

- Feedback agent: experiment assignment and evaluation.
- Config agent: tunable config store and history.
- CLI agent: `sponge tune --report`.

### Phase 11: Multimodal + Advanced Providers

Done when:

- Image/PDF inputs are represented as content blocks.
- Multimodal cache keys include file hashes.
- Compression policy can omit old images with explicit placeholders.
- Anthropic/OpenAI provider differences are surfaced.

Worker agents:

- Provider agent: multimodal support.
- Context agent: multimodal budget.
- Cache agent: file content addressing.

### Phase 12: Benchmarks + Public Proof

Done when:

- Benchmark suite compares Sponge against naive same-model baselines.
- Claims are workload-scoped and reproducible.
- Docs show methodology, not only headline percentages.
- Public README claims match benchmark evidence.

Worker agents:

- Benchmark agent: fixtures, scripts, reports.
- Docs agent: claim calibration and launch narrative.

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

The next planner outputs should be written in this order:

1. `docs/superpowers/plans/2026-05-24-phase-0-foundation.md`
2. `docs/superpowers/plans/2026-05-24-phase-1-cost-aware-hello.md`
3. `docs/superpowers/plans/2026-05-24-phase-2-savings-ledger-cache.md`
4. Keep [claims.md](claims.md) and [pricing-policy.md](pricing-policy.md) current as implementation evidence changes.

Do not start broad runtime implementation before Phase 0 and Phase 1 plans are approved.
