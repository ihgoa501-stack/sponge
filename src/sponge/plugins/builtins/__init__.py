"""Built-in plugins for Sponge.

These plugins handle common operations directly without LLM calls,
providing $0 cost execution paths.
"""

from sponge.plugins.base import Plugin
from sponge.plugins.builtins.file_ops import FileOpsPlugin
from sponge.plugins.builtins.search import SearchPlugin
from sponge.plugins.builtins.shell import ShellPlugin


def get_builtin_plugins() -> list[Plugin]:
    """Return all built-in plugins for registration."""
    return [FileOpsPlugin(), SearchPlugin(), ShellPlugin()]
