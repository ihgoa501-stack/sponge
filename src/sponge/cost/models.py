"""Cost model types for Sponge."""

from dataclasses import dataclass, field


@dataclass
class ModelPricing:
    """Pricing for a specific model in USD per 1M tokens."""

    input_per_1k: float
    output_per_1k: float
    cache_write_per_1k: float | None = None
    cache_read_per_1k: float | None = None


@dataclass
class Usage:
    """Token usage from a single LLM call."""

    tokens_in: int
    tokens_out: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass
class CostEntry:
    """Cost breakdown for a single call."""

    usage: Usage
    model: str
    cost: float
    naive_cost: float


@dataclass
class SavingsLedger:
    """Accumulated cost across a session with savings breakdown."""

    entries: list[CostEntry] = field(default_factory=list)

    @property
    def total_actual(self) -> float:
        return sum(e.cost for e in self.entries)

    @property
    def total_naive(self) -> float:
        return sum(e.naive_cost for e in self.entries)

    @property
    def saved_by_cache(self) -> float:
        return self.total_naive - self.total_actual

    def add(self, entry: CostEntry) -> None:
        self.entries.append(entry)
