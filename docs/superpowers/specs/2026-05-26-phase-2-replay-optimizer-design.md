# Phase 2 — Replay Optimizer MVP: Design Spec

> 2026-05-26 · Status: Draft

## Overview

Phase 2 adds a signal-detection framework that reads cost fingerprints from SQLite, detects optimization opportunities, produces ranked tuning proposals, and validates them through real-world shadow A/B testing. No simulation — every validation runs on live session data.

## Architecture

```
sponge tune --report / --apply / --review
        │
        ▼
┌───────────────────────────────────────┐
│  Orchestrator (tuner.py)              │
│  · Runs all detectors                 │
│  · Merges & ranks proposals           │
│  · Manages proposal lifecycle         │
│    (proposed → testing → accepted)    │
├───────────────────────────────────────┤
│  Detectors (analyzer.py)              │
│  · CacheGapDetector                   │
│  · BudgetSlackDetector                │
│  · TaskRepeatDetector                 │
│  · (extensible — add more anytime)    │
├───────────────────────────────────────┤
│  Fingerprints DB                      │
│  ~/.sponge/telemetry/fingerprints.db  │
└───────────────────────────────────────┘
```

## Data Models

### TuningProposal

```python
@dataclass
class TuningProposal:
    id: str              # "cache_gap:2026-05-26T12:00"
    param: str           # "cache_ttl_hours"
    current: object      # 24
    proposed: object     # 72
    reason: str          # Human-readable explanation
    evidence_sql: str    # The SQL query that produced this
    confidence: float    # 0.0–1.0, heuristic score
    risk: str            # "low" | "medium" | "high"
    state: str           # "proposed" | "testing" | "accepted" | "rejected"
    created_at: str      # ISO-8601
```

### ProposalStore

SQLite table at `~/.sponge/telemetry/proposals.db`:

```sql
CREATE TABLE proposals (
    id TEXT PRIMARY KEY,
    param TEXT NOT NULL,
    current_val TEXT NOT NULL,
    proposed_val TEXT NOT NULL,
    reason TEXT NOT NULL,
    evidence_sql TEXT NOT NULL,
    confidence REAL NOT NULL,
    risk TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'proposed',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

## Signal Detector Interface

```python
class SignalDetector(ABC):
    name: str

    @abstractmethod
    def detect(self, db: sqlite3.Connection, window_days: int) -> list[TuningProposal]:
        """Query fingerprints and return proposals."""
```

### Detector 1: CacheGapDetector

**Signal:** Median time gap between consecutive calls in the same session exceeds `cache_ttl_hours`, meaning the cache TTL is expiring between requests that might otherwise hit.

**SQL:**
```sql
SELECT AVG(gap_minutes) FROM (
    SELECT (julianday(t2.timestamp) - julianday(t1.timestamp)) * 1440 AS gap_minutes
    FROM fingerprints t1
    JOIN fingerprints t2 ON t2.id = t1.id + 1 AND t2.session_id = t1.session_id
    WHERE t1.timestamp > datetime('now', ?)
)
```

**Proposal:** If median gap > current `cache_ttl_hours * 60` → propose TTL = median gap * 1.5 (rounded to nearest hour).

**Risk:** low. Only increases cache retention; downside is disk space (negligible).

**Confidence:** min(1.0, gap_ratio / 3) where gap_ratio = median_gap / current_ttl.

### Detector 2: BudgetSlackDetector

**Signal:** Median session total cost is well below `budget_per_session`, meaning the budget ceiling is unnecessarily high (it's a risk control, not savings — but too high a ceiling provides no guardrail).

**SQL:**
```sql
SELECT session_id, SUM(cost) as total
FROM fingerprints
WHERE timestamp > datetime('now', ?)
GROUP BY session_id
```

**Proposal:** If median session cost < budget_per_session * 0.5 → propose budget = P75 session cost * 1.2.

**Risk:** medium. Lowering budget could block legitimate expensive tasks.

**Confidence:** 0.5 + (1.0 - utilization_ratio) * 0.5. Higher slack = higher confidence.

### Detector 3: TaskRepeatDetector

**Signal:** Same `task_hash` appears ≥ 3 times within the window, and at least one occurrence was a cache miss.

**SQL:**
```sql
SELECT task_hash, COUNT(*) as cnt,
       SUM(CASE WHEN cache_hit = 0 THEN 1 ELSE 0 END) as misses
FROM fingerprints
WHERE timestamp > datetime('now', ?)
GROUP BY task_hash
HAVING cnt >= 3 AND misses > 0
```

**Proposal:** For each detected repeat, check if extending `cache_ttl_hours` would have prevented the misses. If the first and last occurrence of a task_hash span is > current TTL, propose TTL = span * 1.5.

**Risk:** low. Same reasoning as CacheGapDetector.

**Confidence:** min(1.0, repeat_count / 5).

## Shadow A/B Lifecycle

No simulation. Validation runs on real sessions.

### State Machine

```
proposed ──→ testing ──→ accepted
                │
                └──→ rejected (if p > 0.05 after min_samples)
```

### Flow

1. **User reviews proposals** via `sponge tune --report`, approves with `sponge tune --apply <id>`.
2. **Shadow injection:** During `sponge run`, if there's a `testing` proposal for a parameter, 50% of sessions use the proposed value instead of the current value. Both paths write fingerprints normally, tagged with `experiment_id`.
3. **Evaluation:** `sponge tune --review` runs Mann-Whitney U test comparing baseline vs shadow session costs.
4. **Decision:** p < 0.05 AND median savings ≥ 5% → accepted → writes to `~/.sponge/config.toml`. Otherwise stays in testing or moves to rejected.

### Fingerprints table extension

Add two nullable columns for A/B tracking:

```sql
ALTER TABLE fingerprints ADD COLUMN experiment_id TEXT;
ALTER TABLE fingerprints ADD COLUMN experiment_group TEXT;  -- "baseline" | "shadow"
```

## Orchestrator

```python
class Tuner:
    def __init__(self, db_path: str, proposal_db: str, settings: Settings):
        ...

    def run_detectors(self, window_days: int = 30) -> list[TuningProposal]:
        """Run all registered detectors, merge/rank results."""

    def rank(self, proposals: list[TuningProposal]) -> list[TuningProposal]:
        """Sort by: confidence * savings_impact / risk_score, deduplicate."""

    def activate(self, proposal_id: str) -> None:
        """Move proposal to 'testing' state."""

    def evaluate(self, proposal_id: str) -> dict:
        """Run Mann-Whitney U on collected shadow data."""

    def apply(self, proposal_id: str) -> None:
        """Accept winning proposal → write to config.toml."""
```

### Merging/dedup strategy

When two proposals touch the same parameter, keep the one with higher confidence, discard the other with a note.

## CLI Commands

### `sponge tune --report`

```bash
$ sponge tune --report
Tuning Report (last 30 days, 47 sessions)
─────────────────────────────────────────

1. cache_ttl_hours: 24 → 72 (confidence: 0.82, risk: low)
   Median gap between requests (8.2 min) exceeds cache TTL (24h).
   Estimated savings: ~$0.04/session.
   [proposed] — approve with: sponge tune --apply cache_gap:2026-05-26T12:00

2. budget_per_session: $10.00 → $4.50 (confidence: 0.71, risk: medium)
   Median session cost ($2.10) is 21% of budget ceiling.
   [proposed] — approve with: sponge tune --apply budget_slack:2026-05-26T12:01

No active experiments.
```

### `sponge tune --apply <id>`

Moves proposal to `testing` state. On next `sponge run` calls, shadow A/B begins.

### `sponge tune --review`

Shows status of active experiments with current p-values and savings estimates.

## Settings Changes

Add to `Settings`:

```python
# Tuning
tune_window_days: int = 30
tune_min_samples: int = 10       # min shadow sessions before evaluation
tune_confidence_p: float = 0.05  # Mann-Whitney U threshold
tune_min_savings_pct: float = 5.0  # % savings required to accept
tune_shadow_ratio: float = 0.5     # fraction of sessions that use shadow params
```

## Files

| File | Action | Purpose |
|------|--------|---------|
| `src/sponge/telemetry/models.py` | Modify | Add `TuningProposal` dataclass |
| `src/sponge/telemetry/collector.py` | Modify | Add `experiment_id` / `experiment_group` columns |
| `src/sponge/telemetry/analyzer.py` | Create | `SignalDetector` ABC + 3 detectors |
| `src/sponge/telemetry/tuner.py` | Create | `Tuner` orchestrator + proposal store + A/B logic |
| `src/sponge/cli/tune_cmd.py` | Create | `sponge tune` commands |
| `src/sponge/cli/app.py` | Modify | Register `tune` command |
| `src/sponge/cli/run.py` | Modify | Shadow param injection during `sponge run` |
| `src/sponge/config/settings.py` | Modify | Add tuning settings |
| `tests/test_analyzer.py` | Create | Detector tests with fixture fingerprints |
| `tests/test_tuner.py` | Create | Tuner lifecycle + A/B evaluation tests |
| `tests/conftest.py` | Modify | Add fixture to populate test fingerprint DB |

## Acceptance Criteria

- `sponge tune --report` shows ranked proposals from ≥ 10 fixture fingerprints.
- At least 1 non-trivial proposal detected from fixture data.
- `sponge tune --apply <id>` moves proposal to testing.
- Shadow A/B injection works during `sponge run`.
- Mann-Whitney U correctly accepts/rejects based on collected data.
- Accepted proposals write to `~/.sponge/config.toml`.
- All tests pass with SQLite fixture data (no real API calls).
