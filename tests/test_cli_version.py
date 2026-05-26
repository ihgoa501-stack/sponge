"""Tests for the Sponge CLI version command."""

from typer.testing import CliRunner

from sponge import __version__
from sponge.cli.app import app


def test_cli_version() -> None:
    """sponge --version prints the version and exits with status 0."""
    runner = CliRunner()

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.output
