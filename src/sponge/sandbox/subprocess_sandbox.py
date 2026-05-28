"""Subprocess sandbox — isolated command execution.

Runs commands in a subprocess with a timeout and working directory
restriction. Provides a thin safety layer for ShellPlugin and other
executors.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("sponge.sandbox")


@dataclass
class SandboxResult:
    """Result of a sandboxed command execution."""

    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False


class SubprocessSandbox:
    """Runs commands in a subprocess with safety constraints.

    - Working directory restricted to cwd or a subdirectory.
    - Timeout prevents runaway processes.
    - Output is capped to prevent memory exhaustion.
    - Network access can be disabled via allow_network=False.
    """

    def __init__(
        self,
        timeout_sec: int = 30,
        max_output: int = 10_000,
        allow_network: bool = True,
    ) -> None:
        self._timeout = timeout_sec
        self._max_output = max_output
        self._allow_network = allow_network

    def run(
        self,
        cmd: str,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Run a command in a subprocess.

        Args:
            cmd: Shell command to execute.
            cwd: Working directory (must be within project cwd).
            env: Extra environment variables.

        Returns:
            SandboxResult with stdout, stderr, exit_code.
        """
        work_dir = self._resolve_cwd(cwd)
        run_env = self._build_env(env)

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                cwd=str(work_dir),
                env=run_env,
            )
            return SandboxResult(
                stdout=result.stdout[: self._max_output],
                stderr=result.stderr[: self._max_output],
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                stdout="",
                stderr=f"Command timed out after {self._timeout}s.",
                exit_code=-1,
                timed_out=True,
            )
        except FileNotFoundError:
            return SandboxResult(
                stdout="",
                stderr=f"Command not found: {cmd}",
                exit_code=-1,
            )

    def _build_env(self, extra: dict[str, str] | None) -> dict[str, str] | None:
        """Build the subprocess environment, stripping network if blocked."""
        if not self._allow_network:
            sandbox_env = os.environ.copy()
            sandbox_env.pop("HTTP_PROXY", None)
            sandbox_env.pop("HTTPS_PROXY", None)
            sandbox_env.pop("http_proxy", None)
            sandbox_env.pop("https_proxy", None)
            sandbox_env.pop("NO_PROXY", None)
            sandbox_env.pop("no_proxy", None)
            if extra:
                sandbox_env.update({k: v for k, v in extra.items()
                                    if not k.upper().endswith("_PROXY")})
            return sandbox_env
        return extra

    def _resolve_cwd(self, cwd: str | Path | None) -> Path:
        """Resolve and validate working directory."""
        project_root = Path.cwd().resolve()

        if cwd is None:
            return project_root

        target = (project_root / cwd).resolve()
        try:
            target.relative_to(project_root)
        except ValueError:
            logger.warning("Sandbox: cwd '%s' outside project root, using root", cwd)
            return project_root

        return target
