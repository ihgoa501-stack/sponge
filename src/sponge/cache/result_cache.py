"""Exact-match result cache.

SHA256-based cache that stores LLM responses keyed by
(task + model + system_prompt + repo_state). Returns cached
responses for identical calls, saving the full model cost.
"""

import hashlib
import json

from sponge.cache.disk_store import DiskStore
from sponge.cache.repo_state import get_repo_state
from sponge.config.settings import Settings


class ResultCache:
    """Exact-match cache for LLM responses."""

    def __init__(self, store: DiskStore, settings: Settings) -> None:
        self._store = store
        self._settings = settings

    def cache_key(
        self,
        task: str,
        model: str,
        system_prompt: str = "",
    ) -> str:
        """Build a SHA256 cache key from task inputs + repo state."""
        state = get_repo_state()
        ingredients = f"{task}|{model}|{system_prompt}|{state}"
        return hashlib.sha256(ingredients.encode()).hexdigest()

    def get(
        self,
        task: str,
        model: str,
        system_prompt: str = "",
    ) -> tuple[str, float] | None:
        """Return (cached_response, original_cost) or None on miss/expiry.

        The original_cost is what the LLM call cost when first cached,
        used as naive_cost on cache hits so the savings ledger is accurate.
        """
        if not self._settings.cache_enabled:
            return None
        key = self.cache_key(task, model, system_prompt)
        raw = self._store.get(key)
        if raw is None:
            return None
        try:
            data = json.loads(raw)
            return (data["r"], data.get("c", 0.0))
        except (json.JSONDecodeError, KeyError, TypeError):
            # Legacy cache entries (plain text, no cost).
            return (raw, 0.0)

    def set(
        self,
        task: str,
        model: str,
        system_prompt: str,
        response: str,
        cost: float = 0.0,
    ) -> None:
        """Store a response + cost in cache as JSON."""
        if not self._settings.cache_enabled:
            return
        key = self.cache_key(task, model, system_prompt)
        payload = json.dumps({"r": response, "c": cost})
        self._store.set(key, payload, ttl_hours=self._settings.cache_ttl_hours)
