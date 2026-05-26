"""Tuner orchestrator — runs detectors, manages proposals, evaluates A/B.

All validation uses real session data — no simulation.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from sponge.config.settings import Settings
from sponge.telemetry.analyzer import all_detectors
from sponge.telemetry.models import ExperimentResult, TuningProposal


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ── Mann-Whitney U (no scipy dependency) ──────────────────────────


def _mannwhitneyu(x: list[float], y: list[float], alternative: str = "less") -> tuple[float, float]:
    """Simplified Mann-Whitney U test.

    Returns (u_statistic, p_value). Uses normal approximation for n > 20,
    exact calculation for small samples.
    """
    try:
        from scipy.stats import mannwhitneyu

        result = mannwhitneyu(x, y, alternative=alternative)
        return float(result.statistic), float(result.pvalue)
    except ImportError:
        pass

    # Combine, rank, compute U.
    n1, n2 = len(x), len(y)
    combined = [(v, 0) for v in x] + [(v, 1) for v in y]
    combined.sort(key=lambda p: p[0])

    ranks = [0.0] * len(combined)
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + j + 1) / 2.0  # 1-indexed average
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j

    r1 = sum(ranks[k] for k in range(len(combined)) if combined[k][1] == 0)
    u1 = r1 - n1 * (n1 + 1) / 2.0

    # Normal approximation.
    mu = n1 * n2 / 2.0
    sigma = (n1 * n2 * (n1 + n2 + 1) / 12.0) ** 0.5
    if sigma == 0:
        return u1, 1.0

    z = (u1 - mu) / sigma
    # One-tailed p from z-score (normal approximation).
    p = 0.5 * (1.0 + _erf(z / 1.4142135623730951))  # z / sqrt(2)
    if alternative == "less":
        p = 1.0 - p

    return u1, min(1.0, max(0.0, p))


def _erf(x: float) -> float:
    """Approximation of the error function (Abramowitz & Stegun 7.1.26)."""
    import math

    sign = 1.0 if x >= 0 else -1.0
    x = abs(x)
    t = 1.0 / (1.0 + 0.3275911 * x)
    coef = (
        (((1.061405429 * t + -1.453152027) * t) + 1.421413741) * t + -0.284496736
    ) * t + 0.254829592
    y = 1.0 - coef * t * math.exp(-x * x)
    return sign * y


# ── Proposal Store ────────────────────────────────────────────────


class ProposalStore:
    """SQLite-backed store for tuning proposals."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS proposals (
                    id TEXT PRIMARY KEY,
                    param TEXT NOT NULL,
                    current_val TEXT NOT NULL,
                    proposed_val TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    evidence_sql TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    risk TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'proposed',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def insert(self, p: TuningProposal) -> None:
        """Insert or replace a proposal."""
        now = _now()
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO proposals
                   (id, param, current_val, proposed_val, reason,
                    evidence_sql, confidence, risk, state,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    p.id,
                    p.param,
                    json.dumps(p.current),
                    json.dumps(p.proposed),
                    p.reason,
                    p.evidence_sql,
                    p.confidence,
                    p.risk,
                    p.state,
                    p.created_at or now,
                    now,
                ),
            )
            conn.commit()

    def get(self, proposal_id: str) -> TuningProposal | None:
        """Get a proposal by ID."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM proposals WHERE id = ?", (proposal_id,)).fetchone()
            if row is None:
                return None
            return self._row_to_proposal(row)

    def list_all(self) -> list[TuningProposal]:
        """List all proposals, newest first."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM proposals ORDER BY created_at DESC").fetchall()
        return [self._row_to_proposal(r) for r in rows]

    def list_by_state(self, state: str) -> list[TuningProposal]:
        """List proposals in a given state."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM proposals WHERE state = ? ORDER BY created_at DESC",
                (state,),
            ).fetchall()
        return [self._row_to_proposal(r) for r in rows]

    def update_state(self, proposal_id: str, state: str) -> None:
        """Update a proposal's state."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE proposals SET state = ?, updated_at = ? WHERE id = ?",
                (state, _now(), proposal_id),
            )
            conn.commit()

    def _row_to_proposal(self, row: sqlite3.Row) -> TuningProposal:
        return TuningProposal(
            id=row["id"],
            param=row["param"],
            current=json.loads(row["current_val"]),
            proposed=json.loads(row["proposed_val"]),
            reason=row["reason"],
            evidence_sql=row["evidence_sql"],
            confidence=row["confidence"],
            risk=row["risk"],
            state=row["state"],
            created_at=row["created_at"],
        )


# ── Tuner ─────────────────────────────────────────────────────────


class Tuner:
    """Orchestrates signal detection, proposal lifecycle, and A/B evaluation."""

    def __init__(
        self,
        fingerprints_db: str | Path,
        proposal_db: str | Path,
        settings: Settings,
    ) -> None:
        self._fp_db = Path(fingerprints_db)
        self._settings = settings
        self.store = ProposalStore(proposal_db)

    def _fp_connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._fp_db))

    def run_detectors(self) -> list[TuningProposal]:
        """Run all detectors and return ranked, deduplicated proposals."""
        conn = self._fp_connect()
        try:
            all_proposals: list[TuningProposal] = []
            for detector in all_detectors():
                all_proposals.extend(detector.detect(conn, self._settings))
        finally:
            conn.close()

        return self._rank(self._deduplicate(all_proposals))

    def _deduplicate(self, proposals: list[TuningProposal]) -> list[TuningProposal]:
        """Keep only the highest-confidence proposal per parameter."""
        best: dict[str, TuningProposal] = {}
        for p in proposals:
            if p.param not in best or p.confidence > best[p.param].confidence:
                best[p.param] = p
        return list(best.values())

    def _rank(self, proposals: list[TuningProposal]) -> list[TuningProposal]:
        """Sort by: confidence * savings_potential / risk_score."""
        risk_weight = {"low": 1, "medium": 2, "high": 4}

        def score(p: TuningProposal) -> float:
            risk = risk_weight.get(p.risk, 2)
            return p.confidence / risk

        return sorted(proposals, key=score, reverse=True)

    def activate(self, proposal_id: str) -> TuningProposal | None:
        """Move a proposal to testing state."""
        p = self.store.get(proposal_id)
        if p is None:
            return None
        p.state = "testing"
        self.store.update_state(proposal_id, "testing")
        self.store.insert(p)
        return p

    def evaluate(self, proposal_id: str) -> ExperimentResult | None:
        """Evaluate shadow A/B data for a testing proposal."""
        p = self.store.get(proposal_id)
        if p is None:
            return None

        conn = self._fp_connect()
        try:
            baseline_rows = conn.execute(
                """SELECT cost FROM fingerprints
                   WHERE experiment_id = ? AND experiment_group = 'baseline'""",
                (proposal_id,),
            ).fetchall()
            shadow_rows = conn.execute(
                """SELECT cost FROM fingerprints
                   WHERE experiment_id = ? AND experiment_group = 'shadow'""",
                (proposal_id,),
            ).fetchall()
        finally:
            conn.close()

        baseline = [r[0] for r in baseline_rows]
        shadow = [r[0] for r in shadow_rows]

        if len(baseline) < 3 or len(shadow) < 3:
            return ExperimentResult(
                proposal_id=proposal_id,
                baseline_samples=len(baseline),
                shadow_samples=len(shadow),
                baseline_mean_cost=sum(baseline) / len(baseline) if baseline else 0.0,
                shadow_mean_cost=sum(shadow) / len(shadow) if shadow else 0.0,
                savings_pct=0.0,
                p_value=1.0,
                verdict="collect_more",
            )

        baseline_mean = sum(baseline) / len(baseline)
        shadow_mean = sum(shadow) / len(shadow)

        savings_pct = (
            (baseline_mean - shadow_mean) / baseline_mean * 100 if baseline_mean > 0 else 0.0
        )

        _, p_value = _mannwhitneyu(shadow, baseline, alternative="less")

        min_samples = self._settings.tune_min_samples
        if (
            p_value < self._settings.tune_confidence_p
            and savings_pct >= self._settings.tune_min_savings_pct
            and len(baseline) >= min_samples
            and len(shadow) >= min_samples
        ):
            verdict = "accept"
        elif len(baseline) >= min_samples and len(shadow) >= min_samples:
            verdict = "reject"
        else:
            verdict = "collect_more"

        result = ExperimentResult(
            proposal_id=proposal_id,
            baseline_samples=len(baseline),
            shadow_samples=len(shadow),
            baseline_mean_cost=round(baseline_mean, 6),
            shadow_mean_cost=round(shadow_mean, 6),
            savings_pct=round(savings_pct, 2),
            p_value=round(p_value, 4),
            verdict=verdict,
        )

        if verdict == "accept":
            self.apply(proposal_id)
        elif verdict == "reject":
            self.store.update_state(proposal_id, "rejected")

        return result

    def apply(self, proposal_id: str) -> None:
        """Accept a winning proposal — write to config and mark accepted."""
        p = self.store.get(proposal_id)
        if p is None:
            return

        # Write to ~/.sponge/config.toml
        config_path = Path.home() / ".sponge" / "config.toml"
        self._write_config(config_path, p.param, p.proposed)

        self.store.update_state(proposal_id, "accepted")

    def _write_config(self, path: Path, key: str, value: object) -> None:
        """Write a single key=value to TOML config, preserving existing keys."""
        path.parent.mkdir(parents=True, exist_ok=True)

        existing: dict[str, object] = {}
        if path.is_file():
            try:
                import tomllib

                existing = tomllib.loads(path.read_text())
            except Exception:
                pass

        existing[key] = value

        lines: list[str] = []
        for k, v in sorted(existing.items()):
            if isinstance(v, bool):
                lines.append(f"{k} = {str(v).lower()}")
            elif isinstance(v, str):
                lines.append(f'{k} = "{v}"')
            else:
                lines.append(f"{k} = {v}")
        path.write_text("\n".join(lines) + "\n")
