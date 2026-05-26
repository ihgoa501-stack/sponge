"""Savings ledger — accumulates cost entries and reports savings."""

from dataclasses import dataclass

from sponge.cost.models import SavingsLedger as Ledger


@dataclass
class SavingsReport:
    """A formatted summary of session savings."""

    total_actual: float
    total_naive: float
    saved: float
    saved_pct: float

    def format_text(self) -> str:
        """Human-readable cost summary."""
        return (
            f"Cost: ${self.total_actual:.4f} "
            f"(naive: ${self.total_naive:.4f}, "
            f"saved ${self.saved:.4f} by cache)"
        )

    def format_json(self) -> str:
        """JSON cost summary."""
        import json

        return json.dumps(
            {
                "cost": round(self.total_actual, 6),
                "naive_cost": round(self.total_naive, 6),
                "saved": round(self.saved, 6),
                "saved_pct": round(self.saved_pct, 2),
            }
        )


def build_report(ledger: Ledger) -> SavingsReport:
    """Build a savings report from a ledger."""
    saved = ledger.saved_by_cache
    saved_pct = (saved / ledger.total_naive * 100) if ledger.total_naive > 0 else 0.0
    return SavingsReport(
        total_actual=ledger.total_actual,
        total_naive=ledger.total_naive,
        saved=saved,
        saved_pct=saved_pct,
    )
