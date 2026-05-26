"""Semantic cache — similarity-based cache with state guards.

Uses a simple token-overlap approach (no embedding model required)
to find similar past queries. Only returns cached results when
the repository state matches.

Optionally backed by DiskStore for persistence across restarts.
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sponge.cache.disk_store import DiskStore

logger = logging.getLogger("sponge.cache.semantic")


class SemanticCache:
    """Finds cached responses for similar-but-not-identical queries.

    Uses Jaccard similarity on tokenized queries. Requires matching
    repo state (git HEAD) to prevent stale responses.
    """

    _PREFIX = "sem:"
    _DEFAULT_MAX_ENTRIES = 1000

    def __init__(
        self,
        threshold: float = 0.7,
        store: DiskStore | None = None,
        max_entries: int = _DEFAULT_MAX_ENTRIES,
    ) -> None:
        self._threshold = threshold
        self._disk = store
        self._max_entries = max_entries
        # In-memory hot cache: key → (query, response, repo_state)
        self._store: dict[str, tuple[str, str, str]] = {}
        if self._disk is not None:
            self._load_from_disk()

    def _repo_state(self) -> str:
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""

    def _tokenize(self, text: str) -> set[str]:
        return set(text.lower().split())

    def _jaccard(self, a: set[str], b: set[str]) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def get(self, query: str) -> str | None:
        """Return cached response if a similar query exists with same repo state."""
        current_state = self._repo_state()
        query_tokens = self._tokenize(query)

        best_score = 0.0
        best_response = None

        for stored_query, stored_response, stored_state in self._store.values():
            if stored_state != current_state:
                continue
            score = self._jaccard(query_tokens, self._tokenize(stored_query))
            if score >= self._threshold and score > best_score:
                best_score = score
                best_response = stored_response

        return best_response

    def set(self, query: str, response: str) -> None:
        """Store a query-response pair for future semantic matching."""
        state = self._repo_state()
        key = hashlib.sha256(query.encode()).hexdigest()[:16]
        # Evict oldest entry if at capacity and key is new.
        if key not in self._store and len(self._store) >= self._max_entries:
            oldest = next(iter(self._store))
            del self._store[oldest]
            logger.debug("Semantic cache: evicted oldest entry (limit=%d)", self._max_entries)
        self._store[key] = (query, response, state)

        if self._disk is not None:
            try:
                payload = json.dumps({"q": query, "r": response, "s": state})
                self._disk.set(self._PREFIX + key, payload, ttl_hours=24 * 7)
            except Exception:
                logger.debug("Failed to persist semantic cache entry", exc_info=True)

    def _load_from_disk(self) -> None:
        """Load all semantic cache entries from disk into memory."""
        if self._disk is None:
            return
        try:
            for key, raw in self._disk.list_by_prefix(self._PREFIX):
                try:
                    data = json.loads(raw)
                    short_key = key[len(self._PREFIX):]  # strip prefix
                    self._store[short_key] = (data["q"], data["r"], data["s"])
                except (json.JSONDecodeError, KeyError):
                    logger.debug("Skipping corrupt semantic cache entry", exc_info=True)
        except Exception:
            logger.debug("Failed to load semantic cache from disk", exc_info=True)
