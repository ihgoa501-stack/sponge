> ⚠️ **Draft** — Streaming is implemented in Phase 1 as part of the agent loop. The detailed design here describes features planned for Phase 3+. See [project-plan.md](project-plan.md).

# Streaming Responses — Interactive Latency

> A blocking `llm.chat()` architecture hides latency behind a 30-second loading spinner. Sponge streams by default — characters appear as the model generates them, and the cost tracker accrues incrementally.

---

## Architecture: Two-Level Pipeline

Streaming operates at two levels:

```
Level 1 (hot path — required):
  LLM stream → SSE frames → CLI/TUI render
  Cost tracker: incremental output token accrual
  Circuit breaker: "check during stream" mode

Level 2 (cool path — optional):
  Long-running sub-agent → its own SSE stream
  Multiple sub-agent streams → parent agent consolidates → single user-facing stream
```

---

## Level 1: LLM Stream

### Provider Stream Interface

Every `LLMProvider` implements a single streaming method:

```python
@dataclass
class StreamEvent:
    type: Literal["text", "tool_call", "usage", "error", "done"]

@dataclass
class ContentDelta(StreamEvent):
    type: "text"
    text: str

@dataclass
class ToolCallEvent(StreamEvent):
    type: "tool_call"
    name: str
    input: dict
    id: str

@dataclass
class UsageEvent(StreamEvent):
    type: "usage"
    tokens_in: int
    tokens_out: int
    cache_hit: bool
    cache_write: bool

class LLMProvider(ABC):
    @abstractmethod
    async def stream(self, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        ...
```

### Core Loop Integration

```python
async for event in llm.stream(messages):
    match event:
        case ContentDelta(text=text):
            render(text)                              # immediate display
            output_tokens += count_tokens(text)        # incremental count

        case ToolCallEvent(name=name, input=input):
            if approval_gate.ok(name, input):           # approval check
                result = await execute_tool(name, input)
                messages.append(result)
            else:
                messages.append(ToolResult(id=id, error="Rejected by user"))

        case UsageEvent(tokens_in, tokens_out, ...):
            cost_tracker.record(tokens_in, tokens_out)  # final tally
            cache.write(messages, response)              # cache update
```

### Cost Tracking During Streaming

**Challenge:** Output token count is unknown until the stream ends.

**Solution:** Incremental costing with mid-stream circuit breaker:

```python
class StreamingCostTracker:
    cumulative_output_tokens: int = 0
    estimated_output_cost: float = 0.0

    def on_token(self, text: str, model_pricing: ModelPricing):
        tokens = count_tokens(text)
        self.cumulative_output_tokens += tokens
        self.estimated_output_cost += tokens * model_pricing.output_per_token

    def should_terminate(self, budget_remaining: float) -> bool:
        """Check mid-stream whether to abort."""
        return self.estimated_output_cost > budget_remaining * 0.8  # 80% warning
```

If the stream runs away, the circuit breaker can abort mid-generation — a capability impossible in a blocking architecture.

---

## Level 2: Sub-Agent Streaming

Sub-agents produce their own streams. The parent agent needs to consolidate multiple streams into one coherent output.

### Sub-Agent Stream Lifecycle

```
sponge run "refactor this large project"
  │
  ├─ Agent classifies: needs sub-agents for analysis + implementation
  │
  ├─ spawn SubAgent("analyze")           ───┐
  │     stream: ContentDelta              ←──┤
  │     stream: ToolCallEvent             ←──┤
  │     stream: ContentDelta              ←──┤
  │     stream: UsageEvent                ←──┤
  │     ...                                ←──┤
  │     stream: DoneEvent                 ←──┤
  │                                          │
  ├─ spawn SubAgent("implement")          ───┤
  │     ...                                ←──┤
  │     stream: DoneEvent                 ←──┤
  │                                          │
  └─ Parent consolidates:
       "Analysis: [sub-agent 1 summary]
        Implementation: [sub-agent 2 summary]
        Total cost: $0.42"
```

### Stream Merging Strategy

| Strategy | When | Behavior |
|----------|------|----------|
| **Sequential** | Default | Wait for sub-agent A to complete, then start B. Simple, predictable. |
| **Parallel with interleaving** | Independent subtasks | Show output from both A and B as they arrive, labeled `[analyze]` / `[implement]`. |
| **Parallel with condensation** | Both produce too much text | Show a progress indicator, then emit condensed summaries when each finishes. |

### Sub-Agent Stream → Condensed Result

The sub-agent's full stream is **not** forwarded to the best model. Only the condensed result (summary + key findings) is appended to the parent's message list. This is the same condensation mechanism described in the main architecture — streaming doesn't change it.

---

## CLI Rendering

Level 1 streaming maps directly to the terminal:

| Event | TUI Rendering |
|-------|---------------|
| `ContentDelta` | Append text to current line |
| `ToolCallEvent` | Show collapsible block: `🔧 git diff (expand for details)` |
| `ToolResult` | Show result inline or collapsible |
| `UsageEvent` | Line footer: `⏱ 3.2s · $0.018` |
| `ApprovalGate` | `❓ Approve: write to src/main.py? [Y/n]` (blocks stream until answer) |

Non-TUI mode (pipelines, CI) disables interactive elements:

```bash
# Non-interactive: auto-approve, plain text
sponge run "lint the project" --no-stream --auto-approve
```

---

## Impact on Compression Pipeline

Streaming changes when compression happens:

| Before (blocking) | After (streaming) |
|-------------------|-------------------|
| Compress ALL messages before call | Compress input messages before stream starts |
| Compress again on next turn | Compress again on next turn (unchanged) |
| N/A | Mid-stream: no compression (output is actively being generated) |

**Layer-specific streaming behavior:**

| Layer | Streaming Impact |
|-------|-----------------|
| L1: Server-side clear | Unchanged — applied before stream starts |
| L2: Observation masking | Unchanged — applied before stream starts |
| L3: Message pruning | Unchanged — applied before stream starts |
| L4: LLM summarization | Unchanged — applied before stream starts |
| L5: Sliding window | Unchanged — applied before stream starts |
| **Cost estimator** | Now only predicts **input** cost. Output cost is accrued mid-stream. |
| **Circuit breaker** | Gains mid-stream abort capability (not possible in blocking mode) |

---

## Provider Compatibility

| Provider | Streaming Support | Notes |
|----------|------------------|-------|
| Anthropic | ✅ `messages.stream()` | SSE with content block deltas |
| OpenAI | ✅ `stream=True` | Chat completion chunks |
| DeepSeek | ✅ OpenAI-compatible | Same as OpenAI |
| Ollama (local) | ✅ SSE | Used only for preprocessing, not main model |

All major providers support streaming. The `LLMProvider` ABC enforces a single `stream()` method — no separate `chat()` path. If a future provider doesn't support streaming, the base class provides a fallback that buffers the full response and emits it as a single `ContentDelta`.

---

## Regression: Blocking Mode

Streaming is the default, but blocking mode is available:

| Flag | Behavior | Use Case |
|------|----------|----------|
| `--stream` (default) | Characters appear in real-time | Interactive terminal use |
| `--no-stream` | Wait for full response, then print | CI/CD, pipe to file, non-interactive |

Blocking mode uses the same `stream()` method internally — it just buffers events and emits them as a single block. This keeps the provider interface unified.
