"""sponge benchmark — run benchmark fixtures against real providers.

Usage:
    sponge benchmark                          # run all fixtures
    sponge benchmark --fixture simple_qa      # run one fixture
    sponge benchmark --output results.json    # save results to file
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import typer

from sponge.cache.disk_store import DiskStore
from sponge.cache.result_cache import ResultCache
from sponge.cache.semantic_cache import SemanticCache
from sponge.config.settings import Settings
from sponge.core.agent import Agent
from sponge.core.task import Task
from sponge.llm.factory import create_provider
from sponge.plugins.builtins import get_builtin_plugins
from sponge.plugins.registry import PluginRegistry
from sponge.telemetry.collector import TelemetryCollector

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "tests" / "fixtures"
CACHE_DB = Path.home() / ".sponge" / "cache" / "benchmark_store.db"
TELEMETRY_DB = Path.home() / ".sponge" / "telemetry" / "benchmark_fp.db"


@dataclass
class BenchmarkResult:
    """Result of running a single benchmark fixture."""

    name: str
    task: str
    model: str
    provider: str
    attempt: int
    response: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    naive_cost: float = 0.0
    cache_hit: bool = False
    cache_source: str = ""
    duration_ms: float = 0.0
    error: str = ""


@dataclass
class BenchmarkReport:
    """Aggregate benchmark report."""

    provider: str
    model: str
    results: list[BenchmarkResult] = field(default_factory=list)
    total_cost: float = 0.0
    total_naive: float = 0.0
    total_calls: int = 0
    cache_hits: int = 0
    plugin_calls: int = 0
    total_duration_ms: float = 0.0

    @property
    def cache_hit_rate(self) -> float:
        return (self.cache_hits / self.total_calls * 100) if self.total_calls else 0.0

    @property
    def saved(self) -> float:
        return self.total_naive - self.total_cost

    @property
    def saved_pct(self) -> float:
        return (self.saved / self.total_naive * 100) if self.total_naive else 0.0

    def format(self) -> str:
        lines = [
            "Benchmark Report",
            f"{'─' * 60}",
            f"  Provider: {self.provider}",
            f"  Model:    {self.model}",
            f"  Calls:    {self.total_calls}",
            f"  Cache:    {self.cache_hits} hits ({self.cache_hit_rate:.0f}%)",
            f"  Plugin:   {self.plugin_calls} calls ($0)",
            f"  Duration: {self.total_duration_ms:.0f}ms",
            "  ──────────────────────",
            f"  Naive cost:   ${self.total_naive:.6f}",
            f"  Actual cost:  ${self.total_cost:.6f}",
            f"  Saved:        ${self.saved:.6f} ({self.saved_pct:.1f}%)",
            "",
            "Breakdown:",
        ]
        for r in self.results:
            cache_mark = f" [{r.cache_source}]" if r.cache_hit else ""
            error_mark = f" ERROR: {r.error}" if r.error else ""
            lines.append(
                f"  {r.name} #{r.attempt}  "
                f"in:{r.tokens_in} out:{r.tokens_out}  "
                f"${r.cost:.6f}  {r.duration_ms:.0f}ms"
                f"{cache_mark}{error_mark}"
            )
        return "\n".join(lines)


def _load_fixtures(name: str | None = None) -> list[dict]:
    """Load benchmark fixtures from JSON files."""
    fixtures = []
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        if path.name == "README.md":
            continue
        data = json.loads(path.read_text())
        if name and data.get("name") != name:
            continue
        fixtures.append(data)
    return fixtures


async def _run_task(
    agent: Agent, task: str, model: str, name: str, attempt: int
) -> BenchmarkResult:
    """Run a single task and return its benchmark result."""
    start = time.monotonic()
    try:
        result = await agent.run(Task(prompt=task, model=model))
        duration = (time.monotonic() - start) * 1000
        return BenchmarkResult(
            name=name,
            task=task,
            model=model,
            provider=agent._settings.provider,
            attempt=attempt,
            response=result.response[:200],
            tokens_in=result.cost_entry.usage.tokens_in,
            tokens_out=result.cost_entry.usage.tokens_out,
            cost=result.cost_entry.cost,
            naive_cost=result.cost_entry.naive_cost,
            cache_hit=result.cache_hit,
            cache_source=result.cache_source,
            duration_ms=duration,
        )
    except Exception as e:
        duration = (time.monotonic() - start) * 1000
        return BenchmarkResult(
            name=name, task=task, model=model,
            provider="unknown", attempt=attempt,
            duration_ms=duration, error=str(e),
        )


def run_benchmark(
    fixture_name: str = typer.Option(
        "", "--fixture", "-f", help="Run a specific fixture by name."
    ),
    output_file: str = typer.Option(
        "", "--output", "-o", help="Save results to JSON file."
    ),
) -> None:
    """Run benchmark fixtures against a real LLM provider."""
    settings = Settings()
    fixtures = _load_fixtures(fixture_name or None)

    if not fixtures:
        typer.echo("No fixtures found.")
        return

    # Build infrastructure.
    try:
        provider = create_provider(settings)
    except Exception as e:
        typer.echo(f"Error creating provider: {e}", err=True)
        typer.echo("Set SPONGE_PROVIDER and SPONGE_<PROVIDER>_API_KEY.", err=True)
        raise typer.Exit(code=1) from e

    # Use benchmark-specific DBs so we don't pollute real telemetry.
    store = DiskStore(CACHE_DB)
    cache = ResultCache(store, settings)
    collector = TelemetryCollector(TELEMETRY_DB)
    sem_cache = SemanticCache(store=store)
    agent = Agent(
        provider, settings, cache, collector,
        plugins=PluginRegistry(get_builtin_plugins()),
        semantic_cache=sem_cache,
    )

    model = settings.model
    report = BenchmarkReport(provider=settings.provider, model=model)

    typer.echo(f"Running benchmarks: {settings.provider}/{model}")
    typer.echo(f"{'─' * 40}")

    for fixture in fixtures:
        name = fixture["name"]
        task = fixture["task"]
        repeat = fixture.get("repeat_count", 1)

        for i in range(repeat):
            typer.echo(f"  {name} #{i + 1}... ", nl=False)
            result = asyncio.run(_run_task(agent, task, model, name, i + 1))
            report.results.append(result)
            report.total_calls += 1
            report.total_cost += result.cost
            report.total_naive += result.naive_cost
            report.total_duration_ms += result.duration_ms
            if result.cache_hit:
                report.cache_hits += 1
            if result.tokens_in == 0 and result.tokens_out == 0 and not result.cache_hit:
                report.plugin_calls += 1

            if result.error:
                typer.echo(f"ERROR: {result.error}")
            else:
                typer.echo(
                    f"${result.cost:.6f} ({result.tokens_in}+{result.tokens_out} tokens, "
                    f"{result.duration_ms:.0f}ms)"
                    + (" [CACHE]" if result.cache_hit else "")
                )

        # Run a semantic-cache variant: slightly different query.
        sem_variant = task.replace("?", " ?").replace("What is", "Tell me")
        if sem_variant != task:
            typer.echo(f"  {name} (semantic variant)... ", nl=False)
            result = asyncio.run(_run_task(agent, sem_variant, model, name, repeat + 1))
            report.results.append(result)
            report.total_calls += 1
            report.total_cost += result.cost
            report.total_naive += result.naive_cost
            report.total_duration_ms += result.duration_ms
            if result.cache_hit:
                report.cache_hits += 1
            if result.error:
                typer.echo(f"ERROR: {result.error}")
            else:
                typer.echo(
                    f"${result.cost:.6f} ({result.tokens_in}+{result.tokens_out} tokens, "
                    f"{result.duration_ms:.0f}ms)"
                    + (" [CACHE]" if result.cache_hit else "")
                )

    typer.echo()
    typer.echo(report.format())

    if output_file:
        data = {
            "provider": report.provider,
            "model": report.model,
            "total_cost": report.total_cost,
            "total_naive": report.total_naive,
            "saved": report.saved,
            "saved_pct": report.saved_pct,
            "cache_hit_rate": report.cache_hit_rate,
            "results": [
                {
                    "name": r.name,
                    "attempt": r.attempt,
                    "tokens_in": r.tokens_in,
                    "tokens_out": r.tokens_out,
                    "cost": r.cost,
                    "naive_cost": r.naive_cost,
                    "cache_hit": r.cache_hit,
                    "cache_source": r.cache_source,
                    "duration_ms": r.duration_ms,
                    "error": r.error,
                }
                for r in report.results
            ],
        }
        Path(output_file).write_text(json.dumps(data, indent=2))
        typer.echo(f"\nResults saved to {output_file}")
