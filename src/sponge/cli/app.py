"""Sponge CLI — Typer app with --version support."""

import typer

from sponge import __version__
from sponge.cli.benchmark_cmd import run_benchmark
from sponge.cli.config_cmd import config_app
from sponge.cli.cost_cmd import cost_app
from sponge.cli.desktop_cmd import run_desktop
from sponge.cli.memory_cmd import memory_app
from sponge.cli.reflections_cmd import reflections_app
from sponge.cli.run import run_task
from sponge.cli.session_cmd import session_app
from sponge.cli.tune_cmd import tune_app
from sponge.utils.logging import setup_logging

setup_logging()

app = typer.Typer(
    name="sponge",
    help="Cost-optimal AI agent harness — use the best model, pay the least.",
)

# Register subcommands.
app.command(name="run")(run_task)
app.command(name="benchmark")(run_benchmark)
app.command(name="desktop")(run_desktop)
app.add_typer(config_app, name="config")
app.add_typer(session_app, name="session")
app.add_typer(tune_app, name="tune")
app.add_typer(memory_app, name="memory")
app.add_typer(reflections_app, name="reflections")
app.add_typer(cost_app, name="cost")


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
