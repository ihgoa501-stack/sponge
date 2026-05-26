"""Tests for cost tracker and savings ledger."""

import pytest

from sponge.cost.ledger import build_report
from sponge.cost.models import (
    CostEntry,
    ModelPricing,
    SavingsLedger,
    Usage,
)
from sponge.cost.tracker import CostTracker


def _make_pricing(
    input_per_1k: float = 3.0,
    output_per_1k: float = 15.0,
    cache_read_per_1k: float | None = 0.30,
) -> ModelPricing:
    return ModelPricing(
        input_per_1k=input_per_1k,
        output_per_1k=output_per_1k,
        cache_read_per_1k=cache_read_per_1k,
    )


def test_cost_tracker_no_cache() -> None:
    """Cost without caching equals naive cost."""
    tracker = CostTracker(_make_pricing())
    tracker.record_usage(Usage(tokens_in=1000, tokens_out=500))
    entry = tracker.finalize("test-model")

    assert entry.cost == pytest.approx(10.5)  # 1k*3 + 0.5k*15
    assert entry.naive_cost == pytest.approx(10.5)
    assert entry.cost == entry.naive_cost


def test_cost_tracker_with_cache_hit() -> None:
    """Cache read tokens reduce cost vs naive."""
    tracker = CostTracker(_make_pricing())
    # 500 input tokens hit cache, 500 don't.
    tracker.record_usage(
        Usage(
            tokens_in=1000,
            tokens_out=500,
            cache_read_tokens=500,
        )
    )
    entry = tracker.finalize("test-model")

    # Naive: 1k*3 + 0.5k*15 = 10.5
    # Actual: 500*0.30/1000 + 500*3/1000 + 500*15/1000 = 0.15 + 1.5 + 7.5 = 9.15
    assert entry.cost < entry.naive_cost
    assert entry.cost == pytest.approx(9.15)


def test_savings_ledger_accumulates() -> None:
    """Ledger accumulates entries and computes totals."""
    ledger = SavingsLedger()
    ledger.add(CostEntry(usage=Usage(100, 50), model="m", cost=1.0, naive_cost=2.0))
    ledger.add(CostEntry(usage=Usage(200, 100), model="m", cost=2.0, naive_cost=4.0))

    assert ledger.total_actual == 3.0
    assert ledger.total_naive == 6.0
    assert ledger.saved_by_cache == 3.0


def test_savings_report_format() -> None:
    """Report formats text and JSON correctly."""
    ledger = SavingsLedger()
    ledger.add(CostEntry(usage=Usage(100, 50), model="m", cost=1.0, naive_cost=2.0))

    report = build_report(ledger)
    text = report.format_text()
    assert "Cost: $1.0000" in text
    assert "naive: $2.0000" in text
    assert "saved $1.0000" in text

    json_str = report.format_json()
    import json

    data = json.loads(json_str)
    assert data["cost"] == 1.0
    assert data["saved"] == 1.0


def test_cost_tracker_zero_tokens() -> None:
    """Zero tokens produce zero cost."""
    tracker = CostTracker(_make_pricing())
    tracker.record_usage(Usage(tokens_in=0, tokens_out=0))
    entry = tracker.finalize("test-model")
    assert entry.cost == 0.0
    assert entry.naive_cost == 0.0
