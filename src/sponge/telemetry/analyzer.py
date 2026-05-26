"""Signal detectors — analyze fingerprints to find optimization opportunities.

Each detector independently queries the fingerprints database and
returns TuningProposal instances when patterns are detected.
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from datetime import UTC, datetime

from sponge.config.settings import Settings
from sponge.telemetry.models import TuningProposal


def _now() -> str:
    return datetime.now(UTC).isoformat()


class SignalDetector(ABC):
    """Base class for signal detectors."""

    name: str

    @abstractmethod
    def detect(self, db: sqlite3.Connection, settings: Settings) -> list[TuningProposal]:
        """Query fingerprints and return any tuning proposals."""


class CacheGapDetector(SignalDetector):
    """Detects when cache TTL is shorter than median request gap.

    If the median time between consecutive calls within a session
    exceeds the current cache_ttl_hours, the cache is expiring between
    requests that might otherwise hit.
    """

    name = "cache_gap"

    def detect(self, db: sqlite3.Connection, settings: Settings) -> list[TuningProposal]:
        window = f"-{settings.tune_window_days} days"
        sql = """
            SELECT AVG(gap_minutes) FROM (
                SELECT (julianday(t2.timestamp) - julianday(t1.timestamp))
                       * 1440 AS gap_minutes
                FROM fingerprints t1
                JOIN fingerprints t2
                  ON t2.rowid = t1.rowid + 1
                 AND t2.session_id = t1.session_id
                WHERE t1.timestamp > datetime('now', ?)
            )
        """
        row = db.execute(sql, (window,)).fetchone()
        if row is None or row[0] is None:
            return []

        median_gap_min = row[0]
        current_ttl_min = settings.cache_ttl_hours * 60

        if median_gap_min <= current_ttl_min:
            return []

        proposed_hours = max(1, round(median_gap_min * 1.5 / 60))
        gap_ratio = median_gap_min / max(current_ttl_min, 1)
        confidence = min(1.0, gap_ratio / 3.0)

        return [
            TuningProposal(
                id=f"cache_gap:{_now()}",
                param="cache_ttl_hours",
                current=settings.cache_ttl_hours,
                proposed=proposed_hours,
                reason=(
                    f"Median request gap ({median_gap_min:.0f} min) "
                    f"exceeds cache TTL ({current_ttl_min:.0f} min). "
                    f"Raising TTL to {proposed_hours}h may increase cache hits."
                ),
                evidence_sql=sql,
                confidence=round(confidence, 2),
                risk="low",
                created_at=_now(),
            )
        ]


class BudgetSlackDetector(SignalDetector):
    """Detects when budget ceiling is too high relative to actual spend.

    Budget ceilings are risk controls, not savings engines. But a ceiling
    set too high provides no guardrail.
    """

    name = "budget_slack"

    def detect(self, db: sqlite3.Connection, settings: Settings) -> list[TuningProposal]:
        window = f"-{settings.tune_window_days} days"
        sql = """
            SELECT session_id, SUM(cost) as total
            FROM fingerprints
            WHERE timestamp > datetime('now', ?)
            GROUP BY session_id
        """
        rows = db.execute(sql, (window,)).fetchall()
        if len(rows) < 3:
            return []

        costs = sorted(r[1] for r in rows)
        median = costs[len(costs) // 2]
        p75 = costs[int(len(costs) * 0.75)]

        if median > settings.budget_per_session * 0.5:
            return []

        proposed = round(p75 * 1.2, 2)
        utilization = median / max(settings.budget_per_session, 0.01)
        confidence = 0.5 + (1.0 - min(utilization, 1.0)) * 0.5

        return [
            TuningProposal(
                id=f"budget_slack:{_now()}",
                param="budget_per_session",
                current=settings.budget_per_session,
                proposed=proposed,
                reason=(
                    f"Median session cost (${median:.2f}) is "
                    f"{utilization:.0%} of budget (${settings.budget_per_session:.2f}). "
                    f"Lowering to ${proposed:.2f} (P75 * 1.2) tightens guardrails."
                ),
                evidence_sql=sql,
                confidence=round(confidence, 2),
                risk="medium",
                created_at=_now(),
            )
        ]


class TaskRepeatDetector(SignalDetector):
    """Detects repeated tasks that could benefit from longer cache TTL.

    If the same task_hash appears at least 3 times with at least one
    cache miss, and the time span between first and last occurrence
    exceeds the current cache TTL, extending TTL could prevent misses.
    """

    name = "task_repeat"

    def detect(self, db: sqlite3.Connection, settings: Settings) -> list[TuningProposal]:
        window = f"-{settings.tune_window_days} days"
        sql = """
            SELECT task_hash, COUNT(*) as cnt,
                   SUM(CASE WHEN cache_hit = 0 THEN 1 ELSE 0 END) as misses,
                   MIN(timestamp) as first_seen,
                   MAX(timestamp) as last_seen
            FROM fingerprints
            WHERE timestamp > datetime('now', ?)
            GROUP BY task_hash
            HAVING cnt >= 3 AND misses > 0
        """
        rows = db.execute(sql, (window,)).fetchall()
        proposals: list[TuningProposal] = []

        for task_hash, cnt, misses, first_seen, last_seen in rows:
            # Calculate hours between first and last occurrence.
            try:
                first = datetime.fromisoformat(first_seen)
                last = datetime.fromisoformat(last_seen)
                span_hours = (last - first).total_seconds() / 3600
            except (ValueError, TypeError):
                continue

            if span_hours <= settings.cache_ttl_hours:
                continue

            proposed_hours = max(1, round(span_hours * 1.5))
            confidence = min(1.0, cnt / 5.0)

            proposals.append(
                TuningProposal(
                    id=f"task_repeat:{task_hash[:8]}:{_now()}",
                    param="cache_ttl_hours",
                    current=settings.cache_ttl_hours,
                    proposed=proposed_hours,
                    reason=(
                        f"Task '{task_hash[:8]}...' repeated {cnt} times "
                        f"over {span_hours:.0f}h (TTL: {settings.cache_ttl_hours}h), "
                        f"with {misses} cache misses."
                    ),
                    evidence_sql=sql,
                    confidence=round(confidence, 2),
                    risk="low",
                    created_at=_now(),
                )
            )

        return proposals


def all_detectors() -> list[SignalDetector]:
    """Return all built-in signal detectors."""
    return [CacheGapDetector(), BudgetSlackDetector(), TaskRepeatDetector()]
