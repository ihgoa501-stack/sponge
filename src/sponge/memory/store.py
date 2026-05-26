"""Project memory — cross-session persistent context.

Stored in .sponge/memory.toml. Injected into the system prompt at the
start of every task so the agent remembers project conventions and
user preferences without repeating them.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("sponge.memory")


class ProjectMemory:
    """Reads and writes project-level memory from .sponge/memory.toml.

    Format:
        [memory]
        rules = [
            "Never touch test/fixtures/",
            "Use httpx not requests",
        ]
    """

    DEFAULT_PATH = Path(".sponge") / "memory.toml"

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or self.DEFAULT_PATH

    @property
    def path(self) -> Path:
        return self._path

    @property
    def exists(self) -> bool:
        return self._path.is_file()

    def load(self) -> list[str]:
        """Load all memory rules. Returns empty list if no file exists."""
        if not self._path.is_file():
            return []
        try:
            import tomllib

            data = tomllib.loads(self._path.read_text())
            return list(data.get("memory", {}).get("rules", []))
        except Exception:
            logger.warning("Failed to parse %s", self._path, exc_info=True)
            return []

    def save(self, rules: list[str]) -> None:
        """Save memory rules to TOML."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # Quote strings so TOML stays readable.
        lines = ["[memory]\n", "rules = [\n"]
        for rule in rules:
            escaped = rule.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'  "{escaped}",\n')
        lines.append("]\n")
        self._path.write_text("".join(lines))

    def add(self, rule: str) -> None:
        """Add a rule and save."""
        rules = self.load()
        if rule not in rules:
            rules.append(rule)
        self.save(rules)

    def remove(self, index: int) -> bool:
        """Remove a rule by index. Returns False if out of range."""
        rules = self.load()
        if index < 0 or index >= len(rules):
            return False
        rules.pop(index)
        self.save(rules)
        return True

    def to_system_prompt(self) -> str:
        """Render memory as a system prompt block."""
        rules = self.load()
        if not rules:
            return ""
        lines = ["## Project Memory", ""]
        for i, rule in enumerate(rules, 1):
            lines.append(f"{i}. {rule}")
        lines.append("")
        return "\n".join(lines)
