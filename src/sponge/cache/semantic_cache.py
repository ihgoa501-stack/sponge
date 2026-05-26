"""Semantic cache — similarity-based cache with state guards.

Uses a simple token-overlap approach (no embedding model required)
to find similar past queries. Only returns cached results when
the repository state matches.
"""

import hashlib
import subprocess


class SemanticCache:
    """Finds cached responses for similar-but-not-identical queries.

    Uses Jaccard similarity on tokenized queries. Requires matching
    repo state (git HEAD) to prevent stale responses.
    """

    def __init__(self, threshold: float = 0.7) -> None:
        self._threshold = threshold
        self._store: dict[str, tuple[str, str, str]] = {}  # key → (query, response, repo_state)

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
        """Simple whitespace tokenization, lowercased."""
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
        self._store[key] = (query, response, state)
