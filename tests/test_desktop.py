"""Tests for the desktop FastAPI server."""

from unittest import mock

import pytest

pytest.importorskip("fastapi", reason="fastapi is not installed (pip install sponge-ai[desktop])")

from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Create a TestClient for the desktop app, with provider mocked out."""
    # Patch _build_agent's dependencies so no real LLM/DB is needed.
    with (
        mock.patch("sponge.desktop.server.create_provider") as mock_provider,
        mock.patch("sponge.desktop.server.DiskStore") as mock_diskstore,
        mock.patch("sponge.desktop.server.ResultCache") as mock_cache,
        mock.patch("sponge.desktop.server.SemanticCache") as mock_semcache,
        mock.patch("sponge.desktop.server.TelemetryCollector") as mock_collector,
        mock.patch("sponge.desktop.server.PluginRegistry") as mock_registry,
    ):
        # Set up the mock agent to return a canned result.
        from sponge.cost.models import CostEntry, Usage
        from sponge.core.task import TaskResult
        from sponge.core.task import Task

        mock_agent = mock.AsyncMock()
        mock_agent.run.return_value = TaskResult(
            task=Task(prompt="hello"),
            response="Hello from Sponge!",
            cost_entry=CostEntry(
                usage=Usage(tokens_in=10, tokens_out=5),
                model="test-model",
                cost=0.001,
                naive_cost=0.002,
            ),
            fingerprint=mock.Mock(),
            cache_hit=False,
        )

        # _build_agent should return our mock agent.
        from sponge.desktop import server
        original_build = server._build_agent
        server._build_agent = lambda: mock_agent

        from sponge.desktop.server import app
        tc = TestClient(app)
        yield tc

        # Restore.
        server._build_agent = original_build


def test_index_returns_html(client: TestClient) -> None:
    """GET / returns an HTML page (or fallback if static/index.html missing)."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_chat_empty_message_returns_error() -> None:
    """POST /chat with empty message returns an SSE error event."""
    from sponge.desktop.server import app
    client = TestClient(app)

    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    assert "event: error" in body


def test_chat_with_message_returns_sse_stream(client: TestClient) -> None:
    """POST /chat streams response + cost + done events."""
    response = client.post("/chat", json={"message": "hello"})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    body = response.text
    assert "event: response" in body
    assert "Hello from Sponge!" in body
    assert "event: cost" in body
    assert "event: done" in body


def test_chat_with_images_streams(client: TestClient) -> None:
    """POST /chat with images attaches them to the task."""
    response = client.post("/chat", json={
        "message": "Describe this",
        "images": ["base64encodedimage"],
    })
    assert response.status_code == 200
    assert "event: response" in response.text


def test_sse_format() -> None:
    """_sse() helper produces valid SSE-formatted strings."""
    from sponge.desktop.server import _sse

    result = _sse("test", {"key": "value"})
    assert result.startswith("event: test\n")
    assert '"key": "value"' in result
    assert result.endswith("\n\n")
