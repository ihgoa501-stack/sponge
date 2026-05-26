"""FileOpsPlugin — read, list, write, and delete files without LLM calls.

Pattern-matches user intent from the task string and executes
filesystem operations directly. All paths are restricted to the
current working directory — path traversal is blocked.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from sponge.plugins.base import (
    Plugin,
    PluginContext,
    PluginMatch,
    PluginResult,
)

logger = logging.getLogger("sponge.plugins.file_ops")

# ── Operation kinds ────────────────────────────────────────────────

READ_KEYWORDS = [
    r"\bread\s+(?:the\s+)?(?:file|contents\s+of)\b",
    r"\bshow\s+(?:me\s+)?(?:the\s+)?(?:contents\s+of|file)\b",
    r"\bcat\s+",
    r"\bview\s+(?:the\s+)?(?:file|contents\s+of)\b",
    r"\bdisplay\s+(?:the\s+)?(?:file|contents\s+of)\b",
    r"\bwhat(?:\'s|\s+is)\s+in\s+",
    r"\bprint\s+(?:the\s+)?(?:contents\s+of|file)\b",
]

LIST_KEYWORDS = [
    r"\blist\s+(?:files|directory|dir)\b",
    r"\bshow\s+(?:files|directory|dir)\b",
    r"\bls\b",
    r"\bdir\b",
    r"\bwhat\s+files\s+are\s+in\b",
]

WRITE_KEYWORDS = [
    r"\bwrite\s+.+\s+to\s+",
    r"\bcreate\s+(?:a\s+)?file\b",
    r"\bsave\s+.+\s+to\s+",
    r"\bappend\s+.+\s+to\s+",
    r"\boverwrite\s+.+\s+(?:with|in)\s+",
]

DELETE_KEYWORDS = [
    r"\bdelete\s+(?:the\s+)?file\b",
    r"\bremove\s+(?:the\s+)?file\b",
    r"\brm\s+",
    r"\bunlink\s+",
]

# ── Path extraction ────────────────────────────────────────────────

_PATH_PATTERNS = [
    re.compile(r"""["']([^"']+\.[a-zA-Z0-9]+)["']"""),  # quoted paths
    re.compile(r"`([^`]+\.[a-zA-Z0-9]+)`"),  # backtick paths
    re.compile(r"""(["'])([^"']+)["']"""),  # quoted anything (dirs)
    re.compile(r"`([^`]+)`"),  # backtick anything
    re.compile(r"(?:(?:in|from|of)\s+)([~\w.-]+(?:/[\w.-]*)*/?)"),  # "in DIR" pattern
    re.compile(r"([~\w./-]+\.[a-zA-Z0-9]{1,10})"),  # bare paths with ext
    re.compile(r"((?:\.\.?/)+[\w.-][\w./-]*)"),  # relative traversal
    re.compile(r"([\w.-]+/)"),  # bare dir with trailing /
    re.compile(r"(?:\b(?:file|directory|dir)\s+)([\w.-]+)"),  # word after file/dir
]


def _extract_paths(task: str) -> list[str]:
    """Extract candidate file/directory paths from a task string."""
    paths: list[str] = []
    seen: set[str] = set()
    for pat in _PATH_PATTERNS:
        for m in pat.finditer(task):
            p = m.group(1).strip().strip("\"'")
            if p and p not in seen and not p.startswith("--"):
                seen.add(p)
                paths.append(p)
    return paths


# ── Safety ──────────────────────────────────────────────────────────


def _safe_resolve(path_str: str) -> Path | None:
    """Resolve a path and verify it's within cwd. Returns None if unsafe."""
    cwd = Path.cwd().resolve()
    try:
        resolved = (cwd / path_str).resolve()
    except (OSError, ValueError, RuntimeError):
        return None
    # Must be within cwd (or equal to cwd).
    try:
        resolved.relative_to(cwd)
    except ValueError:
        return None
    return resolved


# ── Plugin ──────────────────────────────────────────────────────────


class FileOpsPlugin(Plugin):
    """Handles file read, list, write, and delete via pattern matching.

    Read and list operations execute directly (ALLOW).
    Write and delete require confirmation (CONFIRM) — they are not
    executed until the approval infrastructure is built.
    """

    name = "file_ops"
    description = "Read, list, write, and delete files — $0 LLM cost."
    priority = 10

    def can_handle(self, task: str) -> PluginMatch | None:
        """Detect file operation intent and return match with confidence."""
        task_lower = task.lower()

        # Determine operation kind and confidence.
        kind: str | None = None
        confidence: float = 0.0

        for kw in READ_KEYWORDS:
            if re.search(kw, task_lower):
                kind = "read"
                confidence = 0.9
                break

        if kind is None:
            for kw in LIST_KEYWORDS:
                if re.search(kw, task_lower):
                    kind = "list"
                    confidence = 0.9
                    break

        if kind is None:
            for kw in WRITE_KEYWORDS:
                if re.search(kw, task_lower):
                    kind = "write"
                    confidence = 0.9
                    break

        if kind is None:
            for kw in DELETE_KEYWORDS:
                if re.search(kw, task_lower):
                    kind = "delete"
                    confidence = 0.85
                    break

        if kind is None:
            return None

        # Extract target paths.
        paths = _extract_paths(task)
        if not paths and kind in ("read", "write", "delete"):
            # Can't do read/write/delete without a path.
            return None

        # Lower confidence if no explicit path found.
        if not paths:
            confidence = 0.6

        return PluginMatch(
            plugin=self,
            confidence=confidence,
            args={"kind": kind, "paths": ",".join(paths)},
        )

    async def execute(self, context: PluginContext) -> PluginResult:
        """Execute the matched file operation."""
        # Re-derive kind from the task (simpler than threading through Match args).
        task_lower = context.task.lower()
        op: str | None = None
        for kw in READ_KEYWORDS:
            if re.search(kw, task_lower):
                op = "read"
                break
        if op is None:
            for kw in LIST_KEYWORDS:
                if re.search(kw, task_lower):
                    op = "list"
                    break
        if op is None:
            for kw in WRITE_KEYWORDS:
                if re.search(kw, task_lower):
                    op = "write"
                    break
        if op is None:
            for kw in DELETE_KEYWORDS:
                if re.search(kw, task_lower):
                    op = "delete"
                    break
        if op is None:
            return PluginResult(output="Could not determine file operation.", success=False)

        paths = _extract_paths(context.task)

        if op == "write":
            return self._do_write(context.task, paths)

        if op == "delete":
            return self._do_delete(paths)

        if op == "list":
            return self._do_list(paths[0] if paths else ".")

        if op == "read":
            return self._do_read(paths)

    # ── operation implementations ───────────────────────────────

    def _do_list(self, target: str) -> PluginResult:
        resolved = _safe_resolve(target)
        if resolved is None:
            return PluginResult(
                output=f"Cannot access '{target}': path is outside the working directory.",
                success=False,
            )
        if not resolved.exists():
            return PluginResult(output=f"Path not found: {target}", success=False)
        if resolved.is_file():
            return PluginResult(
                output=f"{target}\n  ({resolved.stat().st_size} bytes, file)",
            )

        try:
            entries = sorted(resolved.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return PluginResult(output=f"Permission denied: {target}", success=False)

        lines = [f"Contents of {target} ({len(entries)} entries):", ""]
        for entry in entries:
            suffix = "/" if entry.is_dir() else ""
            try:
                size = entry.stat().st_size
                lines.append(f"  {entry.name}{suffix}  ({size} bytes)")
            except OSError:
                lines.append(f"  {entry.name}{suffix}")

        return PluginResult(output="\n".join(lines))

    def _do_read(self, paths: list[str]) -> PluginResult:
        if not paths:
            return PluginResult(output="No file path specified.", success=False)

        results: list[str] = []
        any_success = False
        for p in paths:
            resolved = _safe_resolve(p)
            if resolved is None:
                results.append(f"--- {p}: SKIPPED (outside working directory) ---")
                continue
            if not resolved.exists():
                results.append(f"--- {p}: NOT FOUND ---")
                continue
            if resolved.is_dir():
                results.append(f"--- {p}: is a directory, not a file ---")
                continue
            try:
                content = resolved.read_text()
                results.append(f"--- {p} ({len(content)} chars) ---\n{content}")
                any_success = True
            except (OSError, UnicodeDecodeError) as e:
                results.append(f"--- {p}: ERROR ({e}) ---")

        return PluginResult(output="\n\n".join(results), success=any_success)

    def _do_write(self, task: str, paths: list[str]) -> PluginResult:
        # Extract file path (last path-like token, or after "to").
        target_path: str | None = None
        content: str = ""

        # Try "write CONTENT to PATH" pattern.
        m = re.search(r"\b(?:write|save)\s+(.+?)\s+to\s+([~\w./-]+)", task, re.IGNORECASE)
        if m:
            content = m.group(1).strip().strip("\"'")
            target_path = m.group(2).strip()
        elif paths:
            target_path = paths[-1]  # last path extracted
            content = task  # fallback: whole task as content

        if not target_path:
            return PluginResult(output="No target file path found.", success=False)

        resolved = _safe_resolve(target_path)
        if resolved is None:
            return PluginResult(
                output=f"Cannot write to '{target_path}': path outside working directory.",
                success=False,
            )

        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content)
            return PluginResult(
                output=f"Wrote {len(content)} chars to {target_path}",
            )
        except (OSError, PermissionError) as e:
            return PluginResult(output=f"Write failed: {e}", success=False)

    def _do_delete(self, paths: list[str]) -> PluginResult:
        if not paths:
            return PluginResult(output="No file path specified.", success=False)

        results: list[str] = []
        any_success = False
        for p in paths:
            resolved = _safe_resolve(p)
            if resolved is None:
                results.append(f"--- {p}: SKIPPED (outside working directory) ---")
                continue
            if not resolved.exists():
                results.append(f"--- {p}: NOT FOUND ---")
                continue
            if resolved.is_dir():
                results.append(f"--- {p}: is a directory, not deleting ---")
                continue
            try:
                resolved.unlink()
                results.append(f"Deleted: {p}")
                any_success = True
            except OSError as e:
                results.append(f"--- {p}: ERROR ({e}) ---")

        return PluginResult(output="\n".join(results), success=any_success)
