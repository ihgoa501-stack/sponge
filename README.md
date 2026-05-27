# Sponge 🧽

[![PyPI version](https://img.shields.io/pypi/v/sponge-ai)](https://pypi.org/project/sponge-ai/)
[![CI](https://github.com/ihgoa501-stack/sponge/actions/workflows/ci.yml/badge.svg)](https://github.com/ihgoa501-stack/sponge/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Same model. Same quality. 1/10 the tokens.**

Sponge is an **architecture-level cost compression harness** for LLM agents. It doesn't switch you to cheaper models or bolt on caching as an afterthought. Every layer — task decomposition, context loading, sub-agent results, memory — is designed from first principles to slash token consumption. Same model quality, dramatically lower cost.

---

## Quick Start

```bash
pip install sponge-ai[deepseek]       # or [anthropic] or [openai] or [openrouter]
export SPONGE_DEEPSEEK_API_KEY=sk-...  # or SPONGE_ANTHROPIC_API_KEY etc.
sponge run "explain the CAP theorem in one sentence"
```

---

## How It Saves Tokens

| Layer | What It Does | Cost |
|-------|-------------|------|
| **Plugin Routing** | File ops, code search, shell commands → handled locally | $0 |
| **Exact Cache** | Identical tasks return cached result (SHA256 match) | $0 |
| **Semantic Cache** | Similar tasks match via Jaccard similarity | $0 |
| **Self-Tuning** | Detects waste (TTL too short, budget too loose) → proposes fixes | 5-20% |
| **Context Compression** | Old conversation turns summarized, not re-sent | 2-5× |
| **Task Decomposition** | Complex tasks split into focused sub-tasks | 5-10× |
| **LLM Call** | Only when nothing else works | Full price |

---

## Commands

```bash
sponge run "task"          # Execute a task
  --model, -m MODEL        # Override the model
  --json                   # JSON output
  --auto-approve           # Allow write/delete/shell operations

sponge benchmark           # Run benchmark fixtures against a real provider
  --fixture, -f NAME       # Run a single fixture
  --output, -o FILE.json   # Save results

sponge cost session        # Cost breakdown for latest session
sponge cost total --days 30 # Total cost over N days
sponge cost stats          # Overall efficiency statistics

sponge tune report         # Detect optimization opportunities
sponge tune apply ID       # Activate a tuning proposal
sponge tune review         # Evaluate active experiments

sponge session start       # Start a multi-turn conversation
sponge session chat "msg"  # Send a message
sponge session resume ID   # Resume a saved session
sponge session list        # List all sessions

sponge memory add "rule"   # Add project convention
sponge memory list         # List all conventions
sponge memory remove N     # Remove a convention

sponge config show         # Show current configuration
sponge config set KEY=VAL  # Change a setting

sponge --version           # Show version
```

---

## Supported Providers

| Provider | Install | Env Var |
|----------|---------|---------|
| Anthropic (Claude) | `[anthropic]` | `SPONGE_ANTHROPIC_API_KEY` |
| OpenAI (GPT-4o) | `[openai]` | `SPONGE_OPENAI_API_KEY` |
| DeepSeek (V4) | `[deepseek]` | `SPONGE_DEEPSEEK_API_KEY` |
| OpenRouter (200+ models) | `[openrouter]` | `SPONGE_OPENROUTER_API_KEY` |

Switch via `SPONGE_PROVIDER` env var or `sponge config set provider=deepseek`.

---

## Project Memory

Create `.sponge/memory.toml` in your project root (or use `sponge memory add`):

```toml
[memory]
rules = [
    "Never modify tests/fixtures/ without asking",
    "Use httpx instead of requests",
]
```

These are injected into every LLM call as system instructions.

---

## Cost Transparency

Every LLM call is logged to `~/.sponge/telemetry/fingerprints.db`:

```bash
sponge cost stats
# Sponge Efficiency Stats
#   Total calls:      42
#   Cache hits:       23 (55%)
#   Plugin calls:     8 ($0)
#   LLM calls:        11
#   Total cost:       $0.002347
#   Naive cost:       $0.005120
#   Total saved:      $0.002773 (54.2%)
```

---

## Development

```bash
git clone https://github.com/ihgoa501-stack/sponge.git
cd sponge
pip install -e ".[dev]"
pytest                  # 157 tests, zero API calls required
ruff check src/         # lint
mypy src/sponge/        # type check
```

---

## License

MIT
