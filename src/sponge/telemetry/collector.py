"""Telemetry collector — writes cost fingerprints to local SQLite.

Every LLM call produces a CostFingerprint row. This data feeds the
replay optimizer in Phase 2. All data stays local — no cloud, no server.
"""

import sqlite3
from pathlib import Path

from sponge.telemetry.models import CostFingerprint


class TelemetryCollector:
    """Writes cost fingerprints to SQLite for later analysis.

    The database lives at ~/.sponge/telemetry/fingerprints.db.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS fingerprints (
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
                    experiment_group TEXT,
                    reflection_tokens INTEGER NOT NULL DEFAULT 0,
                    lessons_retrieved INTEGER NOT NULL DEFAULT 0,
                    lesson_stored TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_session
                    ON fingerprints(session_id);
                CREATE INDEX IF NOT EXISTS idx_timestamp
                    ON fingerprints(timestamp);
                CREATE INDEX IF NOT EXISTS idx_experiment
                    ON fingerprints(experiment_id);
            """)
            conn.commit()

    def log_call(self, fp: CostFingerprint) -> None:
        """Write one cost fingerprint to the database."""
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO fingerprints
                   (session_id, task_hash, model, provider,
                    tokens_in, tokens_out, cache_hit,
                    cost, naive_cost, repo_state, timestamp,
                    experiment_id, experiment_group,
                    reflection_tokens, lessons_retrieved, lesson_stored)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    fp.session_id,
                    fp.task_hash,
                    fp.model,
                    fp.provider,
                    fp.tokens_in,
                    fp.tokens_out,
                    1 if fp.cache_hit else 0,
                    fp.cost,
                    fp.naive_cost,
                    fp.repo_state,
                    fp.timestamp,
                    fp.experiment_id,
                    fp.experiment_group,
                    fp.reflection_tokens,
                    fp.lessons_retrieved,
                    fp.lesson_stored,
                ),
            )
            conn.commit()

    def get_session(self, session_id: str) -> list[CostFingerprint]:
        """Return all fingerprints for a given session."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT session_id, task_hash, model, provider,
                          tokens_in, tokens_out, cache_hit,
                          cost, naive_cost, repo_state, timestamp,
                          experiment_id, experiment_group,
                          reflection_tokens, lessons_retrieved, lesson_stored
                   FROM fingerprints
                   WHERE session_id = ?
                   ORDER BY id""",
                (session_id,),
            ).fetchall()
        return [
            CostFingerprint(
                session_id=r[0],
                task_hash=r[1],
                model=r[2],
                provider=r[3],
                tokens_in=r[4],
                tokens_out=r[5],
                cache_hit=bool(r[6]),
                cost=r[7],
                naive_cost=r[8],
                repo_state=r[9],
                timestamp=r[10],
                experiment_id=r[11],
                experiment_group=r[12],
                reflection_tokens=r[13] if len(r) > 13 else 0,
                lessons_retrieved=r[14] if len(r) > 14 else 0,
                lesson_stored=r[15] if len(r) > 15 else "",
            )
            for r in rows
        ]

    def recent_sessions(self, limit: int = 10) -> list[dict[str, object]]:
        """Return summary stats for recent sessions."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT session_id,
                          COUNT(*) as calls,
                          SUM(cost) as total_cost,
                          SUM(naive_cost) as total_naive,
                          MIN(timestamp) as first_call,
                          MAX(timestamp) as last_call
                   FROM fingerprints
                   GROUP BY session_id
                   ORDER BY last_call DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        return [
            {
                "session_id": r[0],
                "calls": r[1],
                "total_cost": r[2],
                "total_naive": r[3],
                "first_call": r[4],
                "last_call": r[5],
            }
            for r in rows
        ]
