"""Tests for reflective memory — the wooden pillar."""

import json
import tempfile
from pathlib import Path

import pytest

from sponge.core.reflection import Lesson
from sponge.memory.reflective import ReflectiveMemory, StoredLesson


# ---------------------------------------------------------------------------
# StoredLesson
# ---------------------------------------------------------------------------


class TestStoredLesson:
    def test_from_lesson(self):
        lesson = Lesson(
            condition="file_edit | test_breakage",
            action="Edited test file",
            observed_outcome="Tests broke",
            lesson="Run tests after editing",
            severity="high",
        )
        stored = StoredLesson.from_lesson(lesson, id="ref_test")
        assert stored.id == "ref_test"
        assert stored.condition == lesson.condition
        assert stored.lesson == "Run tests after editing"
        assert stored.severity == "high"
        assert stored.timestamp  # auto-assigned
        assert stored.supersedes is None
        assert stored.impact_score == 0.0
        assert stored.times_retrieved == 0

    def test_auto_id(self):
        lesson = Lesson(
            condition="test",
            action="test",
            observed_outcome="test",
            lesson="test",
        )
        stored = StoredLesson.from_lesson(lesson)
        assert stored.id.startswith("ref_")
        assert len(stored.id) == 12  # ref_ + 8 hex

    def test_roundtrip_dict(self):
        original = StoredLesson(
            id="ref_001",
            timestamp="2026-01-01T00:00:00Z",
            condition="file_edit",
            action="edited file",
            observed_outcome="broke things",
            lesson="be careful",
            severity="medium",
            supersedes="ref_000",
            impact_score=0.75,
            times_retrieved=3,
        )
        d = original.to_dict()
        restored = StoredLesson.from_dict(d)
        assert restored.id == original.id
        assert restored.condition == original.condition
        assert restored.supersedes == "ref_000"
        assert restored.impact_score == 0.75
        assert restored.times_retrieved == 3

    def test_to_context_line(self):
        stored = StoredLesson(
            id="ref_042",
            lesson="Always read_file before edit_file.",
        )
        line = stored.to_context_line()
        assert "[ref_042]" in line
        assert "Always read_file" in line


# ---------------------------------------------------------------------------
# ReflectiveMemory
# ---------------------------------------------------------------------------


@pytest.fixture
def mem():
    """Create a ReflectiveMemory backed by a temp directory."""
    with tempfile.TemporaryDirectory() as tmp:
        yield ReflectiveMemory(directory=Path(tmp) / "reflections")


@pytest.fixture
def sample_lesson():
    return Lesson(
        condition="file_edit | test_breakage | Fix tests",
        action="Edited test_auth.py without reading first",
        observed_outcome="Broke 3 existing tests",
        lesson="Always read_file before edit_file in test files.",
        severity="high",
    )


class TestReflectiveMemory:
    def test_store_and_count(self, mem, sample_lesson):
        assert mem.count() == 0
        stored = mem.store(sample_lesson)
        assert stored.id.startswith("ref_")
        assert mem.count() == 1

    def test_store_creates_file(self, mem, sample_lesson):
        mem.store(sample_lesson)
        files = list(mem.directory.glob("*.jsonl"))
        assert len(files) == 1

    def test_query_matching(self, mem):
        mem.store(Lesson(
            condition="file_edit | test_breakage",
            action="edited file",
            observed_outcome="tests broke",
            lesson="Run tests after editing",
        ))
        mem.store(Lesson(
            condition="shell_cmd | network_error",
            action="ran pip install",
            observed_outcome="timeout",
            lesson="Use --timeout flag",
        ))

        # Query matches file_edit condition.
        results = mem.query("file_edit")
        assert len(results) == 1
        assert "Run tests" in results[0].lesson

        # Query matches shell_cmd condition.
        results = mem.query("shell_cmd")
        assert len(results) == 1
        assert "timeout" in results[0].lesson

        # Query matches nothing.
        results = mem.query("nonexistent")
        assert len(results) == 0

    def test_query_is_case_insensitive(self, mem):
        mem.store(Lesson(
            condition="FILE_EDIT",
            action="x",
            observed_outcome="y",
            lesson="z",
        ))
        results = mem.query("file_edit")
        assert len(results) == 1

    def test_find_by_id(self, mem):
        stored = mem.store(Lesson(
            condition="test",
            action="x",
            observed_outcome="y",
            lesson="z",
        ))
        found = mem.find_by_id(stored.id)
        assert found is not None
        assert found.id == stored.id

        not_found = mem.find_by_id("ref_nonexistent")
        assert not_found is None

    def test_list_all_newest_first(self, mem):
        first = mem.store(Lesson(
            condition="a", action="x", observed_outcome="y", lesson="first",
        ))
        second = mem.store(Lesson(
            condition="b", action="x", observed_outcome="y", lesson="second",
        ))
        all_lessons = mem.list_all()
        assert len(all_lessons) == 2
        # Newest first.
        assert all_lessons[0].lesson == "second"
        assert all_lessons[1].lesson == "first"

    def test_supersede(self, mem):
        old = mem.store(Lesson(
            condition="test", action="x", observed_outcome="y", lesson="old lesson",
        ))
        new_lesson = Lesson(
            condition="test", action="x", observed_outcome="y", lesson="new lesson",
        )
        new_stored = mem.supersede(old.id, new_lesson)
        assert new_stored is not None
        assert new_stored.supersedes == old.id

        # Without include_superseded, old is hidden.
        results = mem.query("test")
        assert len(results) == 1
        assert results[0].lesson == "new lesson"

        # With include_superseded, both appear.
        results_all = mem.query("test", include_superseded=True)
        assert len(results_all) == 2

    def test_supersede_nonexistent(self, mem):
        result = mem.supersede("ref_nonexistent", Lesson(
            condition="t", action="x", observed_outcome="y", lesson="z",
        ))
        assert result is None

    def test_to_context(self, mem):
        mem.store(Lesson(
            condition="file_edit",
            action="x",
            observed_outcome="y",
            lesson="Always read before editing.",
        ))
        mem.store(Lesson(
            condition="file_edit",
            action="x",
            observed_outcome="y",
            lesson="Run tests after editing auth files.",
        ))
        ctx = mem.to_context("file_edit")
        assert "Lessons from Past Attempts" in ctx
        assert "Always read before editing" in ctx
        assert "Run tests after editing auth files" in ctx

    def test_to_context_empty(self, mem):
        ctx = mem.to_context("nothing_matches")
        assert ctx == ""

    def test_to_context_respects_max(self, mem):
        for i in range(10):
            mem.store(Lesson(
                condition="test",
                action="x",
                observed_outcome="y",
                lesson=f"lesson {i}",
            ))
        ctx = mem.to_context("test", max_lessons=3)
        # Should only have 3 lessons.
        lines = [l for l in ctx.split("\n") if l.startswith("- [ref_")]
        assert len(lines) == 3

    def test_prune_superseded(self, mem):
        old = mem.store(Lesson(
            condition="test", action="x", observed_outcome="y", lesson="old",
        ))
        mem.supersede(old.id, Lesson(
            condition="test", action="x", observed_outcome="y", lesson="new",
        ))
        assert mem.count(include_superseded=True) == 2  # both exist

        removed = mem.prune_superseded()
        assert removed == 1
        assert mem.count() == 1
        assert mem.list_all()[0].lesson == "new"

    def test_empty_directory(self, mem):
        assert mem.count() == 0
        assert mem.list_all() == []
        assert mem.query("anything") == []
        assert mem.to_context("anything") == ""

    def test_multiple_shards(self, mem):
        """Lessons with different condition hashes go to different files."""
        mem.store(Lesson(
            condition="file_edit", action="x", observed_outcome="y", lesson="a",
        ))
        mem.store(Lesson(
            condition="completely_different_condition_string",
            action="x", observed_outcome="y", lesson="b",
        ))
        files = list(mem.directory.glob("*.jsonl"))
        assert len(files) == 2

    def test_corrupt_line_recovery(self, mem):
        """A corrupt JSONL line should be skipped, not crash."""
        mem.store(Lesson(
            condition="test", action="x", observed_outcome="y", lesson="good",
        ))
        # Find the file and append garbage.
        files = list(mem.directory.glob("*.jsonl"))
        with files[0].open("a") as f:
            f.write("this is not valid json\n")

        # Should still load the good lesson.
        results = mem.query("test")
        assert len(results) == 1
        assert results[0].lesson == "good"
