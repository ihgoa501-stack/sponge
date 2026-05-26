# Cost Model — How Sponge Accounts For Savings

> Sponge's core claim is narrower and testable: for compatible repeated project
> work, the configured final reasoning model should receive fewer paid tokens
> than a naive same-model harness. This document explains the accounting model.

---

## The Baseline

The primary baseline is a naive same-model harness with no caching, no
compression, no plugin routing, and no helper condensation.

| Scenario | Baseline Shape | Why It Costs Money |
|----------|----------------|--------------------|
| Simple Q&A | One prompt, one model call | Pays full system + user prompt cost. |
| Code review | Multiple turns with repository context | Re-sends repeated context and tool output. |
| Multi-step refactor | Search, edit, test, repair loop | Accumulates history and tool observations. |

Exact dollar amounts depend on the configured provider pricing table. Public
docs should not quote provider prices unless they are sourced and dated; see
[pricing-policy.md](pricing-policy.md).

---

## The Saving Layers

Each layer independently reduces cost. They compound.

### Layer 1: Plugin Routing

Tasks that don't need an LLM at all → **\$0**.

| Task | Naive (Opus 4.7) | Sponge (plugin) | Saving |
|------|-------------------|-----------------|--------|
| `list files` | $0.08 | $0.00 | **100%** |
| `read file` | $0.08 | $0.00 | **100%** |
| `run shell command` | $0.12 | $0.00 | **100%** |

### Layer 2: Result Cache (Exact Match)

Identical compatible task repeated → **\$0 model spend** for exact cache hits.
Semantic cache has embedding and stale-answer risk, so it must be state-guarded.

| Cache Level | Hit Accounting | Required Guard |
|-------------|----------------|----------------|
| Exact (SHA256) | `$0` model spend | Task, prompt, model, config, and state marker match. |
| Semantic | Embedding/search cost, no final model call if accepted | Compatible repository state, model version, tool version, and relevant file hashes. |

Cache hit-rate targets must be workload-specific. Stable repeated Q&A can have a
high hit rate; active coding tasks usually have lower hit rates because files
and test results change.

### Layer 3: Prompt Cache

System prompt + tool definitions + frequent prefixes may be cheaper when the
provider supports prompt caching. Cache write/read multipliers and TTLs differ
by provider and can change.

| Provider Capability | Accounting Impact |
|---------------------|-------------------|
| Cache read multiplier | Reduces paid input cost for retained prefix. |
| Cache write multiplier | Adds cost when creating or refreshing cache. |
| TTL semantics | Determines whether a prefix survives user pauses. |
| Cache breakpoint rules | Decide where Sponge should split stable and volatile context. |

Prompt cache savings must be reported as provider-specific ledger entries, not
as universal percentages.

### Layer 4: Context Compression

Mask + prune + summarize reduce input tokens only when they preserve the facts
needed to finish the task. Compression ratio alone is not a success metric.

| Compression Level | Expected Use | Required Proof |
|-------------------|--------------|----------------|
| Light | Old low-signal turns | Token count drops; recent intent remains. |
| Medium | Large prior tool outputs | Required file paths, errors, and decisions remain. |
| Heavy | Long history near context limit | Fixture preservation and rollback path exist. |

The savings ledger should show pre/post token counts, latency overhead, and any
quality-risk marker.

### Layer 5: Sub-Agent Condensation

Helper agents do exploration; the final model sees condensed evidence rather
than raw transcripts.

The ledger compares raw exploration tokens, helper cost, condensation size, and
source references. This is not a silent final-model downgrade because helper
outputs are preparatory and auditable.

### Layer 6: Local Preprocessing

Ollama or another local helper can compress prompts or generate drafts before the
configured final model is called.

Local inference has no API token fee, but it does have latency and local compute
cost. Sponge should report the latency trade-off when it uses preprocessing.

---

## Compound Effect

Applying all layers to a multi-step refactor should be reported as a ledger, not
as a universal headline percentage:

| Ledger Row | What It Records |
|------------|-----------------|
| Naive baseline | Same model, same task, no cache/compression/plugins. |
| Exact cache | Avoided final model calls for compatible repeats. |
| Prompt cache | Provider-reported cached input tokens and multipliers. |
| Context compression | Pre/post tokens plus preservation check. |
| Plugin routing | Tasks completed without model calls. |
| Helper condensation | Raw exploration tokens vs condensed evidence. |
| Preprocessing | Input reduction, local latency, and final-model tokens. |

The public claim should name the workload and evidence. Example: "On benchmark
fixture X, Sponge reduced paid input tokens by Y% versus naive same-model
execution, with tests Z passing."

---

## Pricing Tables

Runtime pricing belongs in a versioned pricing file, not prose. See
[pricing-policy.md](pricing-policy.md) for required fields and citation rules.
Docs may include illustrative tables only when they are clearly labeled as
examples and do not drive tests.

---

## Budget Enforcement

Even with savings, budgets prevent surprises.

### Circuit Breaker: 3-Axis Check

| Axis | Check | Default Limit |
|------|-------|---------------|
| **Per-call** | `cost_estimator.estimate(messages) > limit` | $2.00 |
| **Cumulative** | `session.total_cost > budget.p95` | P95 of historical distribution |
| **Steps** | `turn_count > max_steps` | 50 |

**Behaviour when tripped:**
- Per-call: agent asks for confirmation before proceeding
- Cumulative: warning at 80%, hard block at 100%
- Steps: force-end with partial results

**Crucially:** the circuit breaker does not silently replace the configured
final reasoning model. Budget exceeded = stop or ask, not automatic model
routing. Budget stops are risk controls, not savings ledger entries.

---

## Telemetry-Driven Optimization

Every cost decision feeds the self-tuning loop (see [self-tuning.md](self-tuning.md)).

Over enough compatible cost fingerprints, parameters may be proposed for
adjustment:
- Cache TTLs extend if repeat patterns are detected
- Compression thresholds tighten if budget is consistently undershot
- Circuit breaker limits calibrate to historical spend distributions

Every accepted change must show measured cost delta, latency delta, risk level,
and rollback path. "Cheaper over time" is a benchmarked outcome, not a universal
promise.
