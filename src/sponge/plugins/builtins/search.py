"""SearchPlugin — grep-based code search without LLM calls.

Pattern-matches search intent from the task string and runs
grep/ripgrep directly. All searches are restricted to the
current working directory and timeout after 10 seconds.
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from sponge.plugins.base import (
    ApprovalLevel,
    Plugin,
    PluginContext,
    PluginMatch,
    PluginResult,
)

logger = logging.getLogger("sponge.plugins.search")

# ── Pattern detection ──────────────────────────────────────────────

_SEARCH_KEYWORDS = [
    r"\bsearch\s+(?:for\s+)?",
    r"\bfind\s+(?:all\s+)?(?:occurrences?\s+of\s+)?",
    r"\bgrep\s+(?:for\s+)?",
    r"\blook\s+for\s+",
    r"\blocate\s+(?:all\s+)?",
]

# Extract quoted pattern or word after keyword.
_PATTERN_RE = re.compile(r"""["']([^"']+)["']""")  # quoted pattern
_IN_DIR_RE = re.compile(r"\bin\s+([~\w./-]+(?:/[\w.-]*)*/?)")  # trailing "in DIR"
_WORD_PATTERN_RE = re.compile(
    r"(?:search\s+(?:for\s+)?|find\s+(?:all\s+)?"
    r"(?:occurrences?\s+of\s+)?|grep\s+(?:for\s+)?|"
    r"look\s+for\s+|locate\s+(?:all\s+)?)"
    r"([\w.-]+)"  # single word pattern
)


def _detect_search(task: str) -> tuple[str | None, str | None, float]:
    """Detect search intent. Returns (pattern, directory, confidence)."""
    task_lower = task.lower()

    # Must match a search keyword.
    matched = False
    for kw in _SEARCH_KEYWORDS:
        if re.search(kw, task_lower):
            matched = True
            break
    if not matched:
        return None, None, 0.0

    # Extract search pattern.
    pattern: str | None = None
    m = _PATTERN_RE.search(task)
    if m:
        pattern = m.group(1)
    else:
        # Try single word after keyword.
        m = _WORD_PATTERN_RE.search(task_lower)
        if m:
            pattern = m.group(1)

    if not pattern:
        return None, None, 0.0

    # Extract target directory.
    directory: str | None = None
    m = _IN_DIR_RE.search(task)
    if m:
        directory = m.group(1)

    confidence = 0.9 if directory else 0.85
    return pattern, directory, confidence


# ── Execution ───────────────────────────────────────────────────────

_SEARCH_TIMEOUT = 10  # seconds
_MAX_OUTPUT_LINES = 200


def _run_grep(pattern: str, directory: str) -> PluginResult:
    """Run grep in the given directory (relative to cwd)."""
    cwd = Path.cwd()
    target = (cwd / directory).resolve() if directory else cwd

    # Safety check.
    try:
        target.relative_to(cwd)
    except ValueError:
        return PluginResult(
            output=f"Cannot search '{directory}': outside working directory.",
            success=False,
        )

    if not target.exists():
        return PluginResult(output=f"Directory not found: {directory}", success=False)

    # Try rg first, fall back to grep.
    try:
        result = subprocess.run(
            ["rg", "--line-number", "--no-heading", "--color=never", "-i", pattern, str(target)],
            capture_output=True,
            text=True,
            timeout=_SEARCH_TIMEOUT,
        )
    except FileNotFoundError:
        try:
            result = subprocess.run(
                ["grep", "-rni", "--color=never", pattern, str(target)],
                capture_output=True,
                text=True,
                timeout=_SEARCH_TIMEOUT,
            )
        except FileNotFoundError:
            return PluginResult(
                output="Neither rg (ripgrep) nor grep found on this system.",
                success=False,
            )
    except subprocess.TimeoutExpired:
        return PluginResult(
            output=f"Search timed out after {_SEARCH_TIMEOUT}s. Try narrowing the scope.",
            success=False,
        )

    if result.returncode not in (0, 1):  # 0 = matches, 1 = no matches
        return PluginResult(
            output=f"Search error: {result.stderr.strip()[:500]}",
            success=False,
        )

    lines = result.stdout.strip().split("\n")
    if not lines or lines == [""]:
        return PluginResult(output=f"No matches for '{pattern}' in {directory or '.'}")

    total = len(lines)
    truncated = total > _MAX_OUTPUT_LINES
    lines = lines[:_MAX_OUTPUT_LINES]

    # Make paths relative to cwd for readability.
    cwd_str = str(cwd) + "/"
    clean_lines = []
    for line in lines:
        if line.startswith(cwd_str):
            line = line[len(cwd_str):]
        clean_lines.append(line)

    header = f"Search results for '{pattern}' in {directory or '.'} ({total} matches"
    if truncated:
        header += f", showing first {_MAX_OUTPUT_LINES}"
    header += "):\n"

    return PluginResult(output=header + "\n".join(clean_lines))


# ── Plugin ──────────────────────────────────────────────────────────


class SearchPlugin(Plugin):
    """Handles code search via grep/ripgrep — $0 LLM cost."""

    name = "search"
    description = "Search code for patterns using grep or ripgrep — $0 LLM cost."
    approval = ApprovalLevel.ALLOW
    priority = 20

    def can_handle(self, task: str) -> PluginMatch | None:
        pattern, directory, confidence = _detect_search(task)
        if pattern is None:
            return None

        return PluginMatch(
            plugin=self,
            confidence=confidence,
            args={"pattern": pattern, "directory": directory or ""},
        )

    async def execute(self, context: PluginContext) -> PluginResult:
        pattern, directory, _ = _detect_search(context.task)
        if pattern is None:
            return PluginResult(output="Could not determine search pattern.", success=False)

        return _run_grep(pattern, directory or ".")
