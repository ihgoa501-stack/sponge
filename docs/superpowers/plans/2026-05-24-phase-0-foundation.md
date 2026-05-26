# Phase 0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repository installable, testable, lintable, and ready for feature agents.

**Architecture:** Phase 0 creates only development infrastructure and CLI skeleton behavior. No LLM calls, cache logic, agent loop, or runtime cost accounting should be implemented here.

**Tech Stack:** Python 3.12+, Typer, pytest, pytest-asyncio, ruff, mypy, GitHub Actions.

---

## Scope

Allowed:

- Packaging, CLI app skeleton, test scaffolding, CI, pre-commit, `.gitignore`.
- Minimal `sponge --version` behavior.

Not allowed:

- Provider integrations.
- Agent loop.
- Caching.
- Telemetry.
- File editing tools.

## Files

- Create: `src/sponge/cli/app.py`
- Create: `tests/test_cli_version.py`
- Create: `tests/conftest.py`
- Create: `.github/workflows/ci.yml`
- Create: `.pre-commit-config.yaml`
- Modify: `src/sponge/__main__.py`
- Modify: `pyproject.toml`
- Modify: `.gitignore`

## Task 1: CLI App Skeleton

**Files:**

- Create: `src/sponge/cli/app.py`
- Modify: `src/sponge/__main__.py`
- Test: `tests/test_cli_version.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_cli_version.py` with tests that assert:

- Typer app imports successfully.
- `sponge --version` exits with status 0.
- Version output contains `0.1.0-dev`.

Required test shape:

```python
from typer.testing import CliRunner

from sponge import __version__
from sponge.cli.app import app


def test_cli_version() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.output
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
pytest tests/test_cli_version.py -v
```

Expected before implementation: import error for `sponge.cli.app`.

- [ ] **Step 3: Implement minimal CLI app**

Create `src/sponge/cli/app.py` with:

- `typer.Typer` app object.
- `--version` callback.
- No `run` command yet.

Required public symbol:

```python
app
```

- [ ] **Step 4: Keep module entry point simple**

`src/sponge/__main__.py` must import `app` and call it. It should not parse args manually.

- [ ] **Step 5: Run test and verify it passes**

Run:

```bash
pytest tests/test_cli_version.py -v
```

Expected: 1 passed.

## Task 2: Test and Typecheck Foundation

**Files:**

- Create: `tests/conftest.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add empty shared test fixture file**

Create `tests/conftest.py` with a module docstring only. This reserves a stable location for later mock providers and temp config fixtures.

- [ ] **Step 2: Confirm pytest discovers tests**

Run:

```bash
pytest -v
```

Expected: all current tests pass.

- [ ] **Step 3: Confirm ruff runs**

Run:

```bash
ruff check .
```

Expected: no lint errors.

- [ ] **Step 4: Confirm mypy runs**

Run:

```bash
mypy src
```

Expected: no type errors.

## Task 3: Repository Hygiene

**Files:**

- Modify: `.gitignore`
- Create: `.pre-commit-config.yaml`
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Update `.gitignore`**

It must ignore:

- Python bytecode and caches.
- virtual environments.
- coverage artifacts.
- build artifacts.
- local Sponge runtime data: `.sponge/`.
- local environment files: `.env`.

- [ ] **Step 2: Add pre-commit config**

Include hooks for:

- ruff check with auto-fix.
- ruff format.
- basic whitespace/end-of-file hygiene.

- [ ] **Step 3: Add CI workflow**

Create `.github/workflows/ci.yml` that runs on push and pull request:

- install package with dev extras.
- run `ruff check .`.
- run `ruff format --check .`.
- run `mypy src`.
- run `pytest`.

- [ ] **Step 4: Run local verification**

Run:

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

Expected: all pass.

## Acceptance Criteria

Phase 0 is complete only when:

- `python -m sponge --version` works.
- `sponge --version` works after `pip install -e .`.
- `pytest`, `ruff check`, `ruff format --check`, and `mypy src` pass.
- CI workflow exists.
- No runtime feature beyond version printing is implemented.

## Planner Review Checklist

- Does the CLI skeleton avoid pretending Sponge can run tasks?
- Are tests fast and offline?
- Did the worker avoid touching unrelated docs or architecture?
- Is the repository ready for Phase 1 agents?
