"""Reflective memory — the wooden pillar where lessons are carved.

Stores structured lessons extracted from agent failures. Each lesson is
immutable once written (can be superseded but never deleted). Lessons are
keyed by a hash of their condition fields for efficient retrieval.

Storage: .sponge/reflections/<condition_hash>.jsonl (one JSON object per line)
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sponge.core.reflection import Lesson

logger = logging.getLogger("sponge.memory.reflective")

# ---------------------------------------------------------------------------
# Persisted lesson format (extends Lesson with metadata)
# ---------------------------------------------------------------------------


class StoredLesson:
    """A lesson as persisted in JSONL — with id, timestamp, and impact tracking."""

    __slots__ = (
        "id",
        "timestamp",
        "condition",
        "action",
        "observed_outcome",
        "lesson",
        "severity",
        "supersedes",
        "impact_score",
        "times_retrieved",
    )

    def __init__(
        self,
        *,
        id: str = "",
        timestamp: str = "",
        condition: str = "",
        action: str = "",
        observed_outcome: str = "",
        lesson: str = "",
        severity: str = "medium",
        supersedes: str | None = None,
        impact_score: float = 0.0,
        times_retrieved: int = 0,
    ) -> None:
        self.id = id
        self.timestamp = timestamp
        self.condition = condition
        self.action = action
        self.observed_outcome = observed_outcome
        self.lesson = lesson
        self.severity = severity
        self.supersedes = supersedes
        self.impact_score = impact_score
        self.times_retrieved = times_retrieved

    @classmethod
    def from_lesson(cls, lesson: Lesson, id: str = "") -> StoredLesson:
        """Create a StoredLesson from a Lesson, assigning id and timestamp."""
        return cls(
            id=id or f"ref_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(UTC).isoformat(),
            condition=lesson.condition,
            action=lesson.action,
            observed_outcome=lesson.observed_outcome,
            lesson=lesson.lesson,
            severity=lesson.severity,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "condition": self.condition,
            "action": self.action,
            "observed_outcome": self.observed_outcome,
            "lesson": self.lesson,
            "severity": self.severity,
            "supersedes": self.supersedes,
            "impact_score": self.impact_score,
            "times_retrieved": self.times_retrieved,
        }

    @classmethod
    def from_dict(cls, d: dict) -> StoredLesson:
        return cls(
            id=d.get("id", ""),
            timestamp=d.get("timestamp", ""),
            condition=d.get("condition", ""),
            action=d.get("action", ""),
            observed_outcome=d.get("observed_outcome", ""),
            lesson=d.get("lesson", ""),
            severity=d.get("severity", "medium"),
            supersedes=d.get("supersedes"),
            impact_score=d.get("impact_score", 0.0),
            times_retrieved=d.get("times_retrieved", 0),
        )

    def to_context_line(self) -> str:
        """Render as a single line for system prompt injection."""
        return f"[{self.id}] {self.lesson}"


# ---------------------------------------------------------------------------
# Reflective memory store
# ---------------------------------------------------------------------------


class ReflectiveMemory:
    """Stores and retrieves lessons extracted from agent failures.

    Lessons are stored as JSONL in .sponge/reflections/, sharded by a hash
    of the condition fields. Each lesson is immutable once written.

    Usage:
        mem = ReflectiveMemory()
        mem.store(lesson)
        relevant = mem.query("file_edit | test_breakage")
        context = mem.to_context("file_edit | test_breakage")
    """

    DEFAULT_DIR = Path(".sponge") / "reflections"

    def __init__(self, directory: Path | None = None) -> None:
        self._dir = directory or self.DEFAULT_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def directory(self) -> Path:
        return self._dir

    # ----- storage -----

    def store(self, lesson: Lesson) -> StoredLesson:
        """Store a lesson and return the persisted version with id.

        The lesson is appended to a JSONL file keyed by its condition hash.
        """
        stored = StoredLesson.from_lesson(lesson)
        path = self._path_for(stored.condition)
        line = json.dumps(stored.to_dict(), ensure_ascii=False)
        with path.open("a") as f:
            f.write(line + "\n")
        logger.debug("Stored lesson %s → %s", stored.id, path)
        return stored

    def supersede(self, old_id: str, new_lesson: Lesson) -> StoredLesson | None:
        """Store a new lesson that supersedes an existing one.

        The old lesson is NOT deleted — it's marked as superseded via the
        supersedes chain. Returns the new StoredLesson, or None if old_id
        not found.
        """
        old = self.find_by_id(old_id)
        if old is None:
            return None
        stored = StoredLesson.from_lesson(new_lesson)
        stored.supersedes = old_id
        path = self._path_for(stored.condition)
        line = json.dumps(stored.to_dict(), ensure_ascii=False)
        with path.open("a") as f:
            f.write(line + "\n")
        logger.debug("Superseded %s with %s", old_id, stored.id)
        return stored

    # ----- retrieval -----

    def query(
        self, condition: str, *, include_superseded: bool = False
    ) -> list[StoredLesson]:
        """Retrieve lessons matching a condition.

        Condition matching is substring-based on the condition field —
        'file_edit' matches 'file_edit | test_breakage | ...'.

        By default, superseded lessons are excluded.
        """
        results: list[StoredLesson] = []
        superseded_ids: set[str] = set()

        # Collect all superseded ids so we can filter.
        if not include_superseded:
            for sl in self._all_superseded():
                if sl.supersedes:
                    superseded_ids.add(sl.supersedes)

        # Search across all shards whose hash prefix might match.
        # For substring matching we need to scan — but we limit to
        # files whose condition hash prefix overlaps with the query.
        for path in self._dir.glob("*.jsonl"):
            lessons = self._load_file(path)
            for sl in lessons:
                if condition.lower() in sl.condition.lower():
                    if not include_superseded and sl.id in superseded_ids:
                        continue
                    results.append(sl)

        # Sort by recency.
        results.sort(key=lambda s: s.timestamp, reverse=True)

        # Mark as retrieved.
        for sl in results:
            sl.times_retrieved += 1
        # NOTE: We don't persist the increment here — that would require
        # rewriting the file. Impact tracking is approximate.

        return results

    def find_by_id(self, lesson_id: str) -> StoredLesson | None:
        """Find a single lesson by its id."""
        for path in self._dir.glob("*.jsonl"):
            lessons = self._load_file(path)
            for sl in lessons:
                if sl.id == lesson_id:
                    return sl
        return None

    def list_all(self, *, include_superseded: bool = False) -> list[StoredLesson]:
        """List all stored lessons, newest first."""
        results: list[StoredLesson] = []
        superseded_ids: set[str] = set()

        if not include_superseded:
            for sl in self._all_superseded():
                if sl.supersedes:
                    superseded_ids.add(sl.supersedes)

        for path in self._dir.glob("*.jsonl"):
            for sl in self._load_file(path):
                if not include_superseded and sl.id in superseded_ids:
                    continue
                results.append(sl)

        results.sort(key=lambda s: s.timestamp, reverse=True)
        return results

    def count(self, *, include_superseded: bool = False) -> int:
        """Count stored lessons."""
        return len(self.list_all(include_superseded=include_superseded))

    # ----- context injection -----

    def to_context(self, condition: str, max_lessons: int = 5) -> str:
        """Render relevant lessons as a system prompt block.

        Args:
            condition: The current task condition to match against.
            max_lessons: Maximum number of lessons to include (most recent first).

        Returns:
            A string like:
            ## Lessons from Past Attempts
            - [ref_001] Always run tests after editing src/auth/.
            - [ref_002] Read the full file before editing.
        """
        lessons = self.query(condition)[:max_lessons]
        if not lessons:
            return ""

        lines = ["## Lessons from Past Attempts", ""]
        for sl in lessons:
            lines.append(f"- {sl.to_context_line()}")
        lines.append("")
        return "\n".join(lines)

    # ----- maintenance -----

    def prune_superseded(self) -> int:
        """Remove all superseded lessons. Returns count removed.

        This rewrites each JSONL file, removing lines whose id appears
        in the supersedes chain of a newer lesson.
        """
        superseded_ids: set[str] = set()
        for sl in self._all_superseded():
            if sl.supersedes:
                superseded_ids.add(sl.supersedes)

        removed = 0
        for path in self._dir.glob("*.jsonl"):
            lessons = self._load_file(path)
            keep = [sl for sl in lessons if sl.id not in superseded_ids]
            removed += len(lessons) - len(keep)
            if len(keep) < len(lessons):
                self._write_file(path, keep)

        return removed

    # ----- internals -----

    def _condition_hash(self, condition: str) -> str:
        """SHA256 hash of the condition string (first 12 hex chars)."""
        return hashlib.sha256(condition.encode()).hexdigest()[:12]

    def _path_for(self, condition: str) -> Path:
        """File path for a given condition."""
        return self._dir / f"{self._condition_hash(condition)}.jsonl"

    @staticmethod
    def _load_file(path: Path) -> list[StoredLesson]:
        """Load all lessons from a JSONL file."""
        lessons: list[StoredLesson] = []
        try:
            for line in path.read_text().strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    lessons.append(StoredLesson.from_dict(data))
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Skipping corrupt line in %s", path)
        except FileNotFoundError:
            pass
        return lessons

    @staticmethod
    def _write_file(path: Path, lessons: list[StoredLesson]) -> None:
        """Write a list of lessons to a JSONL file (overwrite)."""
        lines = [
            json.dumps(sl.to_dict(), ensure_ascii=False) + "\n" for sl in lessons
        ]
        path.write_text("".join(lines))

    def _all_superseded(self) -> list[StoredLesson]:
        """Find all lessons that supersede other lessons."""
        results: list[StoredLesson] = []
        for path in self._dir.glob("*.jsonl"):
            for sl in self._load_file(path):
                if sl.supersedes:
                    results.append(sl)
        return results
