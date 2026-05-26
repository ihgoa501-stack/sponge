"""Tests for telemetry collector and cost fingerprints."""

import tempfile
from pathlib import Path

from sponge.telemetry.collector import TelemetryCollector
from sponge.telemetry.models import CostFingerprint


def _make_fingerprint(
    session_id: str = "sess-001",
    task_hash: str = "abc123",
    model: str = "claude-sonnet-4",
    provider: str = "anthropic",
    tokens_in: int = 100,
    tokens_out: int = 50,
    cache_hit: bool = False,
    cost: float = 0.01,
    naive_cost: float = 0.01,
) -> CostFingerprint:
    return CostFingerprint(
        session_id=session_id,
        task_hash=task_hash,
        model=model,
        provider=provider,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cache_hit=cache_hit,
        cost=cost,
        naive_cost=naive_cost,
        repo_state="abc1234",
        timestamp="2026-05-24T12:00:00Z",
    )


def test_log_and_retrieve_fingerprint() -> None:
    """Fingerprint written to DB can be retrieved."""
    with tempfile.TemporaryDirectory() as tmp:
        collector = TelemetryCollector(Path(tmp) / "fp.db")
        fp = _make_fingerprint()
        collector.log_call(fp)

        results = collector.get_session("sess-001")
        assert len(results) == 1
        assert results[0].task_hash == "abc123"
        assert results[0].model == "claude-sonnet-4"
        assert results[0].cache_hit is False


def test_multiple_fingerprints_per_session() -> None:
    """Multiple calls in one session are all retrievable."""
    with tempfile.TemporaryDirectory() as tmp:
        collector = TelemetryCollector(Path(tmp) / "fp.db")
        collector.log_call(_make_fingerprint(task_hash="task-1"))
        collector.log_call(_make_fingerprint(task_hash="task-2"))
        collector.log_call(_make_fingerprint(task_hash="task-3"))

        results = collector.get_session("sess-001")
        assert len(results) == 3
        assert {r.task_hash for r in results} == {"task-1", "task-2", "task-3"}


def test_recent_sessions() -> None:
    """Recent sessions returns summary stats."""
    with tempfile.TemporaryDirectory() as tmp:
        collector = TelemetryCollector(Path(tmp) / "fp.db")
        collector.log_call(_make_fingerprint(session_id="sess-a", cost=1.0, naive_cost=2.0))
        collector.log_call(_make_fingerprint(session_id="sess-a", cost=3.0, naive_cost=4.0))
        collector.log_call(_make_fingerprint(session_id="sess-b", cost=5.0, naive_cost=5.0))

        sessions = collector.recent_sessions(limit=10)
        assert len(sessions) == 2

        sess_a = [s for s in sessions if s["session_id"] == "sess-a"][0]
        assert sess_a["calls"] == 2
        assert sess_a["total_cost"] == 4.0
        assert sess_a["total_naive"] == 6.0


def test_cache_hit_fingerprint() -> None:
    """Cache-hit flag is correctly stored."""
    with tempfile.TemporaryDirectory() as tmp:
        collector = TelemetryCollector(Path(tmp) / "fp.db")
        collector.log_call(_make_fingerprint(cache_hit=True, cost=0.0, naive_cost=0.01))
        collector.log_call(_make_fingerprint(cache_hit=False, cost=0.01, naive_cost=0.01))

        results = collector.get_session("sess-001")
        assert results[0].cache_hit is True
        assert results[0].cost == 0.0
        assert results[1].cache_hit is False
