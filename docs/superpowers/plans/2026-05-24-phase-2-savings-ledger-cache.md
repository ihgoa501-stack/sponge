# Phase 2 Savings Ledger and Exact Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make repeated compatible tasks avoid model calls and show a savings ledger that proves the saved cost.

**Architecture:** Add a SQLite-backed exact result cache before the LLM call, then add a savings ledger after every run. Cache validity is conservative: exact task, same model, same relevant config, compatible project state marker.

**Tech Stack:** Python 3.12+, SQLite, hashlib, JSON, pytest, Typer.

---

## Scope

Allowed:

- Exact result cache.
- Cache key metadata.
- Savings ledger.
- `--no-cache`.
- Offline tests using mock provider.

Not allowed:

- Semantic cache.
- Prompt cache.
- Provider-side prompt caching.
- Context compression.
- Self-tuning.

## Files

- Create: `src/sponge/cache/base.py`
- Create: `src/sponge/cache/disk_store.py`
- Create: `src/sponge/cache/result_cache.py`
- Create: `src/sponge/cost/ledger.py`
- Create: `src/sponge/core/project_state.py`
- Modify: `src/sponge/core/agent.py`
- Modify: `src/sponge/core/task.py`
- Modify: `src/sponge/cli/run.py`
- Test: `tests/unit/test_disk_store.py`
- Test: `tests/unit/test_result_cache.py`
- Test: `tests/unit/test_savings_ledger.py`
- Test: `tests/integration/test_cache_run.py`

## Public Interfaces

```python
class CacheKey:
    task_hash: str
    model: str
    project_state: str
    config_hash: str
```

```python
class CachedResult:
    text: str
    model: str
    original_cost_usd: Decimal
    created_at: float
    metadata: dict[str, str]
```

```python
class SavingsLedger:
    naive_cost_usd: Decimal
    actual_cost_usd: Decimal
    saved_by_cache_usd: Decimal
    saved_by_compression_usd: Decimal
    saved_by_plugin_usd: Decimal
```

In Phase 2, compression and plugin savings are always zero.

## Task 1: SQLite Disk Store

**Files:**

- Create: `src/sponge/cache/disk_store.py`
- Test: `tests/unit/test_disk_store.py`

- [ ] **Step 1: Write failing disk store tests**

Tests must cover:

- put/get JSON payload by key.
- missing key returns `None`.
- expired row returns `None`.
- store creates parent directory automatically.

- [ ] **Step 2: Implement `DiskStore`**

Use SQLite table:

```sql
CREATE TABLE IF NOT EXISTS cache_entries (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
)
```

Methods:

- `put(key: str, value: dict[str, object], ttl_seconds: int) -> None`
- `get(key: str) -> dict[str, object] | None`
- `delete(key: str) -> None`

- [ ] **Step 3: Run tests**

Run:

```bash
pytest tests/unit/test_disk_store.py -v
```

Expected: all pass.

## Task 2: Exact Result Cache

**Files:**

- Create: `src/sponge/cache/base.py`
- Create: `src/sponge/cache/result_cache.py`
- Create: `src/sponge/core/project_state.py`
- Test: `tests/unit/test_result_cache.py`

- [ ] **Step 1: Write failing cache key tests**

Tests must assert:

- Same task/model/state/config produces same key.
- Different model produces different key.
- Different project state produces different key.
- Whitespace-normalized equivalent task produces same key only if normalization is explicitly implemented.

- [ ] **Step 2: Implement project state marker**

For Phase 2, use conservative marker:

- If inside a git repo, use current `HEAD` commit plus dirty flag.
- If not inside git, use absolute current working directory string and `nogit`.

Do not hash all files yet.

- [ ] **Step 3: Implement result cache**

`ResultCache` should:

- use `DiskStore`.
- build SHA256 key from canonical JSON metadata.
- return `CachedResult | None`.
- store original model cost so later cache hits can report saved cost.

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/unit/test_result_cache.py -v
```

Expected: all pass.

## Task 3: Savings Ledger

**Files:**

- Create: `src/sponge/cost/ledger.py`
- Modify: `src/sponge/cost/reporter.py`
- Test: `tests/unit/test_savings_ledger.py`

- [ ] **Step 1: Write failing ledger tests**

Tests must cover:

- cache miss: actual equals model cost, saved by cache is zero.
- cache hit: actual is zero, saved by cache equals original cost.
- total savings equals naive minus actual.
- report includes `naive`, `actual`, and `saved_by_cache`.

- [ ] **Step 2: Implement ledger model**

Use Decimal fields for all dollar values.

- [ ] **Step 3: Update reporter**

Human output must include:

```text
Naive cost:
Actual cost:
Saved by cache:
Saved by compression:
Saved by plugin:
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/unit/test_savings_ledger.py -v
```

Expected: all pass.

## Task 4: Agent Cache Integration

**Files:**

- Modify: `src/sponge/core/agent.py`
- Modify: `src/sponge/core/task.py`
- Test: `tests/integration/test_cache_run.py`

- [ ] **Step 1: Write failing integration test**

Test scenario:

1. Run `Agent.run("same task")` with mock provider.
2. Assert mock provider was called once.
3. Run the same task again with same model/state/config.
4. Assert mock provider call count remains one.
5. Assert second result text equals first result text.
6. Assert second result ledger actual cost is zero and saved_by_cache is greater than zero.

- [ ] **Step 2: Extend TaskResult**

Add:

- `from_cache: bool`
- `savings_ledger: SavingsLedger`

- [ ] **Step 3: Integrate cache before provider call**

Agent flow:

1. Build cache key.
2. If cache enabled and hit, return cached result with zero actual model cost.
3. If miss, call provider.
4. Store result with original cost.
5. Return result with ledger.

- [ ] **Step 4: Run integration test**

Run:

```bash
pytest tests/integration/test_cache_run.py -v
```

Expected: all pass.

## Task 5: CLI Cache Controls

**Files:**

- Modify: `src/sponge/cli/run.py`
- Test: `tests/integration/test_run_command.py`

- [ ] **Step 1: Add failing CLI cache tests**

Tests:

- First run prints `Cache: miss`.
- Second run prints `Cache: hit`.
- `--no-cache` forces a miss.
- JSON output includes `from_cache` and `savings_ledger`.

- [ ] **Step 2: Implement `--no-cache`**

When set, agent must skip lookup and skip write unless explicitly documented otherwise. Phase 2 should skip both.

- [ ] **Step 3: Run CLI tests**

Run:

```bash
pytest tests/integration/test_run_command.py -v
```

Expected: all pass.

## Acceptance Criteria

Phase 2 is complete only when:

- Running the same mock task twice results in one provider call.
- Second run reports actual model cost `$0`.
- Savings ledger separates naive, actual, cache, compression, and plugin categories.
- Cache key includes model, config hash, and project state marker.
- `--no-cache` works.
- Tests are offline and deterministic.

## Planner Review Checklist

- Is cache validity conservative enough to avoid stale coding answers?
- Does the ledger make the product promise visible?
- Are compression/plugin savings zero in Phase 2 rather than faked?
- Can later semantic cache and prompt cache reuse these abstractions?
