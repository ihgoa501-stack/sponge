# Sponge — CLAUDE.md

## Project Identity
- **Mission**: Build the most cost-effective AI agent, competing with Claude Codex, Cursor, and similar tools.
- **Core principle**: Minimize LLM cost per task while maximizing output quality. Every design decision should be justified by cost-efficiency.
- **Name metaphor**: Like a sponge — absorb knowledge and context efficiently, squeeze out maximum value per token.

## Development Guidelines

### Cost-First Mindset
- Prefer cheaper model tiers for routine operations; reserve expensive reasoning models only when genuinely needed.
- Implement caching aggressively (prompt caching, context caching, result caching) to reduce API spend.
- Batch operations where possible to minimize API calls.
- Log and monitor token usage per operation; surface cost metrics in the UX.

### Tech Stack (defaults)
- Language: Python 3.12+
- Runtime: asyncio for concurrent operations
- LLM SDK: anthropic (for Claude), with provider-agnostic abstraction layer
- CLI framework: click or typer
- Testing: pytest with asyncio support

### Code Style
- Type hints everywhere.
- Async-first; avoid blocking I/O in hot paths.
- Keep dependencies minimal — every dependency adds attack surface and bloat.
- Prefer stdlib over third-party packages where feasible.

### Architecture
- Provider-agnostic LLM interface: support swapping models/providers without changing task logic.
- Token accounting: track and report cost per run, per task, per session.
- Sandboxed execution: run untrusted code in isolated sandboxes.
- Plugin system: allow cost-efficient sub-agents for specialized tasks.

### Testing
- Unit test token/cost accounting logic.
- Integration tests should mock LLM endpoints (don't waste money on test calls).
- Benchmark tests comparing cost-per-task against Claude Codex / Cursor.

### Git Conventions
- Commits should be atomic and have descriptive messages in English.
- Branch from main, PR back to main.
- Keep CI fast — slow CI burns money too.
