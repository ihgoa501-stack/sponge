"""sponge session — multi-turn conversation management."""

import asyncio
from pathlib import Path

import typer

from sponge.cache.disk_store import DiskStore
from sponge.cache.result_cache import ResultCache
from sponge.config.settings import Settings
from sponge.core.agent import Agent
from sponge.core.session import (
    create_session,
    list_sessions,
    load_session,
    save_session,
)
from sponge.cost.ledger import build_report
from sponge.cost.models import SavingsLedger
from sponge.llm.factory import create_provider
from sponge.telemetry.collector import TelemetryCollector

session_app = typer.Typer(name="session", help="Multi-turn conversation sessions.")

CACHE_DB = Path.home() / ".sponge" / "cache" / "store.db"
TELEMETRY_DB = Path.home() / ".sponge" / "telemetry" / "fingerprints.db"


def _current_session_path() -> Path:
    return Path.home() / ".sponge" / "current_session"


def _get_current_session_id() -> str | None:
    p = _current_session_path()
    if p.is_file():
        return p.read_text().strip()
    return None


def _set_current_session(session_id: str) -> None:
    p = _current_session_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(session_id)


@session_app.command(name="start")
def session_start(
    model: str = typer.Option("", "--model", "-m", help="Model to use."),
) -> None:
    """Start a new conversation session."""
    settings = Settings()
    if model:
        settings.model = model

    session = create_session(model=settings.model)
    save_session(session)
    _set_current_session(session.id)
    typer.echo(f"Session started: {session.id} (model: {session.model})")


@session_app.command(name="resume")
def session_resume(
    session_id: str = typer.Argument(..., help="Session ID to resume."),
) -> None:
    """Resume an existing session."""
    session = load_session(session_id)
    if session is None:
        typer.echo(f"Session '{session_id}' not found.", err=True)
        raise typer.Exit(code=1)
    _set_current_session(session_id)
    typer.echo(f"Resumed session: {session_id} ({len(session.turns)} turns)")


@session_app.command(name="chat")
def session_chat(
    message: str = typer.Argument(..., help="Message to send."),
    max_history: int = typer.Option(20, "--max-history", help="Max history turns."),
    json_mode: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Send a message in the current session."""
    session_id = _get_current_session_id()
    if session_id is None:
        typer.echo("No active session. Use 'sponge session start' first.", err=True)
        raise typer.Exit(code=1)

    session = load_session(session_id)
    if session is None:
        typer.echo(f"Session '{session_id}' not found.", err=True)
        raise typer.Exit(code=1)

    settings = Settings()
    if session.model:
        settings.model = session.model

    try:
        provider = create_provider(settings)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e

    store = DiskStore(CACHE_DB)
    cache = ResultCache(store, settings)
    collector = TelemetryCollector(TELEMETRY_DB)
    agent = Agent(provider, settings, cache, collector)

    try:
        result = asyncio.run(agent.run_with_history(session, message, max_history=max_history))
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e

    save_session(session)

    ledger = SavingsLedger()
    ledger.add(result.cost_entry)
    report = build_report(ledger)

    if json_mode:
        import json

        typer.echo(
            json.dumps(
                {
                    "response": result.response,
                    "session_id": session.id,
                    "turns": len(session.turns),
                    "cost": report.total_actual,
                }
            )
        )
    else:
        typer.echo(result.response)
        typer.echo()
        typer.echo(report.format_text())


@session_app.command(name="list")
def session_list() -> None:
    """List all saved sessions."""
    sessions = list_sessions()
    if not sessions:
        typer.echo("No sessions found.")
        return

    typer.echo("Sessions")
    typer.echo("─" * 50)
    for s in sessions:
        typer.echo(f"  {s['id']}  turns: {s['turns']}  cost: ${s['total_cost']:.4f}")
