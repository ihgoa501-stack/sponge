"""Tests for signal detectors."""

import sqlite3
from datetime import UTC, datetime, timedelta

from sponge.config.settings import Settings
from sponge.telemetry.analyzer import (
    BudgetSlackDetector,
    CacheGapDetector,
    TaskRepeatDetector,
    all_detectors,
)


def _make_fingerprints_db(rows: list[tuple]) -> sqlite3.Connection:
    """Create an in-memory DB with synthetic fingerprints."""
    db = sqlite3.connect(":memory:")
    db.execute("""
        CREATE TABLE fingerprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            task_hash TEXT NOT NULL,
            model TEXT NOT NULL,
            provider TEXT NOT NULL,
            tokens_in INTEGER NOT NULL,
            tokens_out INTEGER NOT NULL,
            cache_hit INTEGER NOT NULL DEFAULT 0,
            cost REAL NOT NULL,
            naive_cost REAL NOT NULL,
            repo_state TEXT NOT NULL DEFAULT '',
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            experiment_id TEXT,
            experiment_group TEXT
        )
    """)
    for row in rows:
        db.execute(
            """INSERT INTO fingerprints
               (session_id, task_hash, model, provider,
                tokens_in, tokens_out, cache_hit, cost, naive_cost,
                repo_state, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            row,
        )
    db.commit()
    return db


def _ts(minutes_ago: int) -> str:
    """Return ISO timestamp for N minutes ago."""
    return (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()


def _settings(**kwargs: object) -> Settings:
    s = Settings()
    for k, v in kwargs.items():
        setattr(s, k, v)
    return s


# ── CacheGapDetector tests ────────────────────────────────────────


def test_cache_gap_no_signal_when_gap_small() -> None:
    """No proposal when gap < TTL."""
    db = _make_fingerprints_db(
        [
            ("s1", "a1", "m", "p", 10, 5, 0, 0.01, 0.01, "", _ts(10)),
            ("s1", "a2", "m", "p", 10, 5, 0, 0.01, 0.01, "", _ts(5)),
        ]
    )
    detector = CacheGapDetector()
    proposals = detector.detect(db, _settings(cache_ttl_hours=24))
    assert proposals == []


def test_cache_gap_detects_large_gap() -> None:
    """Proposal when gap > TTL."""
    # Two calls 120 min apart, TTL = 1 hour (60 min)
    db = _make_fingerprints_db(
        [
            ("s1", "a1", "m", "p", 10, 5, 0, 0.01, 0.01, "", _ts(130)),
            ("s1", "a2", "m", "p", 10, 5, 0, 0.01, 0.01, "", _ts(10)),
        ]
    )
    detector = CacheGapDetector()
    proposals = detector.detect(db, _settings(cache_ttl_hours=1, tune_window_days=30))
    assert len(proposals) == 1
    assert proposals[0].param == "cache_ttl_hours"
    assert proposals[0].proposed > 1
    assert proposals[0].risk == "low"


# ── BudgetSlackDetector tests ─────────────────────────────────────


def test_budget_slack_no_signal_when_tight() -> None:
    """No proposal when actual spend is close to budget."""
    db = _make_fingerprints_db(
        [
            ("s1", "a1", "m", "p", 10, 5, 0, 8.0, 8.0, "", _ts(10)),
            ("s2", "a2", "m", "p", 10, 5, 0, 9.0, 9.0, "", _ts(5)),
            ("s3", "a3", "m", "p", 10, 5, 0, 7.0, 7.0, "", _ts(0)),
        ]
    )
    detector = BudgetSlackDetector()
    proposals = detector.detect(db, _settings(budget_per_session=10.0))
    assert proposals == []


def test_budget_slack_detects_slack() -> None:
    """Proposal when median spend << budget."""
    db = _make_fingerprints_db(
        [
            ("s1", "a1", "m", "p", 10, 5, 0, 2.0, 2.0, "", _ts(10)),
            ("s2", "a2", "m", "p", 10, 5, 0, 1.0, 1.0, "", _ts(5)),
            ("s3", "a3", "m", "p", 10, 5, 0, 3.0, 3.0, "", _ts(0)),
        ]
    )
    detector = BudgetSlackDetector()
    proposals = detector.detect(db, _settings(budget_per_session=10.0))
    assert len(proposals) == 1
    assert proposals[0].param == "budget_per_session"
    assert proposals[0].proposed < 10.0
    assert proposals[0].risk == "medium"


# ── TaskRepeatDetector tests ──────────────────────────────────────


def test_task_repeat_no_signal_when_few_repeats() -> None:
    """No proposal with < 3 repeats."""
    db = _make_fingerprints_db(
        [
            ("s1", "abc123", "m", "p", 10, 5, 0, 0.01, 0.01, "", _ts(10)),
            ("s2", "abc123", "m", "p", 10, 5, 0, 0.01, 0.01, "", _ts(5)),
        ]
    )
    detector = TaskRepeatDetector()
    proposals = detector.detect(db, _settings())
    assert proposals == []


def test_task_repeat_detects_repeats() -> None:
    """Proposal when task repeats with misses over a long span."""
    db = _make_fingerprints_db(
        [
            ("s1", "abc123", "m", "p", 10, 5, 0, 0.01, 0.01, "", _ts(1500)),  # 25h ago
            ("s2", "abc123", "m", "p", 10, 5, 0, 0.01, 0.01, "", _ts(1000)),  # ~17h ago
            ("s3", "abc123", "m", "p", 10, 5, 0, 0.01, 0.01, "", _ts(500)),  # ~8h ago
        ]
    )
    detector = TaskRepeatDetector()
    proposals = detector.detect(db, _settings(cache_ttl_hours=1))
    assert len(proposals) == 1
    assert proposals[0].param == "cache_ttl_hours"
    assert proposals[0].confidence > 0


# ── all_detectors ─────────────────────────────────────────────────


def test_all_detectors_returns_three() -> None:
    """all_detectors() returns exactly 3 detectors."""
    detectors = all_detectors()
    assert len(detectors) == 3
    names = {d.name for d in detectors}
    assert names == {"cache_gap", "budget_slack", "task_repeat"}


def test_all_detectors_run_on_empty_db() -> None:
    """No crashes on empty DB."""
    db = _make_fingerprints_db([])
    for detector in all_detectors():
        proposals = detector.detect(db, _settings())
        assert proposals == []
