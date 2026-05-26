"""SQLite-backed key-value store for caching."""

import sqlite3
import time
from pathlib import Path


class DiskStore:
    """Simple SQLite key-value store with TTL support."""

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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS store (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            conn.commit()

    def get(self, key: str) -> str | None:
        """Get a value by key. Returns None if expired or missing."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value, expires_at FROM store WHERE key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            value, expires_at = row
            if expires_at < time.time():
                self.delete(key)
                return None
            return str(value)

    def set(self, key: str, value: str, ttl_hours: int = 24) -> None:
        """Set a value with TTL in hours."""
        expires_at = time.time() + (ttl_hours * 3600)
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO store (key, value, expires_at) VALUES (?, ?, ?)",
                (key, value, expires_at),
            )
            conn.commit()

    def delete(self, key: str) -> None:
        """Delete a key."""
        with self._connect() as conn:
            conn.execute("DELETE FROM store WHERE key = ?", (key,))
            conn.commit()

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM store WHERE expires_at < ?", (time.time(),))
            conn.commit()
            return cursor.rowcount

    def list_by_prefix(self, prefix: str) -> list[tuple[str, str]]:
        """Return (key, value) pairs for all non-expired keys with given prefix."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key, value FROM store WHERE key LIKE ? AND expires_at >= ?",
                (prefix + "%", time.time()),
            ).fetchall()
        return [(str(r[0]), str(r[1])) for r in rows]
