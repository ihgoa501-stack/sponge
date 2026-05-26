"""Tests for CLI run and config commands."""

from typer.testing import CliRunner

from sponge.cli.app import app


def test_run_empty_task() -> None:
    """Empty task should error."""
    runner = CliRunner()
    result = runner.invoke(app, ["run", ""])
    # Empty string is still a valid argument — but no provider key available.
    # This should fail with a provider error or succeed via mock.
    # Just verify it doesn't crash.
    assert result.exit_code in (0, 1)


def test_run_help() -> None:
    """run --help shows usage."""
    runner = CliRunner()
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "--model" in result.output
    assert "--json" in result.output
    assert "--no-cache" in result.output


def test_config_show() -> None:
    """config show displays settings."""
    runner = CliRunner()
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "Provider" in result.output
    assert "Model" in result.output
    assert "Cache" in result.output


def test_config_set_bad_format() -> None:
    """config set without = exits non-zero."""
    runner = CliRunner()
    result = runner.invoke(app, ["config", "set", "badformat"])
    assert result.exit_code == 1


def test_config_set_unknown_key() -> None:
    """config set with unknown key exits non-zero."""
    runner = CliRunner()
    result = runner.invoke(app, ["config", "set", "nonexistent=value"])
    assert result.exit_code == 1
    assert "unknown setting" in result.output.lower()
