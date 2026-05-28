"""sponge desktop — launch the web-based chat UI."""

import webbrowser

import typer


def run_desktop(
    port: int = typer.Option(8420, "--port", "-p", help="Port to listen on."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser."),
) -> None:
    """Launch the Sponge Desktop chat interface."""
    import uvicorn

    if not no_browser:
        webbrowser.open(f"http://localhost:{port}")

    uvicorn.run(
        "sponge.desktop.server:app",
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )
