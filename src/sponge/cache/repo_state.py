"""Memoized repository state for cache and fingerprint modules.

Avoids repeated `git rev-parse` + `git status` subprocess calls.
State is cached for the process lifetime — git HEAD doesn't change
while a process is running.
"""

from __future__ import annotations

import subprocess

_repo_state_cache: str | None = None
_state_fetched: bool = False


def get_repo_state() -> str:
    """Return current git HEAD + dirty flag, memoized per process.

    Returns empty string if not in a git repo.
    """
    global _repo_state_cache, _state_fetched

    if _state_fetched:
        return _repo_state_cache or ""

    _state_fetched = True
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        _repo_state_cache = f"{head}{':dirty' if dirty else ''}"
    except (subprocess.CalledProcessError, FileNotFoundError):
        _repo_state_cache = ""

    return _repo_state_cache or ""
