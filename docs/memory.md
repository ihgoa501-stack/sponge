# Memory & Multimodal Input

> Two previously unaddressed dimensions: **cross-session memory** so Sponge doesn't repeat mistakes, and **multimodal input** so it isn't blind to screenshots, diagrams, and PDFs.

---

## Long-Term Memory

### The Problem

Without memory, every session starts blank:

- Session 1: "Don't touch the test fixtures." → Agent touches test fixtures.
- Session 2: "Don't touch the test fixtures." → Agent touches them again.
- Users waste tokens repeating themselves. The best model wastes context re-learning project conventions.

### Three-Layer Memory Model

| Layer | Scope | Storage | Injected Into | Example |
|-------|-------|---------|---------------|---------|
| **Session** | Single conversation | `~/.sponge/sessions/<id>.jsonl` | N/A (turn history) | "Earlier you said to use httpx" |
| **Project** | Current project | `<project>/.sponge/memory.toml` | System prompt | "Never touch test/fixtures/" |
| **User** | All projects | `~/.sponge/preferences.toml` | System prompt | "Default model = Opus 4.7" |

### Project Memory (`.sponge/memory.toml`)

Analogous to Claude Code's `CLAUDE.md` or Cursor's `.cursorrules`:

```toml
[project]
name = "sponge"
description = "Cost-optimal AI agent harness"

[rules]
# Conventions the agent should follow
no_touch = "Never modify test/fixtures/ directory"
http_lib = "Use httpx, not requests"
imports = "stdlib → third-party → local (sections separated by blank line)"
line_length = 100

[preferences]
# User-specific overrides for this project
model = "claude-opus-4-7"
budget_ceiling = "P95"
auto_approve = false
```

**How it works:**

1. At session start, `memory/injector.py` reads `<project>/.sponge/memory.toml`
2. Injects rules into the system prompt as structured context
3. Agent can suggest additions to memory.toml (with confirmation)
4. User can edit memory.toml directly (it's plain TOML)

**Agent-initiated memory writes:**

```
User: "From now on, don't use requests, use httpx."
Agent: "Got it. Add this to project memory? [Y/n]"
  → Y → Appends to .sponge/memory.toml:
      [rules]
      http_lib = "Use httpx, not requests"
```

### User Preferences (`~/.sponge/preferences.toml`)

Applied across all projects:

```toml
[defaults]
model = "claude-opus-4-7"
budget_ceiling = "P95"
sandbox = "docker"
stream = true
auto_approve = false

[plugins]
# Default approval tiers per plugin (merged with project-level config)
file_ops.write_file = "confirm"
shell.exec = "confirm"

[mcp]
# MCP servers available everywhere
github = { command = "npx", args = ["-y", "@modelcontextprotocol/server-github"] }
```

### Conflicts & Resolution

When project and user memory conflict, **project wins**:

| Setting | User (global) | Project (local) | Resolution |
|---------|--------------|-----------------|------------|
| `model` | `gpt-5.5` | `claude-opus-4-7` | ✅ Project wins |
| `budget_ceiling` | `P50` | `P95` | ✅ Project wins |
| `auto_approve` | `true` | Not set | ✅ User fallback |

Session overrides (`--auto-approve`, `--read-only`) win over both.

---

## Multimodal Input

### The Problem

Real development involves more than text:

- A screenshot of a bug → "Why is this button misaligned?"
- A PDF spec → "Implement this API"
- A diagram → "Build this architecture"
- A video recording → "What's causing this flicker?"

A text-only harness is blind to all of these.

### Content Block Model

The `Message` model supports heterogeneous content blocks:

```python
@dataclass
class ContentBlock:
    type: Literal["text", "image", "pdf", "tool_use", "tool_result"]
    text: str | None = None
    image_url: str | None = None   # base64 data URI ("data:image/png;base64,...")
    pdf_url: str | None = None     # base64 data URI (for providers that support PDF)
    source: FileSource | None = None

@dataclass
class FileSource:
    path: str                      # auto-encode from file path
    mime_type: str                 # image/png, application/pdf, ...
    size_bytes: int

@dataclass
class Message:
    role: Literal["user", "assistant", "tool"]
    content: list[ContentBlock]
```

### Provider Support

| Provider | Image | PDF | Notes |
|----------|-------|-----|-------|
| Anthropic Claude | ✅ | ✅ | PDF requires base64, max 100MB |
| OpenAI GPT-5.5 | ✅ | ✅ | PDF via `file` parameter |
| DeepSeek | ❌ | ❌ | Text only — images routed to sub-agent |

### CLI Usage

```bash
# Screenshot
sponge run "what's wrong with this UI?" --image screenshot.png

# PDF spec
sponge run "implement this API spec" --file spec.pdf

# Multiple files
sponge run "review these changes" --image before.png --image after.png

# Drag-and-drop (TUI mode)
# User drags image onto terminal → auto-encoded as content block
```

### Cost Impact

Images are expensive in token terms:

| Image Size | Approx Token Cost (Claude) | Cost at Opus 4.7 |
|-----------|---------------------------|------------------|
| 100x100 (icon) | ~150 tokens | ~$0.002 |
| 800x600 (screenshot) | ~800 tokens | ~$0.012 |
| 1920x1080 (full screen) | ~1,600 tokens | ~$0.024 |
| PDF (10 pages) | ~2,000 tokens | ~$0.030 |

### Multimodal Compression

The context pipeline gains a multimodal-aware compression layer:

```
Before compression:
  [User text] "What's wrong?"                          ← 50 tokens
  [Image] screenshot.png                               ← 1,600 tokens
  [Assistant] "Analysis with annotations..."           ← 800 tokens
  [User text] "And now fix it"                         ← 20 tokens
  [Image] screenshot2.png                              ← 1,400 tokens

After compression (L2 observation masking):
  [User text] "What's wrong?"                          ← 50 tokens
  [Image] screenshot.png                               ← 1,600 tokens (last 3 → keep)
  [Assistant] "Analysis with annotations..."           ← 800 tokens
  [User text] "And now fix it"                         ← 20 tokens
  [Image] [omitted — 1,400 tokens saved]               ← 30 tokens

After aggressive compression (L3 pruning):
  [User text] "What's wrong?"                          ← 50 tokens
  [Image] screenshot.png                               ← 1,600 tokens (keep: most recent image)
  [Assistant] "Analysis..."                            ← 800 tokens
  [User text] "And now fix it"                         ← 20 tokens
```

**Compression rules for multimodal content:**

| Rule | Rationale |
|------|-----------|
| Keep the most recent image from each user turn | User might reference it |
| Drop images before text in pruning order | Text is more compressible |
| Mark omitted images with `[image omitted — N tokens]` | Model knows something was there |
| Never omit images from the first user turn | Task definition often includes visuals |
| Never omit images fewer than 3 turns ago | Model may still reference them |

### Multimodal Caching

Images and PDFs are content-addressed by SHA256:

```
cache_key = SHA256(image_data + preceding_text)
```

If the same image is referenced in a future session (e.g., daily screenshot of a dashboard), the cache returns the previous analysis at zero cost.

---

## Implementation Phases

| Phase | Memory | Multimodal |
|-------|--------|------------|
| Phase 1-6 | Session-only (turn history) | Text-only |
| Phase 7 | Session save/resume | File attachment via CLI flags |
| Phase 8 | Project memory (`.sponge/memory.toml`) | Image support (Anthropic) |
| Phase 9 | User preferences | PDF support |
| Phase 10 | Agent-initiated memory writes | Multimodal compression tuning |
| Phase 11 | Self-tuning memory TTLs | Embedding-based image caching |
