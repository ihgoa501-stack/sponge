"""Tests for disk store and result cache."""

import tempfile
from pathlib import Path

from sponge.cache.disk_store import DiskStore
from sponge.cache.result_cache import ResultCache
from sponge.config.settings import Settings


def test_disk_store_set_get() -> None:
    """DiskStore can set and get values."""
    with tempfile.TemporaryDirectory() as tmp:
        store = DiskStore(Path(tmp) / "store.db")
        store.set("hello", "world")
        assert store.get("hello") == "world"


def test_disk_store_missing_key() -> None:
    """DiskStore returns None for missing keys."""
    with tempfile.TemporaryDirectory() as tmp:
        store = DiskStore(Path(tmp) / "store.db")
        assert store.get("nonexistent") is None


def test_disk_store_delete() -> None:
    """DiskStore can delete keys."""
    with tempfile.TemporaryDirectory() as tmp:
        store = DiskStore(Path(tmp) / "store.db")
        store.set("key", "val")
        store.delete("key")
        assert store.get("key") is None


def test_disk_store_expiry() -> None:
    """DiskStore returns None for expired keys (TTL=0 immediately expires)."""
    with tempfile.TemporaryDirectory() as tmp:
        store = DiskStore(Path(tmp) / "store.db")
        store.set("key", "val", ttl_hours=0)
        assert store.get("key") is None
        assert store.cleanup_expired() >= 0


def test_result_cache_hit() -> None:
    """ResultCache returns cached response on exact match."""
    with tempfile.TemporaryDirectory() as tmp:
        store = DiskStore(Path(tmp) / "store.db")
        settings = Settings(cache_enabled=True, cache_ttl_hours=24)
        cache = ResultCache(store, settings)

        assert cache.get("hello", "claude-sonnet-4") is None
        cache.set("hello", "claude-sonnet-4", "", "world")
        assert cache.get("hello", "claude-sonnet-4") == "world"


def test_result_cache_miss_different_task() -> None:
    """Different tasks produce different cache keys."""
    with tempfile.TemporaryDirectory() as tmp:
        store = DiskStore(Path(tmp) / "store.db")
        settings = Settings(cache_enabled=True)
        cache = ResultCache(store, settings)

        cache.set("task-a", "claude-sonnet-4", "", "response-a")
        assert cache.get("task-b", "claude-sonnet-4") is None


def test_result_cache_disabled() -> None:
    """Disabled cache always returns None."""
    with tempfile.TemporaryDirectory() as tmp:
        store = DiskStore(Path(tmp) / "store.db")
        settings = Settings(cache_enabled=False)
        cache = ResultCache(store, settings)

        cache.set("hello", "claude-sonnet-4", "", "world")
        assert cache.get("hello", "claude-sonnet-4") is None


def test_disk_store_cleanup_expired() -> None:
    """Cleanup removes expired entries."""
    with tempfile.TemporaryDirectory() as tmp:
        store = DiskStore(Path(tmp) / "store.db")
        store.set("keep", "val", ttl_hours=24)
        store.set("expire", "val", ttl_hours=0)
        removed = store.cleanup_expired()
        assert removed >= 1
        assert store.get("keep") == "val"
        assert store.get("expire") is None


def test_disk_store_list_by_prefix() -> None:
    """list_by_prefix returns matching non-expired entries."""
    with tempfile.TemporaryDirectory() as tmp:
        store = DiskStore(Path(tmp) / "store.db")
        store.set("sem:abc", "v1", ttl_hours=24)
        store.set("sem:xyz", "v2", ttl_hours=24)
        store.set("other:1", "v3", ttl_hours=24)
        store.set("sem:exp", "v4", ttl_hours=0)

        results = store.list_by_prefix("sem:")
        assert len(results) == 2
        keys = {r[0] for r in results}
        assert "sem:abc" in keys
        assert "sem:xyz" in keys
        assert "sem:exp" not in keys  # expired
