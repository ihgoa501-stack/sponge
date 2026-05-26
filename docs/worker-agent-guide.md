# Worker Agent Guide

> This guide is for implementation agents. Read it before touching runtime code. It keeps independent agents aligned with the Sponge product thesis.

## One-Sentence Mission

Build a cost-learning coding agent harness: every successful run should leave behind data that makes future runs cheaper without silently downgrading the final reasoning model.

## What Sponge Can Eventually Do

Yes, Sponge is intended to write code. It should become a coding-capable agent harness comparable in workflow shape to Codex, Claude Code, Cursor agents, and OpenHands, with one major difference: Sponge treats cost compression as infrastructure.

Coding capability arrives in stages:

| Stage | Capability | User-Facing Meaning |
|-------|------------|---------------------|
| Phase 1 | Single model call | Sponge can answer coding questions, but cannot safely inspect or edit projects yet. |
| Phase 2 | Savings ledger + exact cache | Repeated coding questions can be answered from cache when state is compatible. |
| Phase 3 | Context compression | Multi-turn coding conversations send fewer paid tokens. |
| Phase 4 | File/search plugins + approval | Sponge can inspect code locally and perform approved file edits. |
| Phase 5 | Sessions + fingerprints | Sponge can resume coding tasks and produce replayable cost records. |
| Phase 8 | Sub-agent condensation | Sponge can search/review larger codebases while sending condensed evidence to the main model. |

Until Phase 4 write tools exist, Sponge is not a practical code-writing agent. It is only a cost-aware conversational CLI.

## Non-Negotiable Product Rules

- The final answer model must not be silently downgraded.
- Helper executors may be local or cheaper, but only for preprocessing, retrieval, summarization, validation, or condensation.
- Normal tests must not call real LLM APIs.
- Every model call path must eventually emit usage/cost data.
- Every cache hit must explain why it is valid.
- Any write, delete, shell execution, network action, or package install must go through approval policy.
- Provider pricing must be data-driven and easy to update.
- Savings claims must be backed by measured ledger data or marked as estimates.

## Required Reading By Phase

| Phase | Required Docs |
|-------|---------------|
| 0 | `docs/project-plan.md`, `ROADMAP.md`, `pyproject.toml` |
| 1 | `docs/architecture.md`, `docs/streaming.md`, `docs/cost-model.md`, `docs/cli-reference.md` |
| 2 | `docs/project-plan.md`, `docs/cost-model.md`, `docs/test-plan.md` |
| 3 | `docs/context-pipeline.md`, `docs/risk-assessment.md` |
| 4 | `docs/security.md`, `docs/mcp-integration.md`, `docs/cli-reference.md` |
| 5+ | `docs/self-tuning.md`, `docs/memory.md`, `docs/risk-assessment.md` |

## Handoff Contract

Each worker task must finish with:

- Code changes scoped to the task files.
- Tests added before or alongside implementation.
- `pytest` for the touched area.
- `ruff check` and `mypy` when feasible.
- A short note describing cost-accounting implications.
- No unrelated refactors.

## Shared Data Concepts

All implementation agents should use these names consistently:

- `Usage`: raw provider token usage.
- `CostEntry`: one priced operation.
- `CostSummary`: aggregate spend for a run/session.
- `SavingsLedger`: actual vs naive cost plus savings by source.
- `CostFingerprint`: replayable explanation of why a run cost what it cost.
- `ProviderCapabilities`: what a model provider supports.
- `StreamEvent`: typed event emitted by an LLM provider.

If a worker agent needs a different name, it must update this guide and the relevant phase plan in the same task.
