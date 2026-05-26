# Contributing to Sponge

Thanks for your interest! Sponge is a cost-first AI agent harness, and every contribution should reflect that ethos — **efficient, focused, high-leverage**.

---

## Quick Start

```bash
# Clone & install
git clone https://github.com/yourname/sponge
cd sponge
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Verify
sponge --version
pytest
```

---

## Development Philosophy

### Cost-First Mindset

- **Every line of code has a token cost** — if Sponge itself uses an LLM call, that call must be as compressed as the calls it orchestrates.
- **Measure everything** — new features must include a "savings vs naive" metric. If you add a compression layer, prove it compresses.
- **Cache aggressively** — before adding a new LLM call, ask: can this be cached? Can it be routed to a plugin?

### Quality Principles

| Principle | Why |
|-----------|-----|
| Type hints everywhere | Cost of catching bugs at runtime is higher than at type-check time |
| Async-first | Blocking I/O in hot paths burns wall time and token budget |
| Minimal dependencies | Every dep adds attack surface and bloat — prefer stdlib |
| Fail-open for optional features | Local preprocessor down? Pass through, don't crash |

---

## Code Style

This project uses:

- **Ruff** for formatting and linting (replaces black + flake8 + isort)
- **mypy** for type checking (strict mode)
- **pytest** + **pytest-asyncio** for testing

```bash
# Run all checks before committing
ruff check src/
ruff format --check src/
mypy src/ --strict
pytest
```

Conventions:

- **Naming:** `snake_case` for functions/methods, `PascalCase` for classes, `UPPER_CASE` for constants
- **Imports:** stdlib → third-party → local (sections separated by blank line)
- **Line length:** 100 characters
- **Docstrings:** Google style for public APIs; omit for trivial private methods

---

## Testing

### Test Layers

| Layer | What | Cost Awareness |
|-------|------|---------------|
| **Unit** | Token counting, cache logic, cost math | Free — no LLM calls |
| **Integration** | Plugin registry, context pipeline, session persistence | Mock LLM endpoints — never pay for test calls |
| **Benchmark** | Cost-per-task vs Claude Code / Copilot / Cursor | Compare against naive baseline; CI must see positive savings |

### Guidelines

- **Never make real LLM calls in tests** — mock at the provider boundary.
- Every compression feature needs a ratio assertion: `assert compression_ratio >= 1.5`.
- Cache tests must verify HIT returns identical result and MISS falls through.
- Budget/circuit-breaker tests should verify it blocks at threshold AND allows just under.

---

## Pull Request Process

1. **Pick a phase.** See [ROADMAP.md](ROADMAP.md) — each phase has clear deliverables.
2. **Open an issue first** for non-trivial changes (unless it's a Phase 0 task).
3. **Branch naming:** `phase-N-short-description` (e.g. `phase-1-core-loop`).
4. **Keep PRs atomic** — one phase deliverable per PR. A working end-to-end is better than a perfect 80%.
5. **Include tests** — if you add a module, it needs a test file.
6. **Include metrics** — for compression/cache features, add benchmark results to the PR description.
7. **CI must pass** — lint, typecheck, tests, and benchmarks.

### PR Checklist

```markdown
- [ ] Code follows style guide (ruff + mypy clean)
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] Benchmark shows positive savings (for compression/cache features)
- [ ] Documentation updated (docstrings + relevant .md)
- [ ] Changelog entry in `CHANGELOG.md`
```

---

## Architecture Overview

The source is in `src/sponge/`. Key modules:

| Module | Responsibility |
|--------|---------------|
| `core/` | Agent loop, task models, context pipeline, session lifecycle |
| `llm/` | Provider-agnostic LLM abstraction (Anthropic, OpenAI, factory) |
| `cost/` | Token/cost accounting, budget enforcement, circuit breaker |
| `cache/` | Multi-level cache (exact match, semantic, prompt cache management) |
| `plugins/` | Plugin ABC, registry, built-in zero-cost plugins, sub-agents |
| `sandbox/` | Isolated code execution (Docker, E2B, subprocess) |
| `config/` | Pydantic settings, TOML + env var config loading |
| `telemetry/` | Self-tuning infrastructure (collector, analyzer, feedback, tuner) |
| `cli/` | Typer CLI commands |
| `utils/` | Logging, errors, retry helpers |

See [docs/architecture.md](docs/architecture.md) for the full picture.

---

## Questions?

Open a [GitHub Discussion] or ask in the project's chat. Keep it cost-efficient — search existing issues first.
