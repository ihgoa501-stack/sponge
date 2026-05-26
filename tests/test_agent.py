"""Tests for the agent loop."""

import tempfile
from pathlib import Path

import pytest

from sponge.cache.disk_store import DiskStore
from sponge.cache.result_cache import ResultCache
from sponge.config.settings import Settings
from sponge.core.agent import Agent
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
