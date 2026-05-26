"""Sponge Desktop server — FastAPI + SSE streaming chat."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from sponge.cache.disk_store import DiskStore
from sponge.cache.result_cache import ResultCache
from sponge.cache.semantic_cache import SemanticCache
from sponge.config.settings import Settings
from sponge.core.agent import Agent
from sponge.core.task import Task
from sponge.cost.ledger import build_report
from sponge.cost.models import SavingsLedger
from sponge.llm.factory import create_provider
from sponge.plugins.builtins import get_builtin_plugins
from sponge.plugins.registry import PluginRegistry
from sponge.telemetry.collector import TelemetryCollector

logger = logging.getLogger("sponge.desktop")

STATIC_DIR = Path(__file__).parent / "static"
CACHE_DB = Path.home() / ".sponge" / "cache" / "desktop_store.db"
TELEMETRY_DB = Path.home() / ".sponge" / "telemetry" / "desktop_fp.db"

app = FastAPI(title="Sponge Desktop", version="0.1.0")


def _build_agent() -> Agent:
    settings = Settings()
    provider = create_provider(settings)
    store = DiskStore(CACHE_DB)
    cache = ResultCache(store, settings)
    collector = TelemetryCollector(TELEMETRY_DB)
    sem_cache = SemanticCache(store=store)
    return Agent(
        provider, settings, cache, collector,
        plugins=PluginRegistry(get_builtin_plugins()),
        semantic_cache=sem_cache,
    )


@app.get("/")
async def index() -> HTMLResponse:
    """Serve the chat UI."""
    html_path = STATIC_DIR / "index.html"
    if html_path.is_file():
        return HTMLResponse(html_path.read_text())
    return HTMLResponse("<h1>Sponge Desktop</h1><p>UI not found.</p>")


@app.post("/chat")
async def chat(request: Request) -> StreamingResponse:
    """Stream an LLM response via Server-Sent Events."""
    body = await request.json()
    message = body.get("message", "").strip()
    if not message:
        return StreamingResponse(
            _empty(), media_type="text/event-stream"
        )

    agent = _build_agent()
    task = Task(prompt=message)

    async def _stream() -> AsyncGenerator[str, None]:
        try:
            result = await agent.run(task)

            # Send the response text.
            yield _sse("response", {"text": result.response})

            # Send cost breakdown.
            ledger = SavingsLedger()
            ledger.add(result.cost_entry)
            report = build_report(ledger)
            yield _sse("cost", {
                "cost": report.total_actual,
                "naive_cost": report.total_naive,
                "saved": report.saved,
                "saved_pct": report.saved_pct,
                "cache_hit": result.cache_hit,
                "cache_source": result.cache_source,
            })

            yield _sse("done", {})
        except Exception as e:
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(_stream(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _empty() -> AsyncGenerator[str, None]:
    yield _sse("error", {"message": "Empty message"})
    yield _sse("done", {})
