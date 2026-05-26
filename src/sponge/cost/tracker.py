"""Cost tracker — incremental cost accounting for streaming responses.

Tracks cost as tokens arrive during streaming. Compute actual cost
from pricing data and naive cost (what it would cost without caching).
"""

from sponge.cost.models import CostEntry, ModelPricing, Usage


class CostTracker:
    """Tracks cost for a single LLM call.

    Usage:
        tracker = CostTracker(pricing)
        # During streaming:
        tracker.record_output_tokens(chunk_tokens)
        # At stream end:
        tracker.record_usage(usage)
        entry = tracker.finalize(model="claude-sonnet-4")
    """

    def __init__(self, pricing: ModelPricing) -> None:
        self._pricing = pricing
        self._input_tokens = 0
        self._output_tokens = 0
        self._cache_read_tokens = 0
        self._cache_write_tokens = 0

    def record_usage(self, usage: Usage) -> None:
        """Record final token counts from a UsageEvent."""
        self._input_tokens = usage.tokens_in
        self._output_tokens = usage.tokens_out
        self._cache_read_tokens = usage.cache_read_tokens
        self._cache_write_tokens = usage.cache_write_tokens

    @property
    def actual_cost(self) -> float:
        """Compute actual cost including cache savings.

        Cache-hit input tokens are charged at cache_read rate,
        non-cache input tokens at full input rate.
        Cache writes add cost at cache_write rate.
        """
        total_input = self._input_tokens / 1000.0
        total_output = self._output_tokens / 1000.0

        # Input cost: cache-hit tokens at read rate, rest at full rate.
        cache_read_k = (self._cache_read_tokens / 1000.0) if self._cache_read_tokens > 0 else 0.0
        uncached_input_k = total_input - cache_read_k

        read_rate = self._pricing.cache_read_per_1k or 0.0
        input_cost = uncached_input_k * self._pricing.input_per_1k + cache_read_k * read_rate
        output_cost = total_output * self._pricing.output_per_1k

        cache_write_cost = 0.0
        if self._cache_write_tokens > 0 and self._pricing.cache_write_per_1k:
            cache_write_cost = (
                self._cache_write_tokens / 1000.0
            ) * self._pricing.cache_write_per_1k

        return input_cost + output_cost + cache_write_cost

    @property
    def naive_cost(self) -> float:
        """Compute what this call would cost with zero caching."""
        return (self._input_tokens / 1000.0) * self._pricing.input_per_1k + (
            self._output_tokens / 1000.0
        ) * self._pricing.output_per_1k

    def finalize(self, model: str) -> CostEntry:
        """Produce the final CostEntry for this call."""
        return CostEntry(
            usage=Usage(
                tokens_in=self._input_tokens,
                tokens_out=self._output_tokens,
                cache_read_tokens=self._cache_read_tokens,
                cache_write_tokens=self._cache_write_tokens,
            ),
            model=model,
            cost=round(self.actual_cost, 6),
            naive_cost=round(self.naive_cost, 6),
        )
