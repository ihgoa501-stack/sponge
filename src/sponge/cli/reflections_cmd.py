"""sponge reflections — manage reflective memory (lessons from failures).

> 木柱上的刻痕 — the carvings on the pillar

Reflective memory stores structured lessons extracted from agent failures.
Each lesson is immutable; it can be superseded but never deleted.
"""

from pathlib import Path

import typer

from sponge.memory.reflective import ReflectiveMemory

reflections_app = typer.Typer(
    name="reflections",
    help="Manage reflective memory — lessons learned from failures.",
)


@reflections_app.command(name="list")
def reflections_list(
    include_superseded: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Include superseded lessons.",
    ),
) -> None:
    """List all stored lessons, newest first."""
    mem = ReflectiveMemory()
    lessons = mem.list_all(include_superseded=include_superseded)

    if not lessons:
        typer.echo("No lessons stored yet. Lessons are created when the agent reflects on failures.")
        return

    active = [sl for sl in lessons if sl.supersedes is None]
    superseded = [sl for sl in lessons if sl.supersedes is not None]

    typer.echo(f"Reflective Memory ({mem.directory})")
    typer.echo(f"  {len(active)} active lessons")
    if superseded:
        typer.echo(f"  {len(superseded)} superseded (use --all to show)")
    typer.echo("─" * 70)

    for sl in lessons:
        superseded_marker = " [SUPERSEDED]" if sl.supersedes else ""
        typer.echo(f"  [{sl.id}]{superseded_marker}")
        typer.echo(f"    Lesson: {sl.lesson}")
        typer.echo(f"    When: {sl.condition}")
        typer.echo(f"    Severity: {sl.severity} | Retrieved: {sl.times_retrieved}x")
        typer.echo("")


@reflections_app.command(name="show")
def reflections_show(
    lesson_id: str = typer.Argument(..., help="Lesson ID to show (e.g. ref_a1b2c3d4)."),
) -> None:
    """Show full details for a single lesson."""
    mem = ReflectiveMemory()
    sl = mem.find_by_id(lesson_id)

    if sl is None:
        typer.echo(f"No lesson found with id '{lesson_id}'.", err=True)
        raise typer.Exit(code=1)

    typer.echo("═" * 70)
    typer.echo(f"  Lesson: {sl.id}")
    typer.echo("═" * 70)
    typer.echo(f"  Timestamp:  {sl.timestamp}")
    typer.echo(f"  Severity:   {sl.severity}")
    typer.echo(f"  Retrieved:  {sl.times_retrieved}x")
    typer.echo(f"  Impact:     {sl.impact_score:.2f}")
    typer.echo("─" * 70)
    typer.echo(f"  Condition:  {sl.condition}")
    typer.echo(f"  Action:     {sl.action}")
    typer.echo(f"  Outcome:    {sl.observed_outcome}")
    typer.echo(f"  Lesson:     {sl.lesson}")
    if sl.supersedes:
        typer.echo(f"  Supersedes: {sl.supersedes}")
    typer.echo("═" * 70)


@reflections_app.command(name="prune")
def reflections_prune(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be removed without actually removing.",
    ),
) -> None:
    """Remove superseded lessons."""
    mem = ReflectiveMemory()

    if dry_run:
        all_lessons = mem.list_all(include_superseded=True)
        active = [sl for sl in all_lessons if sl.supersedes is None]
        superseded = [sl for sl in all_lessons if sl.supersedes is not None]
        typer.echo(f"Would remove {len(superseded)} superseded lessons, keeping {len(active)}.")
        return

    removed = mem.prune_superseded()
    remaining = mem.count()
    typer.echo(f"Removed {removed} superseded lesson(s). {remaining} active lesson(s) remaining.")
