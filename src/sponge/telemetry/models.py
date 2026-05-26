"""Telemetry data models — cost fingerprint and tuning proposal schemas."""

from dataclasses import dataclass


@dataclass
class CostFingerprint:
    """A single cost fingerprint recorded after every LLM call."""

    session_id: str
    task_hash: str
    model: str
    provider: str
    tokens_in: int
    tokens_out: int
    cache_hit: bool
    cost: float
    naive_cost: float
    repo_state: str
    timestamp: str  # ISO-8601
    experiment_id: str | None = None
    experiment_group: str | None = None  # "baseline" | "shadow"


@dataclass
class TuningProposal:
    """A detected optimization opportunity with evidence."""

    id: str  # e.g. "cache_gap:2026-05-26T12:00"
    param: str  # e.g. "cache_ttl_hours"
    current: object  # current value
    proposed: object  # suggested value
    reason: str  # human-readable
    evidence_sql: str  # the SQL that found this
    confidence: float  # 0.0–1.0
    risk: str  # "low" | "medium" | "high"
    state: str = "proposed"  # proposed | testing | accepted | rejected
    created_at: str = ""  # ISO-8601


@dataclass
class ExperimentResult:
    """Statistical evaluation of a shadow A/B experiment."""

    proposal_id: str
    baseline_samples: int
    shadow_samples: int
    baseline_mean_cost: float
    shadow_mean_cost: float
    savings_pct: float
    p_value: float
    verdict: str  # "accept" | "reject" | "collect_more"
