"""ShellPlugin — execute shell commands without LLM calls.

Pattern-matches command execution intent. All commands require
confirmation (--auto-approve). A blocklist prevents dangerous
commands from executing.
"""

from __future__ import annotations

import logging
import re

from sponge.plugins.base import (
    ApprovalLevel,
    Plugin,
    PluginContext,
    PluginMatch,
    PluginResult,
)

logger = logging.getLogger("sponge.plugins.shell")

# ── Pattern detection ──────────────────────────────────────────────

_SHELL_KEYWORDS = [
    r"\brun\s+(?:command\s+)?",
    r"\bexec(?:ute)?\s+(?:command\s+)?",
    r"\bshell:\s*",
]

_CMD_RE = re.compile(
    r"""(?:run|execute|exec|shell)[:\s]+["']?([^"']+?)["']?\s*$""",
    re.IGNORECASE,
)

# ── Dangerous command blocklist ────────────────────────────────────

_BLOCKLIST = [
    r"\brm\s+.*-r[a-z]*f[a-z]*\b",              # rm -rf / rm -r / rm -rf /*
    r"\brm\s+.*-f[a-z]*r[a-z]*\b",              # rm -fr
    r"\brm\s+.*--recursive\b",                    # rm --recursive
    r"\brmdir\b.*\*/?\s*$",                        # rmdir with wildcard
    r"\bsudo\b",                                   # sudo
    r"\bsu\s",                                    # su (switch user)
    r"\bdoas\b",                                   # doas (OpenBSD sudo alt)
    r"\bpkexec\b",                                 # pkexec (polkit)
    r"\bchmod\s+.*777\b",                         # chmod 777
    r"\bchmod\s+.*-R[a-z]*\s+777\b",             # chmod -R 777
    r"\bchown\s+.*root\b",                        # chown root
    r"\bmkfs\b",                                   # mkfs
    r"\bdd\s+if=",                                # dd
    r"\b:\(\)\s*\{\s*:\|:&\s*\}\s*;\s*:",         # fork bomb
    r">\s*/dev/sd[a-z]",                           # redirect to raw device
    r">\s*/dev/mmcblk",                            # redirect to mmc device
    r">\s*/dev/nvme",                              # redirect to nvme device
    r"\bcurl\b.*\|\s*(?:ba)?sh\b",               # curl | bash/sh
    r"\bcurl\b.*\|\s*zsh\b",                      # curl | zsh
    r"\bwget\b.*\|\s*(?:ba)?sh\b",               # wget | bash/sh
    r"\bwget\b.*\|\s*zsh\b",                      # wget | zsh
    r"\bwget\b.*-O\s*-\s*\|",                     # wget -O- |
    r"\bcurl\b.*-o\s*\S+\s*;",                    # curl download then script
    r"\bshutdown\b",                               # shutdown
    r"\breboot\b",                                 # reboot
    r"\bhalt\b",                                   # halt
    r"\bpoweroff\b",                               # poweroff
    r"\binit\s+[06]\b",                           # init runlevel 0/6
    r"\bsystemctl\s+(?:halt|poweroff|reboot)\b",  # systemctl shutdown
]


def _is_blocked(command: str) -> str | None:
    """Check if a command matches the blocklist. Returns the reason or None."""
    cmd_lower = command.lower()
    for pattern in _BLOCKLIST:
        if re.search(pattern, cmd_lower):
            return f"Blocked: matches dangerous pattern '{pattern}'"
    return None


def _extract_command(task: str) -> str | None:
    """Extract the shell command from a task string."""
    # Try explicit shell: prefix.
    m = re.search(r"\bshell:\s*(.+)", task, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # Try quoted command.
    m = re.search(r"""["'](.+?)["']""", task)
    if m:
        candidate = m.group(1)
        # Only match if it looks like a command (contains flags, pipes, or binaries).
        if re.search(r"[-|&;>]|\b[a-z]+\s", candidate):
            return candidate

    # Try "run X" or "execute X" — everything after keyword.
    m = _CMD_RE.search(task)
    if m:
        return m.group(1).strip()

    return None


def _detect_shell(task: str) -> tuple[str | None, float]:
    """Detect shell command intent. Returns (command, confidence)."""
    task_lower = task.lower()

    matched = False
    for kw in _SHELL_KEYWORDS:
        if re.search(kw, task_lower):
            matched = True
            break
    if not matched:
        return None, 0.0

    cmd = _extract_command(task)
    if cmd is None:
        return None, 0.0

    return cmd, 0.85


# ── Execution ───────────────────────────────────────────────────────

from sponge.sandbox.subprocess_sandbox import SubprocessSandbox  # noqa: E402

_sandbox = SubprocessSandbox(timeout_sec=30, max_output=5000)


def _run_command(cmd: str) -> PluginResult:
    """Execute a shell command in a sandbox and return the result."""
    result = _sandbox.run(cmd)

    output_parts: list[str] = [f"$ {cmd}\n"]
    if result.stdout:
        output_parts.append(result.stdout.strip())
    if result.stderr:
        output_parts.append(f"\n[stderr]\n{result.stderr.strip()}")
    if result.timed_out:
        output_parts.append("\n[timed out]")

    return PluginResult(
        output="".join(output_parts),
        success=result.exit_code == 0,
    )


# ── Plugin ──────────────────────────────────────────────────────────


class ShellPlugin(Plugin):
    """Handles shell command execution — $0 LLM cost.

    All commands require confirmation (CONFIRM). Use --auto-approve
    to bypass. Dangerous commands (rm -rf /, sudo, etc.) are always
    rejected.
    """

    name = "shell"
    description = "Run shell commands — $0 LLM cost. Requires --auto-approve."
    approval = ApprovalLevel.CONFIRM
    priority = 30

    def can_handle(self, task: str) -> PluginMatch | None:
        cmd, confidence = _detect_shell(task)
        if cmd is None:
            return None

        # Always reject blocklisted commands.
        blocked = _is_blocked(cmd)
        if blocked:
            return PluginMatch(
                plugin=self,
                confidence=confidence,
                args={"cmd": cmd, "blocked": blocked},
            )

        return PluginMatch(
            plugin=self,
            confidence=confidence,
            args={"cmd": cmd},
        )

    async def execute(self, context: PluginContext) -> PluginResult:
        cmd, _ = _detect_shell(context.task)
        if cmd is None:
            return PluginResult(output="Could not extract command.", success=False)

        blocked = _is_blocked(cmd)
        if blocked:
            return PluginResult(output=blocked, success=False)

        return _run_command(cmd)
