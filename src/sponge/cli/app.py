"""Sponge CLI — Typer app with --version support."""

import typer

from sponge import __version__
from sponge.cli.config_cmd import config_app
from sponge.cli.run import run_task
from sponge.cli.session_cmd import session_app
from sponge.cli.tune_cmd import tune_app

app = typer.Typer(
    name="sponge",
    help="Cost-optimal AI agent harness — use the best model, pay the least.",
)

# Register subcommands.
app.command(name="run")(run_task)
app.add_typer(config_app, name="config")
app.add_typer(session_app, name="session")
app.add_typer(tune_app, name="tune")


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit.",
    ),
) -> None:
    """Sponge: use any model, pay less every time."""
    if version:
        typer.echo(__version__)
        raise typer.Exit()
