"""sponge cost — view cost history and savings."""

import sqlite3
from pathlib import Path

import typer

TELEMETRY_DB = Path.home() / ".sponge" / "telemetry" / "fingerprints.db"

cost_app = typer.Typer(name="cost", help="View cost history and savings.")


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(str(TELEMETRY_DB))


@cost_app.command(name="session")
def cost_session(
    session_id: str = typer.Option("", "--session", "-s", help="Session ID (default: latest)."),
) -> None:
    """Show cost breakdown for a session."""
    if not TELEMETRY_DB.is_file():
        typer.echo("No telemetry data yet. Run 'sponge run \"hello\"' first.")
        return

    conn = _connect()

    if session_id:
        row = conn.execute(
            """SELECT session_id, COUNT(*) as calls,
                      SUM(cost) as total_cost, SUM(naive_cost) as total_naive,
                      SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits
               FROM fingerprints WHERE session_id = ?
               GROUP BY session_id""",
            (session_id,),
        ).fetchone()

        if row is None:
            typer.echo(f"Session '{session_id}' not found.")
            conn.close()
            return

        _print_session(row)
        _print_calls(conn, session_id)
    else:
        row = conn.execute(
            """SELECT session_id, COUNT(*) as calls,
                      SUM(cost) as total_cost, SUM(naive_cost) as total_naive,
                      SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits,
                      MAX(timestamp) as last_call
               FROM fingerprints
               GROUP BY session_id
               ORDER BY last_call DESC LIMIT 1"""
        ).fetchone()

        if row is None:
            typer.echo("No sessions found.")
            conn.close()
            return

        _print_session(row)
        _print_calls(conn, row[0])

    conn.close()


@cost_app.command(name="total")
def cost_total(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to include."),
) -> None:
    """Show total cost across all sessions."""
    if not TELEMETRY_DB.is_file():
        typer.echo("No telemetry data yet.")
        return

    conn = _connect()
    row = conn.execute(
        """SELECT COUNT(DISTINCT session_id) as sessions,
                  COUNT(*) as calls,
                  SUM(cost) as total_cost,
                  SUM(naive_cost) as total_naive,
                  SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits
           FROM fingerprints
           WHERE timestamp > datetime('now', ?)""",
        (f"-{days} days",),
    ).fetchone()

    if row is None or row[1] == 0:
        typer.echo(f"No calls in the last {days} days.")
        conn.close()
        return

    sessions, calls, cost, naive, hits = row
    saved = naive - cost if naive else 0
    pct = (saved / naive * 100) if naive else 0.0
    hit_rate = (hits / calls * 100) if calls else 0.0

    typer.echo(f"Cost Summary (last {days} days)")
    typer.echo("─" * 40)
    typer.echo(f"  Sessions:     {sessions}")
    typer.echo(f"  LLM calls:    {calls}")
    typer.echo(f"  Cache hits:   {hits} ({hit_rate:.0f}%)")
    typer.echo(f"  Total cost:   ${cost:.6f}")
    typer.echo(f"  Naive cost:   ${naive:.6f}")
    typer.echo(f"  Saved:        ${saved:.6f} ({pct:.1f}%)")

    conn.close()


@cost_app.command(name="stats")
def cost_stats() -> None:
    """Show overall cache and cost efficiency statistics."""
    if not TELEMETRY_DB.is_file():
        typer.echo("No telemetry data yet.")
        return

    conn = _connect()
    row = conn.execute(
        """SELECT COUNT(*) as calls,
                  SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as hits,
                  SUM(tokens_in) as total_in,
                  SUM(tokens_out) as total_out,
                  SUM(cost) as total_cost,
                  SUM(naive_cost) as total_naive
           FROM fingerprints"""
    ).fetchone()

    if row is None or row[0] == 0:
        typer.echo("No data yet.")
        conn.close()
        return

    calls, hits, ti, to, cost, naive = row
    hit_rate = (hits / calls * 100) if calls else 0
    saved = naive - cost if naive else 0
    pct = (saved / naive * 100) if naive else 0

    plugin_calls = conn.execute(
        """SELECT COUNT(*) FROM fingerprints
           WHERE tokens_in = 0 AND tokens_out = 0 AND cache_hit = 0"""
    ).fetchone()[0]

    llm_calls = calls - hits - plugin_calls

    typer.echo("Sponge Efficiency Stats")
    typer.echo("─" * 50)
    typer.echo(f"  Total calls:      {calls}")
    typer.echo(f"  Cache hits:       {hits} ({hit_rate:.0f}%)")
    typer.echo(f"  Plugin calls:     {plugin_calls} ($0)")
    typer.echo(f"  LLM calls:        {llm_calls}")
    typer.echo(f"  Total tokens in:  {ti:,}")
    typer.echo(f"  Total tokens out: {to:,}")
    typer.echo(f"  Total cost:       ${cost:.6f}")
    typer.echo(f"  Naive cost:       ${naive:.6f}")
    typer.echo(f"  Total saved:      ${saved:.6f} ({pct:.1f}%)")
    if llm_calls > 0:
        typer.echo(f"  Avg cost/LLM call: ${cost / llm_calls:.4f}")

    conn.close()


def _print_session(row: tuple) -> None:
    sid, calls, cost, naive, hits, *_ = row
    saved = naive - cost if naive else 0
    pct = (saved / naive * 100) if naive else 0.0
    hit_rate = (hits / calls * 100) if calls else 0.0

    typer.echo(f"Session: {sid}")
    typer.echo("─" * 40)
    typer.echo(f"  Calls:        {calls}")
    typer.echo(f"  Cache hits:   {hits} ({hit_rate:.0f}%)")
    typer.echo(f"  Total cost:   ${cost:.6f}")
    typer.echo(f"  Naive cost:   ${naive:.6f}")
    typer.echo(f"  Saved:        ${saved:.6f} ({pct:.1f}%)")


def _print_calls(conn: sqlite3.Connection, session_id: str) -> None:
    rows = conn.execute(
        """SELECT task_hash, model, tokens_in, tokens_out,
                  cost, naive_cost, cache_hit, timestamp
           FROM fingerprints
           WHERE session_id = ?
           ORDER BY id""",
        (session_id,),
    ).fetchall()

    if not rows:
        return

    typer.echo()
    typer.echo("  Calls:")
    for r in rows:
        th, model, ti, to, cost, naive, hit, ts = r
        marker = " [CACHE]" if hit else ""
        typer.echo(
            f"    {th[:8]}  {model}  "
            f"in:{ti} out:{to}  "
            f"${cost:.4f}{marker}"
        )
