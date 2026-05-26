"""sponge run — execute a task through the agent."""

import asyncio
from pathlib import Path

import typer

from sponge.cache.disk_store import DiskStore
from sponge.cache.result_cache import ResultCache
from sponge.cache.semantic_cache import SemanticCache
from sponge.config.settings import Settings
from sponge.core.agent import Agent
from sponge.core.task import Task
from sponge.cost.ledger import build_report
from sponge.cost.models import SavingsLedger
from sponge.llm.factory import create_provider
from sponge.memory.store import ProjectMemory
from sponge.plugins.builtins import get_builtin_plugins
from sponge.plugins.registry import PluginRegistry
from sponge.telemetry.collector import TelemetryCollector
from sponge.telemetry.tuner import ProposalStore

run_app = typer.Typer(name="run", help="Execute a task.")

CACHE_DB = Path.home() / ".sponge" / "cache" / "store.db"
TELEMETRY_DB = Path.home() / ".sponge" / "telemetry" / "fingerprints.db"
PROPOSALS_DB = Path.home() / ".sponge" / "telemetry" / "proposals.db"


@run_app.command(name="run", context_settings={"ignore_unknown_options": True})
def run_task(
    task: str = typer.Argument(..., help="The task to execute."),
    model: str = typer.Option("", "--model", "-m", help="Override the model."),
    json_mode: bool = typer.Option(False, "--json", help="Output JSON."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass cache."),
    no_stream: bool = typer.Option(  # noqa: ARG001
        False, "--no-stream", help="Disable streaming output."
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Auto-approve plugin operations (writes, deletes)."
    ),
) -> None:
    """Execute a task and show the response with cost breakdown."""
    settings = Settings()
    if model:
        settings.model = model
    if no_cache:
        settings.cache_enabled = False
    if auto_approve:
        settings.auto_approve = True

    # Build infrastructure.
    try:
        provider = create_provider(settings)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e

    store = DiskStore(CACHE_DB)
    cache = ResultCache(store, settings)
    collector = TelemetryCollector(TELEMETRY_DB)
    sem_cache = SemanticCache(store=store)
    mem = ProjectMemory()
    agent = Agent(
        provider, settings, cache, collector,
        plugins=PluginRegistry(get_builtin_plugins()),
        semantic_cache=sem_cache,
        memory=mem,
    )

    # Shadow A/B injection: check for testing proposals.
    experiment_id: str | None = None
    experiment_group: str | None = None
    try:
        prop_store = ProposalStore(PROPOSALS_DB)
        testing = prop_store.list_by_state("testing")
        if testing:
            import hashlib

            for p in testing:
                # Deterministic assignment: hash session fingerprint to decide group.
                session_fp = f"{p.id}:{task[:50]}"
                bucket = int(hashlib.md5(session_fp.encode()).hexdigest(), 16) % 100
                threshold = int(settings.tune_shadow_ratio * 100)

                if bucket < threshold:
                    experiment_group = "shadow"
                    _apply_shadow_override(settings, p.param, p.proposed)
                else:
                    experiment_group = "baseline"
                experiment_id = p.id
                break  # Only one active experiment at a time.
    except Exception:
        pass  # If proposals DB doesn't exist yet, skip silently.

    # Run the task.
    try:
        result = asyncio.run(
            agent.run(
                Task(prompt=task, model=settings.model),
                experiment_id=experiment_id,
                experiment_group=experiment_group,
            )
        )
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e

    # Output.
    ledger = SavingsLedger()
    ledger.add(result.cost_entry)
    report = build_report(ledger)

    if json_mode:
        import json

        typer.echo(
            json.dumps(
                {
                    "response": result.response,
                    "cache_hit": result.cache_hit,
                    "cost": report.total_actual,
                    "naive_cost": report.total_naive,
                    "saved": report.saved,
                }
            )
        )
    else:
        typer.echo(result.response)
        typer.echo()
        typer.echo(report.format_text())

    if result.cache_hit:
        source = result.cache_source or "cache"
        typer.echo(f"(served from {source} cache)")


def _apply_shadow_override(settings: Settings, param: str, value: object) -> None:
    """Apply a shadow parameter override to settings."""
    if hasattr(settings, param):
        setattr(settings, param, value)
