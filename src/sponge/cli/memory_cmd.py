"""sponge memory — manage project memory."""

import typer

from sponge.memory.store import ProjectMemory

memory_app = typer.Typer(name="memory", help="Manage project memory (.sponge/memory.toml).")


@memory_app.command(name="list")
def memory_list() -> None:
    """List all memory rules."""
    mem = ProjectMemory()
    rules = mem.load()
    if not rules:
        typer.echo("No memory rules. Add one with: sponge memory add \"rule\"")
        return

    typer.echo("Project Memory (.sponge/memory.toml)")
    typer.echo("─" * 50)
    for i, rule in enumerate(rules, 1):
        typer.echo(f"  {i}. {rule}")


@memory_app.command(name="add")
def memory_add(
    rule: str = typer.Argument(..., help="Memory rule to add."),
) -> None:
    """Add a memory rule."""
    mem = ProjectMemory()
    mem.add(rule)
    typer.echo(f"Added: {rule}")


@memory_app.command(name="remove")
def memory_remove(
    index: str = typer.Argument(..., help="Rule number to remove (from 'sponge memory list')."),
) -> None:
    """Remove a memory rule by its number."""
    try:
        idx = int(index) - 1
    except ValueError:
        typer.echo(f"Invalid index: {index} (use a number from 'sponge memory list')", err=True)
        raise typer.Exit(code=1) from None

    mem = ProjectMemory()
    if mem.remove(idx):
        typer.echo(f"Removed rule {index}.")
    else:
        typer.echo(f"No rule at position {index}.", err=True)
        raise typer.Exit(code=1)
