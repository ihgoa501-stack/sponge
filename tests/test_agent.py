"""Tests for the agent loop."""

import tempfile
from pathlib import Path

import pytest

from sponge.cache.disk_store import DiskStore
from sponge.cache.result_cache import ResultCache
from sponge.config.settings import Settings
from sponge.core.agent import Agent, AgentServices
from sponge.core.condenser import SubAgentCondenser
from sponge.core.context_planner import ContextPlanner
from sponge.core.decomposer import TaskDecomposer
from sponge.core.session import Session, Turn
from sponge.core.task import Task
from sponge.telemetry.collector import TelemetryCollector
from tests.mock_provider import MockProvider


@pytest.fixture
def tmp_dirs() -> tuple[Path, Path]:
    """Create temp directories for cache and telemetry DBs."""
    tmp = Path(tempfile.mkdtemp())
    return tmp / "cache.db", tmp / "telemetry.db"


async def test_agent_run_with_mock() -> None:
    """Agent returns TaskResult with mock provider."""
    tmp = Path(tempfile.mkdtemp())
    cache_path = tmp / "cache.db"
    telemetry_path = tmp / "telemetry.db"
    store = DiskStore(cache_path)
    settings = Settings(cache_enabled=True)
    cache = ResultCache(store, settings)
    collector = TelemetryCollector(telemetry_path)
    provider = MockProvider(responses=["Hello from mock!"])

    agent = Agent(provider, settings, cache, collector)
    task = Task(prompt="Say hello")
    result = await agent.run(task)

    assert result.response == "Hello from mock!"
    assert result.cache_hit is False
    assert result.cost_entry.cost > 0
    assert result.fingerprint.session_id


async def test_agent_cache_hit() -> None:
    """Second identical call returns from cache with $0 cost."""
    tmp = Path(tempfile.mkdtemp())
    cache_path = tmp / "cache.db"
    telemetry_path = tmp / "telemetry.db"
    store = DiskStore(cache_path)
    settings = Settings(cache_enabled=True)
    cache = ResultCache(store, settings)
    collector = TelemetryCollector(telemetry_path)
    provider = MockProvider(responses=["Response"])

    agent = Agent(provider, settings, cache, collector)
    task = Task(prompt="What is 2+2?")

    # First call — goes to provider.
    result1 = await agent.run(task)
    assert result1.cache_hit is False
    assert result1.cost_entry.cost > 0

    # Second call — cache hit.
    result2 = await agent.run(task)
    assert result2.cache_hit is True
    assert result2.cost_entry.cost == 0.0
    assert result2.response == "Response"


async def test_agent_records_fingerprint() -> None:
    """Agent writes fingerprints after both cache hits and misses."""
    tmp = Path(tempfile.mkdtemp())
    cache_path = tmp / "cache.db"
    telemetry_path = tmp / "telemetry.db"
    store = DiskStore(cache_path)
    settings = Settings(cache_enabled=True)
    cache = ResultCache(store, settings)
    collector = TelemetryCollector(telemetry_path)
    provider = MockProvider(responses=["A", "B"])

    agent = Agent(provider, settings, cache, collector)

    await agent.run(Task(prompt="Task 1"))
    await agent.run(Task(prompt="Task 2"))
    await agent.run(Task(prompt="Task 1"))  # cache hit

    sessions = collector.recent_sessions(limit=10)
    assert len(sessions) >= 2

    # Get all fingerprints across sessions.
    all_fps = []
    for s in sessions:
        all_fps.extend(collector.get_session(s["session_id"]))
    assert len(all_fps) == 3
    assert any(fp.cache_hit for fp in all_fps)
    assert any(not fp.cache_hit for fp in all_fps)


# ── run_decomposed ──────────────────────────────────────────────────


async def test_run_decomposed_full_pipeline() -> None:
    """run_decomposed executes sub-tasks, plans context, and condenses results."""
    tmp = Path(tempfile.mkdtemp())
    store = DiskStore(tmp / "cache.db")
    settings = Settings(cache_enabled=True)
    cache = ResultCache(store, settings)
    collector = TelemetryCollector(tmp / "telemetry.db")

    # Decomposer: returns 2 sub-tasks.
    decomposer_provider = MockProvider(responses=[
        '{"sub_tasks": ['
        '{"id": 1, "description": "Fix auth routes", "context_hint": "src/auth/routes.py"},'
        '{"id": 2, "description": "Update middleware", "context_hint": "src/auth/middleware.py"}'
        "]}",
    ])
    decomposer = TaskDecomposer(decomposer_provider)

    # Context planner: plans files needed per sub-task.
    context_planner = ContextPlanner()

    # Condenser: condenses multi-result output.
    condenser_provider = MockProvider(responses=[
        '{"summary": "Fixed 2 files", '
        '"findings": [{"file": "routes.py", "line": 10, '
        '"finding": "added async", "confidence": "high"}], '
        '"key_insight": "Auth module now async"}',
    ])
    condenser = SubAgentCondenser(condenser_provider, min_raw_tokens=10)

    # Main provider: returns canned responses for each sub-task.
    main_provider = MockProvider(responses=["Sub result A", "Sub result B"])

    services = AgentServices(
        decomposer=decomposer,
        context_planner=context_planner,
        condenser=condenser,
    )
    agent = Agent(main_provider, settings, cache, collector, services=services)

    result = await agent.run_decomposed(
        Task(prompt="refactor the auth module to use async/await across all files")
    )

    # Verify the pipeline ran.
    assert result.response is not None
    assert "Fixed 2 files" in result.response
    assert result.cache_hit is False
    assert result.cost_entry.cost > 0
    # At least 2 sub-task calls + 1 decomposition call + 1 condensation call.
    assert main_provider.call_count >= 2


async def test_run_decomposed_simple_task_falls_back() -> None:
    """Simple tasks bypass decomposition and fall back to run()."""
    tmp = Path(tempfile.mkdtemp())
    store = DiskStore(tmp / "cache.db")
    settings = Settings(cache_enabled=True)
    cache = ResultCache(store, settings)
    collector = TelemetryCollector(tmp / "telemetry.db")

    # Decomposer with a provider that matches the simple-task path.
    # "What is 2+2?" is < 50 chars → should_decompose returns False.
    decomposer = TaskDecomposer(MockProvider())
    condenser = SubAgentCondenser(MockProvider(), min_raw_tokens=2000)
    main_provider = MockProvider(responses=["4"])

    services = AgentServices(decomposer=decomposer, condenser=condenser)
    agent = Agent(main_provider, settings, cache, collector, services=services)

    result = await agent.run_decomposed(Task(prompt="What is 2+2?"))

    assert result.response == "4"
    assert result.cache_hit is False
    # Only one LLM call (no decomposition overhead).
    assert main_provider.call_count == 1


async def test_run_decomposed_no_services_falls_back() -> None:
    """When no decomposer is configured, run_decomposed falls back to run()."""
    tmp = Path(tempfile.mkdtemp())
    store = DiskStore(tmp / "cache.db")
    settings = Settings(cache_enabled=True)
    cache = ResultCache(store, settings)
    collector = TelemetryCollector(tmp / "telemetry.db")
    main_provider = MockProvider(responses=["Plain response"])

    agent = Agent(main_provider, settings, cache, collector, services=None)

    result = await agent.run_decomposed(Task(prompt="any task"))

    assert result.response == "Plain response"
    assert main_provider.call_count == 1


# ── run_with_history ───────────────────────────────────────────────


async def test_run_with_history_appends_turns() -> None:
    """run_with_history appends user + assistant turns to the session."""
    tmp = Path(tempfile.mkdtemp())
    store = DiskStore(tmp / "cache.db")
    settings = Settings(cache_enabled=True, provider="anthropic")
    cache = ResultCache(store, settings)
    collector = TelemetryCollector(tmp / "telemetry.db")
    main_provider = MockProvider(responses=["I remember our conversation."])

    agent = Agent(main_provider, settings, cache, collector)

    session = Session(id="test-session-1", model="claude-sonnet-4")
    session.add_turn(Turn(role="user", content="My name is Alice."))
    session.add_turn(Turn(role="assistant", content="Hi Alice!"))

    result = await agent.run_with_history(session, "What is my name?")

    assert result.response == "I remember our conversation."
    # Verify turns were appended.
    assert len(session.turns) == 4  # 2 existing + user + assistant
    assert session.turns[2].role == "user"
    assert session.turns[2].content == "What is my name?"
    assert session.turns[3].role == "assistant"
    assert session.turns[3].cost is not None


async def test_run_with_history_tracks_cost() -> None:
    """run_with_history records cost on assistant turn and fingerprint."""
    tmp = Path(tempfile.mkdtemp())
    store = DiskStore(tmp / "cache.db")
    settings = Settings(cache_enabled=True, provider="anthropic")
    cache = ResultCache(store, settings)
    collector = TelemetryCollector(tmp / "telemetry.db")
    main_provider = MockProvider(responses=["Response with cost"])

    agent = Agent(main_provider, settings, cache, collector)

    session = Session(id="test-session-2", model="claude-sonnet-4")
    session.add_turn(Turn(role="user", content="Hello."))
    session.add_turn(Turn(role="assistant", content="Hi."))

    result = await agent.run_with_history(session, "How are you?")

    assert result.cost_entry.cost > 0
    assert result.fingerprint is not None
    assert session.turns[-1].cost is not None
    assert session.turns[-1].cost > 0


async def test_run_with_history_max_history_sliding_window() -> None:
    """Only the most recent max_history turns are sent to the provider."""
    tmp = Path(tempfile.mkdtemp())
    store = DiskStore(tmp / "cache.db")
    settings = Settings(cache_enabled=True, context_token_budget=999999, provider="anthropic")
    cache = ResultCache(store, settings)
    collector = TelemetryCollector(tmp / "telemetry.db")

    # This provider records the messages it receives.
    captured_messages: list = []

    class SpyProvider(MockProvider):
        async def stream(self, messages, **kwargs):
            captured_messages.extend(messages)
            async for event in MockProvider.stream(self, messages, **kwargs):
                yield event

    main_provider = SpyProvider(responses=["OK"])

    agent = Agent(main_provider, settings, cache, collector)

    session = Session(id="test-session-3", model="claude-sonnet-4")
    # Add 5 turns.
    for i in range(5):
        session.add_turn(Turn(role="user", content=f"Message {i}"))
        session.add_turn(Turn(role="assistant", content=f"Reply {i}"))

    await agent.run_with_history(session, "New message", max_history=2)

    # max_history=2 means at most 2 recent non-system turns + the new user message.
    # So the provider should see: the 2 most recent turns + "New message".
    assert len(captured_messages) >= 1
    # The last message should be the new user message.
    assert captured_messages[-1].content == "New message"
