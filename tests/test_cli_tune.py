"""Tests for sponge tune CLI commands."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from sponge.cli.app import app


def test_tune_report_empty_db() -> None:
    """tune --report handles empty fingerprints DB gracefully."""
    import sqlite3

    runner = CliRunner()
    fp_db = Path(tempfile.mkdtemp()) / "fp.db"
    # Create empty fingerprints table.
    conn = sqlite3.connect(str(fp_db))
    conn.execute("""CREATE TABLE fingerprints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT, task_hash TEXT, model TEXT, provider TEXT,
        tokens_in INTEGER, tokens_out INTEGER, cache_hit INTEGER,
        cost REAL, naive_cost REAL, repo_state TEXT, timestamp TEXT,
        experiment_id TEXT, experiment_group TEXT
    )""")
    conn.commit()
    conn.close()

    with (
        patch("sponge.cli.tune_cmd.FINGERPRINTS_DB", fp_db),
        patch("sponge.cli.tune_cmd.PROPOSALS_DB", Path(tempfile.mkdtemp()) / "prop.db"),
    ):
        result = runner.invoke(app, ["tune", "report"])
        assert result.exit_code == 0


def test_tune_apply_missing_id() -> None:
    """tune --apply with missing ID returns error."""
    runner = CliRunner()
    with (
        patch("sponge.cli.tune_cmd.PROPOSALS_DB", Path(tempfile.mkdtemp()) / "prop.db"),
    ):
        result = runner.invoke(app, ["tune", "apply", "nonexistent"])
        assert result.exit_code == 1


def test_tune_review_empty() -> None:
    """tune --review handles empty proposals DB."""
    import sqlite3

    runner = CliRunner()
    fp_db = Path(tempfile.mkdtemp()) / "fp.db"
    conn = sqlite3.connect(str(fp_db))
    conn.execute("""CREATE TABLE fingerprints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT, task_hash TEXT, model TEXT, provider TEXT,
        tokens_in INTEGER, tokens_out INTEGER, cache_hit INTEGER,
        cost REAL, naive_cost REAL, repo_state TEXT, timestamp TEXT,
        experiment_id TEXT, experiment_group TEXT
    )""")
    conn.commit()
    conn.close()

    with (
        patch("sponge.cli.tune_cmd.FINGERPRINTS_DB", fp_db),
        patch("sponge.cli.tune_cmd.PROPOSALS_DB", Path(tempfile.mkdtemp()) / "prop.db"),
    ):
        result = runner.invoke(app, ["tune", "review"])
        assert result.exit_code == 0
        assert "No active experiments" in result.output


def test_tune_history_empty() -> None:
    """tune --history handles empty proposals DB."""
    runner = CliRunner()
    with (
        patch("sponge.cli.tune_cmd.PROPOSALS_DB", Path(tempfile.mkdtemp()) / "prop.db"),
    ):
        result = runner.invoke(app, ["tune", "history"])
        assert result.exit_code == 0


def test_tune_help() -> None:
    """tune --help shows available commands."""
    runner = CliRunner()
    result = runner.invoke(app, ["tune", "--help"])
    assert result.exit_code == 0
    assert "report" in result.output
    assert "apply" in result.output
    assert "review" in result.output
    assert "history" in result.output
