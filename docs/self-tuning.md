> ⚠️ **Draft** — The replay optimizer (Phase 2) supersedes the self-tuning design described here. This document will be updated when Phase 2 is complete. See [project-plan.md](project-plan.md) for current strategy.

# Self-Tuning Infrastructure

> Sponge's most radical planned feature: the harness records cost fingerprints,
> replays candidate configurations, and only then tests low-risk changes live.
> Every call, cache hit, compression decision, and budget event feeds into a
> local telemetry store.

---

## Overview

```
┌────────────────────────────────────────────────────────────────┐
│  1. COLLECT       2. REPLAY        3. VALIDATE       4. APPLY  │
│  Telemetry        Optimizer        Feedback          Parameter │
│  Collector        + Analyzer       Loop              Tuner     │
│                                                                    │
│  (every call)     (post-session)   (shadow A/B)      (commit)   │
└────────────────────────────────────────────────────────────────┘
```

Four components. No ML framework. No server. SQL, replay simulation, and simple
statistics.

---

## Why Self-Tuning?

Static configurations are suboptimal because usage patterns vary:

| Pattern | Static Config Problem | Self-Tuning Solution |
|---------|----------------------|---------------------|
| User takes coffee breaks | 5-min cache TTL expires between prompts | Detect 8-min cadence → extend TTL to 1h |
| User asks same question daily | 24h result cache TTL misses next-day repeat | Detect pattern → extend TTL to 72h |
| User does simple lookups | Budget ceiling at P95 may allow runaway spend | Detect utilization → propose a lower ceiling as a risk-control change |
| Compression barely saves | Masking threshold too conservative | Detect ratio <1.2× → increase aggressiveness |
| Sub-agent returns too much raw data | Condensation disabled | Detect >10K tokens → force condensation on |

**Target effect:** accepted changes reduce measured cost on compatible repeated
work without increasing known quality, latency, or rollback risk. No per-session
reduction is promised before benchmarks prove it.

---

## Component 1: Telemetry Collector

**Purpose:** Record every cost-significant event with minimal overhead.

**Design:**
- Non-blocking: events are queued and flushed in background batches
- Overhead: <0.1ms per event
- Storage: SQLite at `~/.sponge/telemetry/events.db`

**Event types:**

| Event | Fields | When |
|-------|--------|------|
| `llm_call` | tokens_in, tokens_out, cache_hit/miss, cost, latency, model | Every LLM response |
| `cache_decision` | level, key_hash, hit/miss, ttl | Every cache lookup |
| `compress` | pre/post tokens, layer (1-5), ratio | Every compression run |
| `subagent` | task_type, tokens_consumed, tokens_returned, ratio | Every sub-agent completion |
| `circuit_breaker` | trigger_axis, budget_consumed, limit | Every budget check |
| `plugin` | plugin_name, zero_cost, latency | Every plugin execution |

**Schema:**

```sql
CREATE TABLE events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    timestamp   REAL NOT NULL,
    data        TEXT NOT NULL   -- JSON blob
);
CREATE INDEX idx_events_session ON events(session_id);
CREATE INDEX idx_events_type ON events(event_type);
```

---

## Component 2: Pattern Analyzer

**Purpose:** Analyze telemetry data and replay historical fingerprints under
candidate settings before producing live tuning proposals.

**Mechanism:** SQL queries over the event table plus replay simulation over cost
fingerprints. No ML, no external services.

**Signals detected:**

| Signal | Query Logic | Tuning Proposal |
|--------|-------------|-----------------|
| **Cache gap** | Median time between consecutive `llm_call` events > 5 min | `prompt_cache_ttl`: 5m → 1h |
| **Compression waste** | Median compression ratio < 1.2 | `masking_threshold`: raise (more aggressive) |
| **Budget slack** | Median session budget utilization < 50% | `budget_ceiling`: P95 → P75 as risk control, not savings |
| **Task repeats** | ≥3 identical SHA256 cache hits in 7 days | `result_cache_ttl`: 24h → 72h |
| **Sub-agent waste** | Median sub-agent return > 10K tokens | Enable/strengthen `subagent_condensation` |
| **Preprocessor gap** | Prompts > 5K tokens bypassing local preprocessor | Suggest enabling preprocessor |

**Output:** `List[TuningProposal]`, where each proposal is:

```python
@dataclass
class TuningProposal:
    param: str                    # Which knob to turn
    from_val: Any                 # Current value
    to_val: Any                   # Proposed value
    reason: str                   # Human-readable explanation
    estimated_savings: float      # $ per session
    risk: Literal["low", "medium", "high"]
```

---

## Component 3: Feedback Loop

**Purpose:** Validate replay-backed proposals before committing via shadow A/B
testing.

**Method:**

1. **Replay first:** Historical cost fingerprints are evaluated under the
   proposed parameter value. Proposals that do not show a plausible net benefit
   or violate safety constraints never enter live testing.

2. **Shadow config injection:** A configurable fraction of new sessions
   (deterministic hash, not random) receive the proposed parameter value
   alongside the baseline value. Both execute normally; costs and risk signals
   are tracked separately.

3. **Statistical evaluation:** After enough sessions, compare shadow vs baseline:

   - **Test:** Mann-Whitney U test (non-parametric, appropriate for non-normal cost distributions)
   - **Threshold:** ≥5% cost reduction at ≥95% confidence (p < 0.05)
   - **Risk checks:** no worse latency tail, no increased rollback/correction signal, no known fixture-preservation failure
   - **Fallback:** If `scipy` unavailable, a simplified 30-line implementation

4. **Verdict:**
   - **Commit:** Apply the change permanently
   - **Discard:** Reject with prejudice — same pattern won't re-propose until telemetry shifts significantly
   - **Extend:** If signal is promising but not significant, collect more data

**Risk gating:**

| Risk Level | Criteria | Action |
|-----------|----------|--------|
| Low | Estimated impact < $0.50/session | Auto-apply on A/B pass |
| Medium | $0.50-2.00/session impact | Stage in config, notify user |
| High | >$2.00/session or behavioral change | Human approval required |

---

## Component 4: Parameter Tuner

**Purpose:** Apply winning configurations.

```python
class ParameterTuner:
    async def apply(self, result, proposal):
        # Record in tuning history
        await db.execute("""
            INSERT INTO tuning_history (param, from_val, to_val, savings_pct,
                p_value, verdict, applied_at)
            VALUES (?,?,?,?,?,?, datetime('now'))
        """, (proposal.param, str(proposal.from_val), str(proposal.to_val),
              result.savings_pct, result.p_value, result.verdict))

        if result.verdict == "commit":
            await self.config.set(proposal.param, proposal.to_val)
```

**Config system:** Every tunable parameter is wired through a central config that supports per-parameter overrides without restart. The tuner writes to `~/.sponge/config.toml`; the running harness picks up changes immediately.

---

## Tunable Parameters

| Parameter | Default | Tuned By | What It Changes |
|-----------|---------|----------|-----------------|
| `prompt_cache_ttl` | 5 min | Request cadence | Cache retention period for system prompt |
| `masking_threshold` | 2000 tokens | Compression ratio | How many tokens before masking triggers |
| `pruning_min_turns` | 5 | Context utilization | Minimum history preserved |
| `budget_ceiling` | P95 | Spend distribution | Budget limit auto-calibration |
| `result_cache_ttl` | 24 hours | Repeat frequency | Exact-match cache lifetime |
| `semantic_threshold` | 0.95 cosine | False positive rate | Semantic match strictness |
| `subagent_condensation` | Enabled | Return token volume | Force/enable sub-agent summary |
| `preprocessor_trigger` | 2000 tokens | Compression data | When to use local preprocessor |
| `circuit_breaker_single` | $2.00 | Per-call distribution | Per-call hard limit |

---

## End-to-End Example

```
Session 1-10 (baseline collection):
  └─ Collector logs 47 events to SQLite
  └─ Analyzer: median request gap = 8.2 min, TTL = 5 min

Session 11 (analyzer triggers):
  └─ Candidate: prompt_cache_ttl → 1h, estimated +$0.04/session
  └─ Replay Optimizer: historical fingerprints show plausible net benefit
  └─ FeedbackLoop: Start limited shadow experiment

Session 12-31 (testing):
  └─ Shadow and baseline sessions tracked with cost, latency, and risk flags

Session 32 (evaluation):
  └─ Shadow mean: $0.14, Baseline mean: $0.18
  └─ Savings: 22.2%, p = 0.012, no risk signal increase
  └─ Tuner: COMMIT or stage for review based on risk level

Session 33+ (benefit realized):
  └─ Compatible sessions use 1h TTL; ledger records realized savings
```

---

## Dashboard

```bash
$ sponge tune --report
═══════════════════════════════════════════════════════════════
  Sponge Self-Optimization Report (example)
═══════════════════════════════════════════════════════════════
  Sessions analyzed:        247
  Parameters auto-tuned:      3   (2 auto-applied, 1 pending)
  Savings from tuning:    $1.87   (measured on compatible sessions)

  ┌─ Recent Changes ─────────────────────────────────────────┐
  │ ✔ prompt_cache_ttl    5m → 1h    +$0.31/session (3 days)  │
  │ ✔ masking_threshold 2000 → 3500  +$0.12/session (1 week)  │
  │ ⏳ budget_ceiling   P95 → P80     -$0.05/session (pending) │
  └──────────────────────────────────────────────────────────┘

  Projected annual savings at current rate: $42.50
═══════════════════════════════════════════════════════════════
```

---

## Privacy

- All telemetry is stored **locally** in `~/.sponge/telemetry/`
- **No data leaves the machine** — no server, no cloud dependency, no phoning home
- Offline analysis only
- Full privacy by architecture

---

## Design Simplicity

- **No ML framework:** Pure SQL queries over structured events
- **No server:** SQLite is the database, the filesystem is the transport
- **~500 lines total** for all four components
- **Each component independently testable** with mock DB fixtures
