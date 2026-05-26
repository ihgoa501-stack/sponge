"""Entry point for `python -m sponge`."""

from sponge.cli.app import app
from sponge.utils.logging import setup_logging

setup_logging()
app()
