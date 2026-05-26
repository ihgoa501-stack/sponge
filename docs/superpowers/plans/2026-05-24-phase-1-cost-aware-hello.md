# Phase 1 Cost-Aware Hello Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `sponge run "say hello"` as a single streamed model call with usage and cost reporting.

**Architecture:** Build the accounting spine first: typed stream events, provider abstraction, usage model, pricing model, cost tracker, and a minimal agent loop. Tests use mock providers; real provider calls are opt-in and must not run in CI.

**Tech Stack:** Python 3.12+, async iterators, Typer, Rich, Pydantic or dataclasses, pytest-asyncio.

---

## Scope

Allowed:

- Single-turn `sponge run TASK`.
- Mock provider for tests.
- One real provider adapter behind optional dependency if API key exists.
- Usage and cost reporting.

Not allowed:

- Tool calls.
- File edits.
- Caching.
- Session persistence.
- Self-tuning.

## Files

- Create: `src/sponge/llm/base.py`
- Create: `src/sponge/llm/mock_provider.py`
- Create: `src/sponge/llm/factory.py`
- Create: `src/sponge/cost/models.py`
- Create: `src/sponge/cost/tracker.py`
- Create: `src/sponge/cost/reporter.py`
- Create: `src/sponge/core/agent.py`
- Create: `src/sponge/core/task.py`
- Create: `src/sponge/cli/run.py`
- Modify: `src/sponge/cli/app.py`
- Test: `tests/unit/test_cost_models.py`
- Test: `tests/unit/test_cost_tracker.py`
- Test: `tests/unit/test_llm_base.py`
- Test: `tests/integration/test_run_command.py`

## Public Interfaces

Implement these concepts with stable names:

```python
class Message:
    role: str
    content: str
```

```python
class Usage:
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0
    cache_write_input_tokens: int = 0
```

```python
class ContentDelta:
    text: str
```

```python
class UsageEvent:
    usage: Usage
```

```python
StreamEvent = ContentDelta | UsageEvent
```

```python
class LLMProvider:
    model: str
    async def stream(self, messages: list[Message]) -> AsyncIterator[StreamEvent]: ...
```

```python
class ModelPricing:
    model: str
    input_per_million: Decimal
    output_per_million: Decimal
    cache_read_input_per_million: Decimal | None
    cache_write_input_per_million: Decimal | None
```

```python
class CostEntry:
    model: str
    usage: Usage
    cost_usd: Decimal
```

```python
class CostSummary:
    total_cost_usd: Decimal
    input_tokens: int
    output_tokens: int
```

## Task 1: Cost Models

**Files:**

- Create: `src/sponge/cost/models.py`
- Test: `tests/unit/test_cost_models.py`

- [ ] **Step 1: Write failing cost tests**

Tests must cover:

- Standard input/output token pricing.
- Cache read tokens use cache read price when present.
- Decimal output rounds only for display, not internal arithmetic.

Example test:

```python
from decimal import Decimal

from sponge.cost.models import ModelPricing, Usage, price_usage


def test_price_usage_standard_tokens() -> None:
    pricing = ModelPricing(
        model="mock/expensive",
        input_per_million=Decimal("10.00"),
        output_per_million=Decimal("30.00"),
        cache_read_input_per_million=Decimal("1.00"),
        cache_write_input_per_million=Decimal("12.50"),
    )
    usage = Usage(input_tokens=1000, output_tokens=500)

    cost = price_usage(pricing, usage)

    assert cost == Decimal("0.025")
```

- [ ] **Step 2: Implement minimal cost model**

`price_usage()` must calculate:

- standard input tokens at `input_per_million`.
- output tokens at `output_per_million`.
- cache read/write tokens at their specific prices when available.

- [ ] **Step 3: Run tests**

Run:

```bash
pytest tests/unit/test_cost_models.py -v
```

Expected: all pass.

## Task 2: Stream Event Abstraction and Mock Provider

**Files:**

- Create: `src/sponge/llm/base.py`
- Create: `src/sponge/llm/mock_provider.py`
- Test: `tests/unit/test_llm_base.py`

- [ ] **Step 1: Write failing stream test**

Test that `MockLLMProvider.stream()` emits:

- at least one `ContentDelta`.
- exactly one final `UsageEvent`.
- configured usage values.

- [ ] **Step 2: Implement base event types**

Use dataclasses or Pydantic models. Keep them provider-agnostic.

- [ ] **Step 3: Implement mock provider**

`MockLLMProvider` should accept:

- `model: str`
- `text: str`
- `usage: Usage`

It should stream text in small chunks and then emit `UsageEvent`.

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/unit/test_llm_base.py -v
```

Expected: all pass.

## Task 3: Cost Tracker and Reporter

**Files:**

- Create: `src/sponge/cost/tracker.py`
- Create: `src/sponge/cost/reporter.py`
- Test: `tests/unit/test_cost_tracker.py`

- [ ] **Step 1: Write failing tracker tests**

Tests must assert:

- Recording one `UsageEvent` creates one `CostEntry`.
- Summary aggregates tokens and cost.
- Unknown model raises a clear configuration error.

- [ ] **Step 2: Implement tracker**

`CostTracker` should:

- be initialized with a pricing table.
- expose `record(model: str, usage: Usage) -> CostEntry`.
- expose `summary() -> CostSummary`.

- [ ] **Step 3: Implement reporter**

Reporter should output a compact string containing:

- model.
- total cost.
- input tokens.
- output tokens.

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/unit/test_cost_tracker.py -v
```

Expected: all pass.

## Task 4: Minimal Agent Loop

**Files:**

- Create: `src/sponge/core/task.py`
- Create: `src/sponge/core/agent.py`
- Test: `tests/integration/test_agent_single_turn.py`

- [ ] **Step 1: Write failing integration test**

Test `Agent.run("say hello")` with `MockLLMProvider`:

- returns the streamed text.
- records cost.
- does not call tools.

- [ ] **Step 2: Implement Task and TaskResult**

`TaskResult` must include:

- `text: str`
- `cost_summary: CostSummary`
- `model: str`

- [ ] **Step 3: Implement Agent**

The loop is one provider stream for now:

- Build messages from task.
- Consume `ContentDelta` into output buffer.
- Pass `UsageEvent` to `CostTracker`.
- Return `TaskResult`.

- [ ] **Step 4: Run integration test**

Run:

```bash
pytest tests/integration/test_agent_single_turn.py -v
```

Expected: all pass.

## Task 5: `sponge run`

**Files:**

- Create: `src/sponge/cli/run.py`
- Modify: `src/sponge/cli/app.py`
- Create: `src/sponge/llm/factory.py`
- Test: `tests/integration/test_run_command.py`

- [ ] **Step 1: Write failing CLI test**

Test:

```bash
sponge run "say hello" --model mock
```

Expected output contains:

- mock response text.
- `Cost:`.
- model name.

- [ ] **Step 2: Implement provider factory**

For Phase 1, factory must support:

- `mock` provider always.
- real provider only if explicitly requested and configured.

- [ ] **Step 3: Implement run command**

Typer command accepts:

- `TASK` argument.
- `--model`.
- `--json`.
- `--no-stream`.

`--json` must emit valid JSON containing:

- `text`
- `model`
- `cost.total_cost_usd`
- `cost.input_tokens`
- `cost.output_tokens`

- [ ] **Step 4: Run CLI tests**

Run:

```bash
pytest tests/integration/test_run_command.py -v
```

Expected: all pass.

## Acceptance Criteria

Phase 1 is complete only when:

- `sponge run "say hello" --model mock` works offline.
- Real model execution, if implemented, is opt-in and skipped without API keys.
- Every response path returns a `CostSummary`.
- No cache or tool features are introduced.
- `pytest`, `ruff check .`, and `mypy src` pass.

## Planner Review Checklist

- Is cost accounting impossible to bypass in the run path?
- Are mock tests deterministic and offline?
- Does JSON output expose enough structure for later automation?
- Does the code avoid provider-specific assumptions in core classes?
