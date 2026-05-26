"""Benchmark tests — validate the full pipeline against fixtures.

These tests use MockProvider — no real API calls. They verify that:
- Responses contain expected strings.
- Costs stay within expected ranges.
- Cache behavior works on repeated tasks.
"""

import json
import tempfile
from pathlib import Path

from sponge.cache.disk_store import DiskStore
from sponge.cache.result_cache import ResultCache
from sponge.config.settings import Settings
from sponge.core.agent import Agent
from sponge.core.task import Task
from sponge.telemetry.collector import TelemetryCollector
from tests.mock_provider import MockProvider


def _load_fixture(name: str) -> dict:
    path = Path(__file__).parent / "fixtures" / name
    return json.loads(path.read_text())


async def _make_agent() -> Agent:
    tmp = Path(tempfile.mkdtemp())
    store = DiskStore(tmp / "cache.db")
    settings = Settings(cache_enabled=True)
    cache = ResultCache(store, settings)
    collector = TelemetryCollector(tmp / "telemetry.db")
    provider = MockProvider(responses=["The answer is 4."])
    return Agent(provider, settings, cache, collector)


async def test_simple_qa_fixture() -> None:
    """Simple Q&A fixture: response contains expected answer."""
    fixture = _load_fixture("simple_qa.json")
    agent = await _make_agent()
    agent._provider = MockProvider(responses=["The answer is 4."])  # type: ignore[assignment]

    result = await agent.run(Task(prompt=fixture["task"]))

    for expected in fixture["expected_contains"]:
        assert expected in result.response
    assert result.cost_entry.cost <= fixture["expected_max_cost"]


async def test_repeated_qa_fixture() -> None:
    """Repeated Q&A: second call hits cache with $0 cost."""
    fixture = _load_fixture("repeated_qa.json")
    agent = await _make_agent()
    agent._provider = MockProvider(responses=["The capital of France is Paris."])  # type: ignore[assignment]

    task = Task(prompt=fixture["task"])

    # First call — from provider.
    result1 = await agent.run(task)
    assert not result1.cache_hit
    assert result1.cost_entry.cost > 0
    for expected in fixture["expected_contains"]:
        assert expected in result1.response

    # Second call — cache hit.
    result2 = await agent.run(task)
    assert result2.cache_hit == fixture["expected_second_call_cache_hit"]
    assert result2.cost_entry.cost == fixture["expected_second_call_cost"]


async def test_code_question_fixture() -> None:
    """Code question: response contains expected code patterns."""
    fixture = _load_fixture("code_question.json")
    agent = await _make_agent()
    fib_code = (
        "def fib(n):\n"
        "    a, b = 0, 1\n"
        "    result = []\n"
        "    for _ in range(n):\n"
        "        result.append(a)\n"
        "        a, b = b, a + b\n"
        "    return result"
    )
    agent._provider = MockProvider(responses=[fib_code])  # type: ignore[assignment]

    result = await agent.run(Task(prompt=fixture["task"]))

    for expected in fixture["expected_contains"]:
        assert expected in result.response
    assert result.cost_entry.cost <= fixture["expected_max_cost"]
