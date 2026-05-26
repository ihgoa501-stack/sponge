"""Tests for tuner orchestrator and proposal store."""

import tempfile
from pathlib import Path

from sponge.config.settings import Settings
from sponge.telemetry.tuner import (
    ProposalStore,
    Tuner,
    _mannwhitneyu,
)


def test_mannwhitneyu_small() -> None:
    """Mann-Whitney U returns reasonable values for small samples."""
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [0.5, 1.0, 1.5, 2.0, 2.5]
    u, p = _mannwhitneyu(y, x, alternative="less")
    assert 0.0 <= p <= 1.0
    assert u > 0


def test_mannwhitneyu_no_difference() -> None:
    """Identical distributions give high p-value."""
    x = [1.0, 2.0, 3.0]
    y = [1.0, 2.0, 3.0]
    _, p = _mannwhitneyu(y, x, alternative="less")
    assert p > 0.1  # Not significantly different


# ── ProposalStore ─────────────────────────────────────────────────


def test_proposal_store_insert_and_get() -> None:
    """Proposal can be inserted and retrieved."""
    from sponge.telemetry.models import TuningProposal

    with tempfile.TemporaryDirectory() as tmp:
        store = ProposalStore(Path(tmp) / "props.db")
        p = TuningProposal(
            id="test:1",
            param="cache_ttl_hours",
            current=24,
            proposed=72,
            reason="Test",
            evidence_sql="SELECT 1",
            confidence=0.8,
            risk="low",
        )
        store.insert(p)
        result = store.get("test:1")
        assert result is not None
        assert result.param == "cache_ttl_hours"
        assert result.proposed == 72
        assert result.state == "proposed"


def test_proposal_store_update_state() -> None:
    """Proposal state can be updated."""
    from sponge.telemetry.models import TuningProposal

    with tempfile.TemporaryDirectory() as tmp:
        store = ProposalStore(Path(tmp) / "props.db")
        p = TuningProposal(
            id="test:2",
            param="budget_per_session",
            current=10.0,
            proposed=5.0,
            reason="Test",
            evidence_sql="SELECT 1",
            confidence=0.6,
            risk="medium",
        )
        store.insert(p)
        store.update_state("test:2", "testing")
        result = store.get("test:2")
        assert result is not None
        assert result.state == "testing"


def test_proposal_store_list_by_state() -> None:
    """List filters by state."""
    from sponge.telemetry.models import TuningProposal

    with tempfile.TemporaryDirectory() as tmp:
        store = ProposalStore(Path(tmp) / "props.db")
        p1 = TuningProposal(
            id="a",
            param="x",
            current=1,
            proposed=2,
            reason="",
            evidence_sql="",
            confidence=0.5,
            risk="low",
        )
        p2 = TuningProposal(
            id="b",
            param="y",
            current=3,
            proposed=4,
            reason="",
            evidence_sql="",
            confidence=0.5,
            risk="low",
        )
        store.insert(p1)
        store.insert(p2)
        store.update_state("b", "testing")

        proposed = store.list_by_state("proposed")
        testing = store.list_by_state("testing")
        assert len(proposed) == 1
        assert len(testing) == 1
        assert proposed[0].id == "a"
        assert testing[0].id == "b"


# ── Tuner lifecycle ────────────────────────────────────────────────


def test_tuner_run_detectors_on_empty_db() -> None:
    """No crash, no proposals on empty fingerprint DB."""
    with tempfile.TemporaryDirectory() as tmp:
        fp_db = Path(tmp) / "fp.db"
        prop_db = Path(tmp) / "prop.db"
        # Create empty fingerprints table.
        import sqlite3

        conn = sqlite3.connect(str(fp_db))
        conn.execute("""
            CREATE TABLE fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT, task_hash TEXT, model TEXT, provider TEXT,
                tokens_in INTEGER, tokens_out INTEGER, cache_hit INTEGER,
                cost REAL, naive_cost REAL, repo_state TEXT, timestamp TEXT,
                experiment_id TEXT, experiment_group TEXT
            )
        """)
        conn.commit()
        conn.close()

        tuner = Tuner(fp_db, prop_db, Settings())
        proposals = tuner.run_detectors()
        assert proposals == []


def test_tuner_activate_and_evaluate() -> None:
    """Activate a proposal and evaluate with shadow data."""
    with tempfile.TemporaryDirectory() as tmp:
        fp_db = Path(tmp) / "fp.db"
        prop_db = Path(tmp) / "prop.db"

        # Create fingerprints with A/B data.
        import sqlite3

        conn = sqlite3.connect(str(fp_db))
        conn.execute("""
            CREATE TABLE fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT, task_hash TEXT, model TEXT, provider TEXT,
                tokens_in INTEGER, tokens_out INTEGER, cache_hit INTEGER,
                cost REAL, naive_cost REAL, repo_state TEXT, timestamp TEXT,
                experiment_id TEXT, experiment_group TEXT
            )
        """)
        # Insert baseline + shadow data.
        for i in range(10):
            conn.execute(
                """INSERT INTO fingerprints
                   (session_id, task_hash, model, provider, tokens_in,
                    tokens_out, cache_hit, cost, naive_cost, repo_state,
                    timestamp, experiment_id, experiment_group)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)""",
                (f"s{i}", f"t{i}", "m", "p", 10, 5, 0, 2.0, 2.0, "", "test:1", "baseline"),
            )
            conn.execute(
                """INSERT INTO fingerprints
                   (session_id, task_hash, model, provider, tokens_in,
                    tokens_out, cache_hit, cost, naive_cost, repo_state,
                    timestamp, experiment_id, experiment_group)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)""",
                (f"s{i}b", f"t{i}b", "m", "p", 10, 5, 0, 1.5, 1.5, "", "test:1", "shadow"),
            )
        conn.commit()
        conn.close()

        # Create a testing proposal.
        tuner = Tuner(
            fp_db,
            prop_db,
            Settings(tune_min_samples=10, tune_confidence_p=0.05, tune_min_savings_pct=5.0),
        )
        from sponge.telemetry.models import TuningProposal

        p = TuningProposal(
            id="test:1",
            param="cache_ttl_hours",
            current=24,
            proposed=72,
            reason="Test",
            evidence_sql="SELECT 1",
            confidence=0.8,
            risk="low",
            state="testing",
        )
        tuner.store.insert(p)

        # Evaluate.
        result = tuner.evaluate("test:1")
        assert result is not None
        assert result.baseline_samples == 10
        assert result.shadow_samples == 10
        # Shadow cost (1.5) < baseline cost (2.0) — should save.
        assert result.savings_pct > 0
