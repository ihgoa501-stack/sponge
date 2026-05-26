# Phase 2 — Replay Optimizer MVP: Implementation Plan

**Goal:** `sponge tune --report` reads fingerprints, runs detectors, shows ranked proposals. Shadow A/B validates through real sessions. Accepted proposals write to config.

---

## Task 1: Settings + Fingerprints Extension

**Files:** `src/sponge/config/settings.py`, `src/sponge/telemetry/collector.py`, `src/sponge/telemetry/models.py`

- [ ] Add tuning settings to `Settings`:
  ```python
  tune_window_days: int = 30
  tune_min_samples: int = 10
  tune_confidence_p: float = 0.05
  tune_min_savings_pct: float = 5.0
  tune_shadow_ratio: float = 0.5
  ```
- [ ] Add `TuningProposal` dataclass to `telemetry/models.py`
- [ ] Add `experiment_id` and `experiment_group` columns to fingerprints table in `collector.py`
- [ ] Extend `log_call()` to accept optional experiment_id and experiment_group

---

## Task 2: Signal Detectors

**Files:** `src/sponge/telemetry/analyzer.py`, `tests/test_analyzer.py`

- [ ] `SignalDetector` ABC with `name` + `detect(db, window_days) -> list[TuningProposal]`
- [ ] `CacheGapDetector` — median gap > TTL → raise TTL
- [ ] `BudgetSlackDetector` — median session cost < 50% budget → lower budget
- [ ] `TaskRepeatDetector` — same task_hash ≥ 3 times with misses → extend TTL
- [ ] Tests: populate fixture DB, run each detector, verify proposals

---

## Task 3: Proposal Store + Tuner Orchestrator

**Files:** `src/sponge/telemetry/tuner.py`, `tests/test_tuner.py`

- [ ] SQLite `proposals.db` with `proposals` table
- [ ] `Tuner` class:
  - `run_detectors(window_days)` — runs all detectors, merges, ranks
  - `rank(proposals)` — sorts by confidence * savings / risk
  - `activate(id)` — moves to testing
  - `evaluate(id)` — Mann-Whitney U on shadow data
  - `apply(id)` — writes to `~/.sponge/config.toml`
- [ ] Mann-Whitney U: try `scipy.stats`, fallback to 30-line pure Python
- [ ] Tests: proposal lifecycle, ranking, evaluation with fixture data

---

## Task 4: Shadow Injection in Agent

**Files:** `src/sponge/cli/run.py`, `src/sponge/core/agent.py`

- [ ] Before `sponge run`, check for active testing proposals
- [ ] 50% of sessions: override parameters with shadow values
- [ ] Pass `experiment_id` + `experiment_group` to collector
- [ ] No change to Agent class — param overrides happen before Agent is created

---

## Task 5: CLI Commands

**Files:** `src/sponge/cli/tune_cmd.py`, `src/sponge/cli/app.py`, `tests/test_cli_tune.py`

- [ ] `sponge tune --report` — runs detectors, displays proposals
- [ ] `sponge tune --apply <id>` — activates proposal for testing
- [ ] `sponge tune --review` — shows experiment status + evaluation
- [ ] `sponge tune --history` — shows all past proposals
- [ ] Tests: CLI output format, apply/review flows

---

## Task 6: Fixture Fingerprints for Testing

**Files:** `tests/conftest.py`, `tests/test_analyzer.py`

- [ ] `populated_db` fixture — creates in-memory DB with 15+ synthetic fingerprints
- [ ] Fingerprints simulate: cache hits, misses, repeats, budget slack patterns
- [ ] Used by both `test_analyzer.py` and `test_tuner.py`
