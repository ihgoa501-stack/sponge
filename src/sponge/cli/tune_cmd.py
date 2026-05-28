"""sponge tune — detect optimization opportunities and manage proposals."""

from pathlib import Path

import typer

from sponge.config.settings import Settings
from sponge.telemetry.tuner import Tuner

tune_app = typer.Typer(name="tune", help="Self-tuning optimizer commands.")

FINGERPRINTS_DB = Path.home() / ".sponge" / "telemetry" / "fingerprints.db"
PROPOSALS_DB = Path.home() / ".sponge" / "telemetry" / "proposals.db"


def _get_tuner() -> Tuner:
    return Tuner(FINGERPRINTS_DB, PROPOSALS_DB, Settings())


@tune_app.command(name="report")
def tune_report() -> None:
    """Run detectors and show ranked tuning proposals."""
    tuner = _get_tuner()
    proposals = tuner.run_detectors()

    if not proposals:
        typer.echo("No tuning proposals detected.")
        return

    typer.echo("Tuning Proposals")
    typer.echo("─" * 60)
    for i, p in enumerate(proposals, 1):
        typer.echo(
            f"\n{i}. {p.param}: {p.current} → {p.proposed} "
            f"(confidence: {p.confidence:.2f}, risk: {p.risk})"
        )
        typer.echo(f"   {p.reason}")
        typer.echo(f"   [{p.state}] — approve: sponge tune apply {p.id}")

    # Save all proposals to store.
    for p in proposals:
        tuner.store.insert(p)


@tune_app.command(name="apply")
def tune_apply(
    proposal_id: str = typer.Argument(..., help="Proposal ID to activate"),
) -> None:
    """Activate a proposal for shadow A/B testing."""
    tuner = _get_tuner()
    result = tuner.activate(proposal_id)
    if result is None:
        typer.echo(f"Proposal '{proposal_id}' not found.", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Activated: {result.id} → testing state.")
    typer.echo("Shadow A/B will run on future sponge run calls.")


@tune_app.command(name="review")
def tune_review() -> None:
    """Review active experiments with statistical results."""
    tuner = _get_tuner()
    testing = tuner.store.list_by_state("testing")

    if not testing:
        typer.echo("No active experiments.")
        return

    typer.echo("Active Experiments")
    typer.echo("─" * 60)
    for p in testing:
        result = tuner.evaluate(p.id)
        if result is None:
            continue

        typer.echo(f"\n{p.param}: {p.current} → {p.proposed}")
        typer.echo(
            f"  baseline: {result.baseline_samples} samples, mean ${result.baseline_mean_cost:.4f}"
        )
        typer.echo(
            f"  shadow:   {result.shadow_samples} samples, mean ${result.shadow_mean_cost:.4f}"
        )
        typer.echo(
            f"  savings: {result.savings_pct:.1f}%, "
            f"p={result.p_value:.4f}, verdict: {result.verdict}"
        )


@tune_app.command(name="history")
def tune_history() -> None:
    """Show all past proposals and their states."""
    tuner = _get_tuner()
    proposals = tuner.store.list_all()

    if not proposals:
        typer.echo("No proposals yet. Run 'sponge tune report' first.")
        return

    typer.echo("Tuning History")
    typer.echo("─" * 60)
    for p in proposals:
        state_marker = {"accepted": "✔", "rejected": "✘", "testing": "⏳"}.get(p.state, "·")
        typer.echo(f"  {state_marker} {p.id}: {p.param} {p.current}→{p.proposed} [{p.state}]")
