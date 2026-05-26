"""Tests for ProjectMemory — cross-session TOML-based rule storage."""

import tempfile
from pathlib import Path

from sponge.memory.store import ProjectMemory


def test_load_missing_file_returns_empty() -> None:
    """Loading a non-existent memory file returns an empty list."""
    mem = ProjectMemory(Path(tempfile.mkdtemp()) / "nonexistent.toml")
    assert mem.load() == []


def test_save_and_load_roundtrip() -> None:
    """Rules survive a save → load cycle."""
    tmp = Path(tempfile.mkdtemp()) / "memory.toml"
    mem = ProjectMemory(tmp)
    mem.save(["Use httpx not requests", "Never touch test/fixtures/"])

    loaded = mem.load()
    assert loaded == ["Use httpx not requests", "Never touch test/fixtures/"]


def test_add_appends_rule() -> None:
    """add() appends a new rule without duplicating existing ones."""
    tmp = Path(tempfile.mkdtemp()) / "memory.toml"
    mem = ProjectMemory(tmp)
    mem.save(["Rule 1"])
    mem.add("Rule 2")
    assert mem.load() == ["Rule 1", "Rule 2"]


def test_add_skips_duplicate() -> None:
    """add() does not append a rule already present."""
    tmp = Path(tempfile.mkdtemp()) / "memory.toml"
    mem = ProjectMemory(tmp)
    mem.save(["Rule 1"])
    mem.add("Rule 1")
    assert mem.load() == ["Rule 1"]


def test_remove_by_index() -> None:
    """remove() deletes the rule at the given index."""
    tmp = Path(tempfile.mkdtemp()) / "memory.toml"
    mem = ProjectMemory(tmp)
    mem.save(["A", "B", "C"])
    assert mem.remove(1) is True
    assert mem.load() == ["A", "C"]


def test_remove_out_of_range_returns_false() -> None:
    """remove() returns False when the index is out of range."""
    tmp = Path(tempfile.mkdtemp()) / "memory.toml"
    mem = ProjectMemory(tmp)
    mem.save(["A"])
    assert mem.remove(5) is False
    assert mem.load() == ["A"]


def test_to_system_prompt_formats_rules() -> None:
    """to_system_prompt() renders rules as a numbered markdown block."""
    tmp = Path(tempfile.mkdtemp()) / "memory.toml"
    mem = ProjectMemory(tmp)
    mem.save(["Use httpx", "Never touch fixtures"])
    prompt = mem.to_system_prompt()
    assert "## Project Memory" in prompt
    assert "1. Use httpx" in prompt
    assert "2. Never touch fixtures" in prompt


def test_to_system_prompt_empty_returns_empty_string() -> None:
    """to_system_prompt() returns '' when there are no rules."""
    tmp = Path(tempfile.mkdtemp()) / "memory.toml"
    mem = ProjectMemory(tmp)
    assert mem.to_system_prompt() == ""


def test_exists_returns_false_for_missing_file() -> None:
    """exists is False when the memory file doesn't exist."""
    mem = ProjectMemory(Path(tempfile.mkdtemp()) / "nonexistent.toml")
    assert mem.exists is False


def test_exists_returns_true_after_save() -> None:
    """exists is True after save() creates the file."""
    tmp = Path(tempfile.mkdtemp()) / "memory.toml"
    mem = ProjectMemory(tmp)
    mem.save(["Rule"])
    assert mem.exists is True
