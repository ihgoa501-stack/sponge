> ⚠️ **Draft** — Context compression is a Phase 3+ commodity feature. This document will be updated when prioritized. See [project-plan.md](project-plan.md) for current phase strategy.

# Context Pipeline — 5-Layer Compression

> Every token sent to the best model is scrutinized. The context pipeline runs **before every call**, asking: *"How few tokens can we send and still get the same quality?"*

---

## Why a Pipeline?

A single compression strategy is brittle. Masking alone misses summarization opportunities; summarization alone is too expensive to run every turn. The 5-layer pipeline applies increasingly aggressive strategies in order, stopping when the context fits within budget:

```
Full context → Layer 1: Clear → Layer 2: Mask → Layer 3: Prune
               → Layer 4: Summarize → Layer 5: Slide → Compressed messages
```

Each layer is **optional and independently configurable**. If Layer 2 reduces context enough, Layers 3-5 are skipped entirely.

---

## Layer 1 — Server-Side Tool Result Clearing

**Mechanism:** Anthropic API headers `clear_tool_uses_20250919` and `clear_thinking_20251015`.

**What it does:** Instructs the Anthropic API to discard tool result blocks and thinking blocks server-side before they count toward the prompt cache or input token tally.

**Cost:** $0 (API-native feature, no client-side processing).

**Rules:**
- Always applied when using Anthropic provider.
- Keeps only the latest tool result visible to the model.
- Old tool uses are stripped server-side — the model gets a cleaner context window for free.

---

## Layer 2 — Observation Masking

**Mechanism:** Replace old tool result content with a short placeholder.

**What it does:** For tool outputs and user messages exceeding `masking_threshold` tokens, replaces the content body with:

```
[...N tokens of tool output omitted...]
```

**Claimed saving:** 52% cost reduction, +2.6% solve rate (JetBrains Research, cited but not independently verified).

**Rules:**
- ✅ **ONLY** mask tool messages and user messages
- ❌ **NEVER** mask assistant reasoning content (removes signal the model needs)
- Keep last **3** tool results intact — the model needs current context to continue
- Configurable threshold (default 2000 tokens, self-tuned by telemetry)

**Why it works:** Older tool outputs (file reads, search results, command output) are bulky but rarely referenced after the immediate next turn. The model doesn't need to read them again; the placeholder signals "something happened here."

---

## Layer 3 — Message Pruning

**Mechanism:** Score-based turn selection.

**What it does:** Assigns an importance score to each turn based on heuristics:

| Signal | Score Modifier | Rationale |
|--------|---------------|-----------|
| Recent turn | +2 per recency rank | Recent context matters more |
| Contains error | +3 | Error context is critical |
| Contains reasoning | +2 | Model's own reasoning is high-signal |
| Contains user message | +1 | User intent must be preserved |
| Clean success (tool) | -1 | Low signal after the fact |

**Rules:**
- Always keep minimum **5 turns** (configurable, default 5).
- Drop lowest-scoring turns first.
- Never drop the first user message (task definition).

---

## Layer 4 — LLM Summarization

**Mechanism:** External cheap model compresses history.

**What it does:** When masking + pruning are insufficient AND the conversation has ≥10 turns with ≥3 turns remaining after pruning, a cheap model (DeepSeek V4-Flash at $0.14/MTok, or local Ollama) summarizes the oldest surviving turns into <300 tokens.

**Constraints:**
- Only triggers when strictly necessary — summarization costs tokens to produce.
- The summary replaces the original turns in the message list.
- The best model sees: `[summary of turns 1-7]` + `[turn 8 intact]` + `[turn 9 intact]`.
- Prefer Anthropic's server-side beta compaction API where available (zero client-side cost).
- Fall back to OpenAI / DeepSeek / Ollama.

---

## Layer 5 — Sliding Window

**Mechanism:** Hard context floor.

**What it does:** Ensures the message list never exceeds the model's context window. Always preserves:

1. System prompt (highest priority — defines agent behavior)
2. Last N turns (where N is computed as `max_turns = floor(context_window / avg_tokens_per_turn)`)
3. Any cached blocks (retained via prompt caching headers)

**Cache integration:** When using Anthropic's `prompt_cache_retention` headers, the sliding window marks system prompt + tool definitions + recent turns as cacheable. Extended context is served from cache at 10% of input cost.

---

## Configuration & Tuning

All Layer 2-5 parameters are self-tuned via the telemetry system:

| Parameter | Default | Self-Tuned By | Effect |
|-----------|---------|---------------|--------|
| `masking_threshold` | 2000 tokens | Compression ratio → raise/lower | Controls how aggressively tool outputs are masked |
| `pruning_min_turns` | 5 | Context utilization → adjust | Minimum history preserved when pruning |
| `summarization_trigger` | ≥10 turns | Compression needs → tighten/relax | When to invoke Layer 4 |
| `summary_target_tokens` | 300 | Sub-agent cost analysis | Target size of compressed summaries |

**Self-tuning logic (simplified):**
- If compression ratio < 1.2× → raise masking threshold (be more aggressive)
- If compression ratio > 3× → lower masking threshold (may be over-masking)
- If sessions consistently stay under 92% context → relax pruning
- If edge cases require context that was aggressively pruned → tighten pruning

---

## Example: Compression in Action

```
Before compression (4 turns, ~12,800 tokens):
  [System] Tools, rules, persona              ← 2,400 tokens
  [User] "Refactor this file"                 ← 120 tokens
  [Tool] file_read result (full file)         ← 5,100 tokens
  [Assistant] "Here's my plan..."             ← 1,800 tokens
  [Tool] shell cmd output (build log)         ← 2,300 tokens
  [Assistant] "Now let me apply changes..."   ← 1,080 tokens

After compression (~5,100 tokens, ratio 2.5×):
  [System] Tools, rules, persona              ← 2,400 tokens (cached, 10% cost)
  [User] "Refactor this file"                 ← 120 tokens
  [Tool] [...5,100 tokens of file omitted...] ← 40 tokens (Layer 2 masked)
  [Assistant] "Here's my plan..."             ← 1,800 tokens
  [Tool] [...2,300 tokens omitted...]         ← 40 tokens (Layer 2 masked)
  [Assistant] "Now let me apply changes..."   ← 1,080 tokens

Cost at Opus 4.7: $0.51 → $0.24 (53% reduction before cache savings)
```

---

## Testing Requirements

Every compression feature must include:

1. **Pre/post token ratio assertion:** `assert compression_ratio >= 1.5`
2. **Semantic preservation test:** Verify the compressed context still produces correct answers (use known-truth prompts)
3. **Edge case tests:** Empty history, single turn, extremely long tool outputs, maximum pruning
