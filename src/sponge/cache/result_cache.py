"""Exact-match result cache.

SHA256-based cache that stores LLM responses keyed by
(task + model + system_prompt + repo_state). Returns cached
responses for identical calls, saving the full model cost.
"""

import hashlib
import subprocess

from sponge.cache.disk_store import DiskStore
from sponge.config.settings import Settings


def _repo_state() -> str:
    """Capture current git HEAD + dirty flag as a state marker.

    Returns empty string if not in a git repo.
    """
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        # Check for uncommitted changes
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return f"{head}{':dirty' if dirty else ''}"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


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
        state = _repo_state()
        ingredients = f"{task}|{model}|{system_prompt}|{state}"
        return hashlib.sha256(ingredients.encode()).hexdigest()

    def get(
        self,
        task: str,
        model: str,
        system_prompt: str = "",
    ) -> str | None:
        """Return cached response or None on miss/expiry."""
        if not self._settings.cache_enabled:
            return None
        key = self.cache_key(task, model, system_prompt)
        return self._store.get(key)

    def set(
        self,
        task: str,
        model: str,
        system_prompt: str,
        response: str,
    ) -> None:
        """Store a response in cache."""
        if not self._settings.cache_enabled:
            return
        key = self.cache_key(task, model, system_prompt)
        self._store.set(key, response, ttl_hours=self._settings.cache_ttl_hours)
