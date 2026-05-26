# Claims Policy

This document defines which public claims Sponge may make before benchmark
evidence exists. Its purpose is to keep the project honest while the runtime is
still early.

## Claim Classes

| Class | Meaning | Allowed Before Benchmarks |
|-------|---------|---------------------------|
| **Implemented** | The feature exists, has tests, and is user-facing. | Yes, with version or phase. |
| **Measured** | The feature has reproducible benchmark or fixture evidence. | Yes, with workload and method. |
| **Target** | The feature is a design goal but not proven yet. | Yes, only when labeled as target/planned. |
| **Forbidden** | The claim is too broad, unmeasured, or misleading. | No. |

## Allowed Positioning

Use these forms:

- Sponge keeps the configured final reasoning model stable unless the user
  explicitly changes it.
- Sponge reduces paid-token footprint through caching, context compression,
  local tools, helper condensation, and cost accounting.
- Exact compatible repeats can return with `$0` model spend once exact caching
  is implemented.
- Self-tuning is a planned closed loop: cost fingerprints, replay, live shadow
  testing, and guarded config changes.
- Savings claims are workload-specific and must show the baseline, model,
  provider pricing version, repo state assumptions, and measurement method.

## Claims That Need Evidence

These claims are allowed only after reproducible measurements exist:

- Any fixed percentage savings claim, such as "70% cheaper" or "40-60% token
  reduction."
- Any cache hit-rate target, such as "80%+ hit rate," unless scoped to a named
  workload.
- Any competitor comparison, such as "cheaper than Cursor" or "Codex quality at
  lower cost."
- Any self-tuning improvement claim, such as "2-5% cheaper per session" or
  "10-15% reduction from tuning."
- Any latency claim, because cache, embedding, compression, and replay logic may
  add overhead.

## Forbidden Claims

Do not use these forms:

- "Pay less every time."
- "Every session gets cheaper."
- "The same model always costs less."
- "Zero model downgrade" without clarifying that the final reasoning model is
  stable and helper executors may be cheaper or local.
- "Budget ceilings save money" without clarifying that budgets prevent runaway
  spend but do not make an identical successful task cheaper.

## Required Evidence Fields

Every measured savings claim must include:

- Workload name and fixture source.
- Model and provider.
- Pricing table version and date.
- Baseline definition, preferably naive same-model execution.
- Actual cost and estimated naive cost.
- Savings source breakdown: exact cache, semantic cache, prompt cache,
  compression, plugin route, helper condensation, preprocessing, or tuning.
- Latency delta.
- Quality guard used: tests, fixture preservation, user-visible acceptance, or
  rollback signal.

## README Rule

The README may describe broad architecture and goals, but headline claims must
stay conservative until Phase 12 benchmarks exist. Prefer "target," "planned,"
"can," and "on compatible repeated work" over universal language.
