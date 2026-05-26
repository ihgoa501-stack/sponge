# Phase 1 — Agent Loop + Cost Fingerprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `sponge run "hello"` streams output from a configured provider, records a cost fingerprint on every call, and reports savings vs naive baseline. Exact cache returns $0 for repeated tasks.

**Architecture:** Phase 1 establishes the accounting spine. No context compression, no plugin routing, no semantic cache — those are Phase 3+.

---

## Scope

Allowed:

- LLM provider ABC + Anthropic Claude provider (streaming)
- Provider factory (reads config, picks provider)
- Token counting (tiktoken) + pricing loader (from `src/sponge/data/pricing.toml`)
- Cost tracker (incremental, streaming-aware) + savings ledger
- Exact result cache (SHA256, SQLite, state-aware keys)
- Cost fingerprint → SQLite telemetry on every call
- Agent loop (~30 line async while loop)
- CLI: `sponge run <task>`, `sponge config [show|set]`
- Structured logging + exception hierarchy
- Mock providers for tests; real provider tests opt-in via `--run-slow`
- 3 benchmark fixtures (simple Q&A, repeated Q&A, code question)

Not allowed:

- Context compression pipeline
- Plugin routing / file operations / shell execution
- Semantic cache (embedding-based)
- Sub-agents
- Multimodal input
- MCP server integration
- Session persistence (beyond fingerprint recording)

---

## Task 1: Foundation Utilities

**Files:**
- Create: `src/sponge/utils/errors.py`
- Create: `src/sponge/utils/logging.py`

- [ ] **Step 1: Exception hierarchy**

```python
# src/sponge/utils/errors.py
class SpongeError(Exception):
    """Base exception for all Sponge errors."""

class ConfigError(SpongeError):
    """Configuration errors: missing keys, invalid values."""

class ProviderError(SpongeError):
    """LLM provider errors: auth, rate limit, API errors."""

class CacheError(SpongeError):
    """Cache errors: disk full, corruption."""

class BudgetExceededError(SpongeError):
    """Circuit breaker tripped."""
```

- [ ] **Step 2: Structured logging**

```python
# src/sponge/utils/logging.py
import logging
import sys

def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for Sponge."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))
    logging.getLogger("sponge").addHandler(handler)
    logging.getLogger("sponge").setLevel(getattr(logging, level.upper()))
```

- [ ] **Step 3: Run tests — any test that imports these should pass**

---

## Task 2: Config + Pricing Foundation

**Files:**
- Modify: `src/sponge/config/settings.py`
- Create: `src/sponge/cost/models.py`
- Create: `src/sponge/cost/pricing.py`
- Create: `tests/test_pricing.py`

- [ ] **Step 1: Pydantic settings model**

```python
# src/sponge/config/settings.py (replace placeholder)
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model: str = "claude-sonnet-4"
    provider: str = "anthropic"
    budget_per_call: float = 2.00
    budget_per_session: float = 10.00
    max_steps: int = 50
    cache_enabled: bool = True
    cache_ttl_hours: int = 24

    model_config = {"env_prefix": "SPONGE_", "env_file": ".env"}
```

- [ ] **Step 2: Cost models**

```python
# src/sponge/cost/models.py
from dataclasses import dataclass

@dataclass
class ModelPricing:
    input_per_1k: float
    output_per_1k: float
    cache_write_per_1k: float | None = None
    cache_read_per_1k: float | None = None

@dataclass
class Usage:
    tokens_in: int
    tokens_out: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

@dataclass
class CostEntry:
    usage: Usage
    model: str
    cost: float
    naive_cost: float  # what this would cost with no caching

@dataclass
class SavingsLedger:
    entries: list[CostEntry]
    total_actual: float
    total_naive: float
    saved_by_cache: float
```

- [ ] **Step 3: Pricing loader**

`src/sponge/cost/pricing.py` — loads `src/sponge/data/pricing.toml`, returns `ModelPricing` for a given model ID. Must handle missing provider/model gracefully (raise `ConfigError`).

- [ ] **Step 4: Test pricing loader**

`tests/test_pricing.py` — test that pricing.toml loads, valid models return `ModelPricing`, unknown models raise `ConfigError`.

---

## Task 3: LLM Provider Layer

**Files:**
- Create: `src/sponge/llm/base.py`
- Create: `src/sponge/llm/anthropic_provider.py`
- Create: `src/sponge/llm/factory.py`
- Create: `src/sponge/llm/token_counter.py`
- Create: `tests/test_llm_provider.py`
- Create: `tests/mock_provider.py`

- [ ] **Step 1: Write failing LLM tests**

`tests/test_llm_provider.py` — test that:
- `LLMProvider` ABC cannot be instantiated directly.
- `MockProvider` returns a stream of `ContentDelta` events.
- `MockProvider` reports `Usage` at end of stream.
- `ProviderFactory` returns the correct provider class from config.

- [ ] **Step 2: Create mock provider**

```python
# tests/mock_provider.py
from sponge.llm.base import LLMProvider, ContentDelta, UsageEvent, StreamEvent

class MockProvider(LLMProvider):
    async def stream(self, messages, **kwargs):
        yield ContentDelta(text="Hello from mock!")
        yield UsageEvent(usage=Usage(tokens_in=10, tokens_out=5))
```

- [ ] **Step 3: Implement LLM base + Anthropic provider**

`src/sponge/llm/base.py`:
- `Message` dataclass (role, content)
- `StreamEvent` union type: `ContentDelta(text)`, `UsageEvent(usage)`, `ToolCallEvent(...)`
- `LLMProvider` ABC with `async stream(messages, **kwargs) -> AsyncIterator[StreamEvent]`

`src/sponge/llm/anthropic_provider.py`:
- Implements `LLMProvider` using `anthropic.Anthropic` client
- `stream()` yields `ContentDelta` for text_delta events
- `stream()` yields `UsageEvent` from the final `message.usage`
- Reads API key from `ANTHROPIC_API_KEY` env var or config

- [ ] **Step 4: Token counter**

`src/sponge/llm/token_counter.py`:
- `count_tokens(text: str, model: str = "claude-sonnet-4") -> int`
- Uses tiktoken with appropriate encoding per model
- Fallback: approximate as `len(text) // 4` if encoding unknown

- [ ] **Step 5: Provider factory**

`src/sponge/llm/factory.py`:
- `ProviderFactory` reads config, instantiates correct provider
- `create(settings: Settings) -> LLMProvider`
- Supports `anthropic` provider; raises `ConfigError` for unknown

- [ ] **Step 6: Run tests — all LLM tests pass with mock provider**

---

## Task 4: Cost Tracker + Savings Ledger

**Files:**
- Create: `src/sponge/cost/tracker.py`
- Create: `src/sponge/cost/ledger.py`
- Create: `src/sponge/cost/reporter.py`
- Create: `tests/test_cost_tracker.py`

- [ ] **Step 1: Write failing cost tracker tests**

`tests/test_cost_tracker.py`:
- `CostTracker` accumulates usage from multiple stream events.
- `CostTracker` computes actual cost from pricing data.
- `CostTracker` computes naive cost (what it would cost without caching).
- `SavingsLedger` correctly splits savings by source (cache hit).
- `CostReporter` formats output as text and JSON.

- [ ] **Step 2: Implement cost tracker**

`src/sponge/cost/tracker.py`:
- `CostTracker(pricing: ModelPricing)` — initialized with model pricing
- `record_delta(tokens: int)` — called on each `ContentDelta` for streaming output count
- `record_usage(usage: Usage)` — called on `UsageEvent` at end of stream
- `final_cost() -> CostEntry` — returns actual + naive cost

- [ ] **Step 3: Implement savings ledger**

`src/sponge/cost/ledger.py`:
- `SavingsLedger` accumulates `CostEntry` across multiple calls in a session
- `add(entry: CostEntry)` — add one call
- `summary() -> SavingsLedgerSummary` — totals with savings breakdown

- [ ] **Step 4: Implement cost reporter**

`src/sponge/cost/reporter.py`:
- `format_text(ledger: SavingsLedger) -> str` — human-readable output
- `format_json(ledger: SavingsLedger) -> str` — JSON output
- Example text output:
  ```
  Cost: $0.0123 (naive: $0.0150, saved $0.0027 by cache)
  ```

- [ ] **Step 5: Run tests — all pass**

---

## Task 5: Exact Result Cache

**Files:**
- Create: `src/sponge/cache/disk_store.py`
- Create: `src/sponge/cache/result_cache.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: Write failing cache tests**

`tests/test_cache.py`:
- `DiskStore` can `get`/`set`/`delete` keys.
- `ResultCache` returns `None` on cold miss.
- `ResultCache` returns cached response on exact match.
- `ResultCache` misses when repo state marker changes.
- `ResultCache` respects `--no-cache` override.

- [ ] **Step 2: Implement disk store**

`src/sponge/cache/disk_store.py`:
- SQLite-backed key-value store
- `get(key: str) -> str | None`
- `set(key: str, value: str, ttl_hours: int = 24) -> None`
- `delete(key: str) -> None`
- `cleanup_expired() -> None`
- Database at `~/.sponge/cache/store.db`

- [ ] **Step 3: Implement result cache**

`src/sponge/cache/result_cache.py`:
- `ResultCache(store: DiskStore, settings: Settings)`
- `cache_key(task: str, model: str, system_prompt: str, repo_state: str) -> str` — SHA256 of all inputs
- `get(task, model, system_prompt, repo_state) -> str | None`
- `set(task, model, system_prompt, repo_state, response: str) -> None`
- `repo_state()` — captures current git HEAD + dirty flag as state marker

- [ ] **Step 4: Run tests — all pass**

---

## Task 6: Cost Fingerprint + Telemetry

**Files:**
- Create: `src/sponge/telemetry/models.py`
- Create: `src/sponge/telemetry/collector.py`
- Create: `tests/test_telemetry.py`

- [ ] **Step 1: Write failing telemetry tests**

`tests/test_telemetry.py`:
- `TelemetryCollector.log_call()` writes a fingerprint row.
- Fingerprint contains: session_id, task_hash, model, tokens_in, tokens_out, cache_hit, cost, naive_cost, repo_state, provider, timestamp.
- `TelemetryCollector.get_session(session_id)` returns all fingerprints for a session.
- `TelemetryCollector.recent_sessions(limit)` returns recent session summaries.

- [ ] **Step 2: Define fingerprint schema**

`src/sponge/telemetry/models.py`:
```python
@dataclass
class CostFingerprint:
    session_id: str
    task_hash: str
    model: str
    provider: str
    tokens_in: int
    tokens_out: int
    cache_hit: bool
    cost: float
    naive_cost: float
    repo_state: str
    timestamp: str  # ISO-8601
```

- [ ] **Step 3: Implement collector**

`src/sponge/telemetry/collector.py`:
- `TelemetryCollector(db_path: str)` — opens SQLite at `~/.sponge/telemetry/fingerprints.db`
- `log_call(fingerprint: CostFingerprint) -> None` — insert row
- `get_session(session_id: str) -> list[CostFingerprint]`
- `recent_sessions(limit: int = 10) -> list[dict]` — summary stats per session
- Database schema:
  ```sql
  CREATE TABLE IF NOT EXISTS fingerprints (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id TEXT NOT NULL,
      task_hash TEXT NOT NULL,
      model TEXT NOT NULL,
      provider TEXT NOT NULL,
      tokens_in INTEGER NOT NULL,
      tokens_out INTEGER NOT NULL,
      cache_hit INTEGER NOT NULL DEFAULT 0,
      cost REAL NOT NULL,
      naive_cost REAL NOT NULL,
      repo_state TEXT NOT NULL DEFAULT '',
      timestamp TEXT NOT NULL DEFAULT (datetime('now'))
  );
  CREATE INDEX IF NOT EXISTS idx_session ON fingerprints(session_id);
  ```

- [ ] **Step 4: Run tests — all pass**

---

## Task 7: Agent Loop + Core Models

**Files:**
- Create: `src/sponge/core/task.py`
- Create: `src/sponge/core/agent.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: Task models**

`src/sponge/core/task.py`:
```python
@dataclass
class Task:
    prompt: str
    model: str | None = None
    system_prompt: str | None = None

@dataclass
class TaskResult:
    task: Task
    response: str
    cost_entry: CostEntry
    fingerprint: CostFingerprint
    cache_hit: bool
```

- [ ] **Step 2: Write failing agent tests**

`tests/test_agent.py`:
- Agent with mock provider returns `TaskResult` with response text.
- Agent with mock provider records cost.
- Agent with mock provider writes fingerprint.
- Agent with cache hit skips LLM call and returns cached response.

- [ ] **Step 3: Implement agent loop**

`src/sponge/core/agent.py`:
```python
class Agent:
    def __init__(self, provider, cache, tracker_factory, collector):
        ...

    async def run(self, task: Task) -> TaskResult:
        # 1. Check exact cache
        # 2. If hit → return cached (cost: $0)
        # 3. If miss → stream from provider
        # 4. Record cost + savings ledger
        # 5. Write cost fingerprint
        # 6. Write to cache
        # 7. Return TaskResult
```

The loop is ~30 lines. Complexity lives in the infrastructure objects passed in.

- [ ] **Step 4: Run tests — all pass with mock provider**

---

## Task 8: CLI Commands

**Files:**
- Create: `src/sponge/cli/run.py`
- Create: `src/sponge/cli/config_cmd.py`
- Modify: `src/sponge/cli/app.py`
- Create: `tests/test_cli_run.py`

- [ ] **Step 1: Write failing CLI tests**

`tests/test_cli_run.py`:
- `sponge run "hello"` exits 0 and prints response text.
- `sponge run "hello" --json` outputs valid JSON with cost data.
- `sponge run "hello" --no-cache` bypasses cache.
- `sponge run ""` exits non-zero with error message.
- `sponge config show` prints current config.
- `sponge config set model=claude-haiku-3-5` updates config.

- [ ] **Step 2: Implement config command**

`src/sponge/cli/config_cmd.py`:
- `sponge config show` — display current settings
- `sponge config set key=value` — update setting in `~/.sponge/config.toml`
- `sponge config init` — create default config

- [ ] **Step 3: Implement run command**

`src/sponge/cli/run.py`:
- `sponge run <task>` — executes task through agent
- `--model <id>` — override model
- `--json` — JSON output
- `--no-cache` — bypass cache
- `--no-stream` — disable streaming output
- `--verbose` — show debug info

- [ ] **Step 4: Wire up app.py**

Register `run` and `config` commands on the main app.

- [ ] **Step 5: Run tests — CLI tests pass**

---

## Task 9: Benchmark Fixtures

**Files:**
- Create: `tests/fixtures/simple_qa.json`
- Create: `tests/fixtures/repeated_qa.json`
- Create: `tests/fixtures/code_question.json`
- Create: `tests/test_benchmarks.py`

- [ ] **Step 1: Create fixture files**

`simple_qa.json`:
```json
{
  "name": "simple_qa",
  "task": "What is 2+2?",
  "expected_contains": ["4"],
  "expected_max_cost": 0.02
}
```

`repeated_qa.json`:
```json
{
  "name": "repeated_qa",
  "task": "What is the capital of France?",
  "repeat_count": 2,
  "expected_contains": ["Paris"],
  "expected_second_call_cost": 0.0,
  "expected_second_call_cache_hit": true
}
```

`code_question.json`:
```json
{
  "name": "code_question",
  "task": "Write a Python function that returns the Fibonacci sequence up to n.",
  "expected_contains": ["def fib", "return"],
  "expected_max_cost": 0.05
}
```

- [ ] **Step 2: Benchmark test runner**

`tests/test_benchmarks.py`:
- Each fixture is run against mock provider (not real LLM).
- Verifies response contains expected strings.
- Verifies cost is within expected range.
- Verifies cache behavior on repeated tasks.
- These are CI-safe (no API calls) but validate the full pipeline.

- [ ] **Step 3: Run benchmark tests — all pass with mock provider**

---

## Acceptance Criteria

Phase 1 is complete when:

- `sponge run "say hello"` streams output from a configured (or mock) provider.
- Exact cache returns $0 for repeated identical tasks.
- Every call writes a cost fingerprint to SQLite.
- Output includes naive vs actual cost with savings breakdown.
- `sponge config show` displays settings.
- `sponge config set model=X` changes the model.
- All tests pass with mock providers (no API keys required in CI).
- `--run-slow` opt-in flag gates real provider tests.
- 3 benchmark fixtures pass with mock provider.
- Pricing is read from `src/sponge/data/pricing.toml`, never hardcoded.

---

## Planner Review Checklist

- Does the agent loop avoid context compression or plugin routing?
- Does the cost tracker use pricing.toml, not hardcoded values?
- Do cache keys include repo state?
- Does every call emit a cost fingerprint?
- Are tests fast and offline by default?
- Is the savings ledger split by savings source?
