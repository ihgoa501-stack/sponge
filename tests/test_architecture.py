"""Tests for architecture modules: decomposer, condenser, context planner."""

from sponge.core.condenser import SubAgentCondenser
from sponge.core.context_planner import ContextPlanner
from sponge.core.decomposer import TaskDecomposer
from tests.mock_provider import MockProvider

# ── Decomposer ─────────────────────────────────────────────────────


def test_decomposer_should_not_decompose_simple() -> None:
    """Simple tasks should not be decomposed."""
    decomposer = TaskDecomposer(MockProvider())
    assert not decomposer.should_decompose("hello")
    assert not decomposer.should_decompose("What is 2+2?")


def test_decomposer_should_decompose_complex() -> None:
    """Complex tasks with keywords should be decomposed."""
    decomposer = TaskDecomposer(MockProvider())
    assert decomposer.should_decompose(
        "refactor the auth module to use async/await across all files in src/auth/"
    )
    assert decomposer.should_decompose(
        "implement user registration, login, logout, and password reset"
    )


async def test_decomposer_simple_task_bypasses() -> None:
    """Simple task returns as single sub-task without decomposition."""
    decomposer = TaskDecomposer(MockProvider())
    result = await decomposer.decompose("What is 2+2?")
    assert not result.was_decomposed
    assert len(result.sub_tasks) == 1
    assert result.sub_tasks[0].description == "What is 2+2?"


async def test_decomposer_complex_task() -> None:
    """Complex task is broken into sub-tasks."""
    json_response = (
        '{"sub_tasks": ['
        '{"id": 1, "description": "Add async to routes", "context_hint": "src/auth/routes.py"},'
        '{"id": 2, "description": "Update middleware", "context_hint": "src/auth/middleware.py"}'
        "]}"
    )
    decomposer = TaskDecomposer(MockProvider(responses=[json_response]))
    result = await decomposer.decompose("refactor the auth module to use async/await everywhere")
    assert result.was_decomposed
    assert len(result.sub_tasks) == 2


# ── Condenser ───────────────────────────────────────────────────────


def test_condenser_should_not_condense_short() -> None:
    """Short outputs should not be condensed (overhead > benefit)."""
    condenser = SubAgentCondenser(MockProvider(), min_raw_tokens=2000)
    assert not condenser.should_condense("short output")


def test_condenser_should_condense_long() -> None:
    """Long outputs should be condensed."""
    condenser = SubAgentCondenser(MockProvider(), min_raw_tokens=2000)
    long_output = "word " * 600  # ~600 words → ~2400 chars
    assert condenser.should_condense(long_output)


async def test_condenser_compresses_output() -> None:
    """Condenser compresses exploration into structured findings."""
    condenser = SubAgentCondenser(
        MockProvider(
            responses=[
                (
                    '{"summary": "Found 3 issues", '
                    '"findings": [{"file": "a.py", "line": 10, '
                    '"finding": "bug", "confidence": "high"}], '
                    '"key_insight": "Fix a.py first"}'
                )
            ]
        ),
        min_raw_tokens=200,
    )
    raw = "word " * 100  # 100 words → small but above min threshold
    result = await condenser.condense(raw)

    assert result.summary == "Found 3 issues"
    assert len(result.findings) == 1
    assert result.findings[0].file == "a.py"
    assert result.compression_ratio > 0


# ── Context Planner ─────────────────────────────────────────────────


def test_context_planner_extracts_paths() -> None:
    """Paths are extracted from description and context hints."""
    planner = ContextPlanner()
    plan = planner.plan(1, "fix bug in 'src/auth/routes.py'", "also check `tests/test_auth.py`")
    paths = {item.path for item in plan.needed}
    assert "src/auth/routes.py" in paths
    assert "tests/test_auth.py" in paths


def test_context_planner_skips_loaded() -> None:
    """Already-loaded paths are not re-planned."""
    planner = ContextPlanner()
    planner.mark_loaded(["src/auth/routes.py"])

    plan = planner.plan(2, "fix 'src/auth/routes.py' and 'src/main.py'")
    assert "src/auth/routes.py" in plan.already_loaded
    needed = {item.path for item in plan.needed}
    assert "src/auth/routes.py" not in needed
    assert "src/main.py" in needed


def test_context_planner_truncates_at_budget() -> None:
    """Plans exceeding budget are truncated."""
    planner = ContextPlanner(max_context_per_task=5)
    # Create many paths.
    paths = " ".join(f"'file{i}.py'" for i in range(20))
    plan = planner.plan(1, f"check {paths}")
    assert len(plan.needed) <= 10
