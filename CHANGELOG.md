# Changelog

All notable changes to Sponge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0-dev] — Unreleased

### Added

- **Agent core**: ~30-line async loop with plugin → cache → LLM execution paths
- **3 LLM providers**: Anthropic (Claude), OpenAI (GPT-4o), DeepSeek (V3/R1) — all with streaming
- **Exact result cache**: SHA256(task + model + git HEAD) → SQLite, $0 repeated calls
- **Semantic cache**: Jaccard similarity ≥ 0.7, SQLite-persisted, LRU eviction
- **Cost tracking**: streaming incremental cost, per-call CostEntry, SavingsLedger
- **Cost fingerprint**: every call logged to SQLite (session, tokens, cache hit, cost, repo state)
- **Self-tuning loop**: 3 signal detectors → shadow A/B testing → Mann-Whitney U → auto-apply
- **3 built-in plugins**: FileOps (read/list/write/delete), Search (grep/ripgrep), Shell (sandboxed)
- **Plugin routing**: priority-ordered plugin registry, approval levels (ALLOW/CONFIRM/REJECT)
- **MCP integration**: MCPClient (JSON-RPC stdio), MCPPlugin adapter
- **Task decomposition**: LLM-driven complex task → sub-tasks
- **Sub-agent condensation**: exploration output → structured JSON summary (10-100× compression)
- **Progressive context loading**: per-subtask context planning with deduplication
- **Context compression**: 5-layer pipeline (mask → prune → summarize → slide)
- **Project memory**: `.sponge/memory.toml` injected as system prompt, CLI management
- **Multi-turn sessions**: JSONL persistence, save/resume, history compression
- **Approval system**: agent-level gate for plugin operations, `--auto-approve` flag
- **Subprocess sandbox**: timeout, output cap, cwd restriction
- **Retry utility**: exponential backoff for LLM calls, Ctrl+C graceful interrupt
- **Structured logging**: `setup_logging()` wired into CLI and `python -m sponge`
- **CLI**: 7 commands, 18 subcommands — run, session, config, tune, memory, cost, version
- **Cost CLI**: `sponge cost session`, `total --days`, `stats` with cache hit rates
- **Pricing data**: versioned `pricing.toml`, never hardcoded
- **106 tests**: full coverage with MockProvider, zero real API calls in normal test runs
