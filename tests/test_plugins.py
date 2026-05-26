"""Tests for built-in plugins."""

import tempfile
from pathlib import Path

import pytest

from sponge.plugins.base import PluginContext
from sponge.plugins.builtins.file_ops import FileOpsPlugin
from sponge.plugins.builtins.search import SearchPlugin
from sponge.plugins.builtins.shell import ShellPlugin


@pytest.fixture
def file_plugin() -> FileOpsPlugin:
    return FileOpsPlugin()


@pytest.fixture
def search_plugin() -> SearchPlugin:
    return SearchPlugin()


@pytest.fixture
def shell_plugin() -> ShellPlugin:
    return ShellPlugin()


# ═══════════════════════════════════════════════════════════════════
# FileOpsPlugin
# ═══════════════════════════════════════════════════════════════════


def test_can_handle_read(file_plugin: FileOpsPlugin) -> None:
    match = file_plugin.can_handle("read file src/main.py")
    assert match is not None
    assert match.confidence >= 0.8
    assert match.args["kind"] == "read"


def test_can_handle_read_variants(file_plugin: FileOpsPlugin) -> None:
    for task in [
        "show me the contents of config.toml",
        "cat pyproject.toml",
        "view the file README.md",
        "display file setup.cfg",
        "what's in src/sponge/__init__.py",
    ]:
        match = file_plugin.can_handle(task)
        assert match is not None, f"should match: {task}"
        assert match.args["kind"] == "read", f"kind should be read for: {task}"


def test_can_handle_list(file_plugin: FileOpsPlugin) -> None:
    match = file_plugin.can_handle("list files in src/")
    assert match is not None
    assert match.confidence >= 0.8
    assert match.args["kind"] == "list"


def test_can_handle_list_variants(file_plugin: FileOpsPlugin) -> None:
    for task in [
        "list directory tests/",
        "ls",
        "show files in src/sponge/",
        "what files are in .",
    ]:
        match = file_plugin.can_handle(task)
        assert match is not None, f"should match: {task}"
        assert match.args["kind"] == "list", f"kind should be list for: {task}"


def test_can_handle_write(file_plugin: FileOpsPlugin) -> None:
    match = file_plugin.can_handle("write hello world to output.txt")
    assert match is not None
    assert match.args["kind"] == "write"


def test_can_handle_delete(file_plugin: FileOpsPlugin) -> None:
    match = file_plugin.can_handle("delete file temp.txt")
    assert match is not None
    assert match.args["kind"] == "delete"


def test_no_match_generic(file_plugin: FileOpsPlugin) -> None:
    for task in [
        "explain the CAP theorem",
        "what is 2+2?",
        "refactor the auth module",
        "help me debug this error",
    ]:
        match = file_plugin.can_handle(task)
        assert match is None, f"should not match: {task}"


def test_read_requires_path(file_plugin: FileOpsPlugin) -> None:
    match = file_plugin.can_handle("read file")
    assert match is None


# ── FileOps execution ──────────────────────────────────────────────


async def test_execute_read_real_file(
    file_plugin: FileOpsPlugin, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.chdir(tmp)
        (Path(tmp) / "hello.txt").write_text("hello sponge")
        result = await file_plugin.execute(PluginContext(task="read file hello.txt"))
        assert result.success is True
        assert "hello sponge" in result.output


async def test_execute_list_directory(
    file_plugin: FileOpsPlugin, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.chdir(tmp)
        (Path(tmp) / "a.txt").write_text("a")
        (Path(tmp) / "b.py").write_text("b")
        (Path(tmp) / "sub").mkdir()
        result = await file_plugin.execute(PluginContext(task="list files"))
        assert result.success is True
        assert "a.txt" in result.output
        assert "b.py" in result.output
        assert "sub" in result.output


async def test_execute_read_missing_file(
    file_plugin: FileOpsPlugin, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.chdir(tmp)
        result = await file_plugin.execute(PluginContext(task="read file nonexistent.xyz"))
        assert "NOT FOUND" in result.output


async def test_execute_read_directory_as_file(
    file_plugin: FileOpsPlugin, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.chdir(tmp)
        (Path(tmp) / "mydir").mkdir()
        result = await file_plugin.execute(PluginContext(task="read file mydir"))
        assert "is a directory" in result.output


async def test_execute_list_single_file(
    file_plugin: FileOpsPlugin, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.chdir(tmp)
        (Path(tmp) / "lonely.txt").write_text("data")
        result = await file_plugin.execute(PluginContext(task="list files in ."))
        assert result.success is True
        assert "lonely.txt" in result.output


async def test_execute_write_creates_file(
    file_plugin: FileOpsPlugin, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.chdir(tmp)
        result = await file_plugin.execute(PluginContext(task="write hello to out.txt"))
        assert result.success is True
        assert (Path(tmp) / "out.txt").read_text() == "hello"


async def test_execute_delete_removes_file(
    file_plugin: FileOpsPlugin, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.chdir(tmp)
        (Path(tmp) / "gone.txt").write_text("bye")
        result = await file_plugin.execute(PluginContext(task="delete file gone.txt"))
        assert result.success is True
        assert not (Path(tmp) / "gone.txt").exists()


# ── FileOps safety ─────────────────────────────────────────────────


async def test_path_traversal_blocked(file_plugin: FileOpsPlugin) -> None:
    result = await file_plugin.execute(PluginContext(task="read file ../../../etc/passwd"))
    assert result.success is False
    assert "outside" in result.output.lower() or "SKIPPED" in result.output


async def test_absolute_path_outside_cwd_blocked(file_plugin: FileOpsPlugin) -> None:
    result = await file_plugin.execute(PluginContext(task="read file /etc/passwd"))
    assert result.success is False


# ═══════════════════════════════════════════════════════════════════
# SearchPlugin
# ═══════════════════════════════════════════════════════════════════


def test_search_can_handle(search_plugin: SearchPlugin) -> None:
    for task in [
        "search for TODO in src/",
        "find all occurrences of import in code",
        "grep pytest in tests/",
        "look for deprecated",
    ]:
        match = search_plugin.can_handle(task)
        assert match is not None, f"should match: {task}"
        assert match.confidence >= 0.8


def test_search_can_handle_quoted(search_plugin: SearchPlugin) -> None:
    match = search_plugin.can_handle("search for 'async def' in src/")
    assert match is not None
    assert match.args["pattern"] == "async def"


def test_search_no_match_generic(search_plugin: SearchPlugin) -> None:
    for task in [
        "explain the CAP theorem",
        "what is 2+2?",
        "read file src/main.py",
        "help me debug this error",
    ]:
        match = search_plugin.can_handle(task)
        assert match is None, f"should not match: {task}"


async def test_search_execute_finds_match(
    search_plugin: SearchPlugin, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.chdir(tmp)
        (Path(tmp) / "a.py").write_text("hello world\nTODO: fix this\nbye")
        (Path(tmp) / "b.py").write_text("nothing here")

        result = await search_plugin.execute(PluginContext(task="search for TODO"))
        assert result.success is True
        assert "TODO" in result.output
        assert "a.py" in result.output


async def test_search_execute_no_match(
    search_plugin: SearchPlugin, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.chdir(tmp)
        (Path(tmp) / "a.py").write_text("hello world")

        result = await search_plugin.execute(PluginContext(task="search for NOMATCH"))
        assert "No matches" in result.output


async def test_search_execute_in_directory(
    search_plugin: SearchPlugin, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.chdir(tmp)
        sub = Path(tmp) / "sub"
        sub.mkdir()
        (sub / "x.py").write_text("FIXME here")
        (Path(tmp) / "y.py").write_text("clean")

        result = await search_plugin.execute(
            PluginContext(task="search for FIXME in sub")
        )
        assert result.success is True
        assert "FIXME" in result.output
        assert "x.py" in result.output


async def test_search_directory_outside_cwd(search_plugin: SearchPlugin) -> None:
    result = await search_plugin.execute(
        PluginContext(task="search for foo in ../../../etc")
    )
    assert result.success is False
    assert "outside" in result.output.lower()


async def test_search_missing_directory(
    search_plugin: SearchPlugin, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.chdir(tmp)
        result = await search_plugin.execute(
            PluginContext(task="search for foo in nope")
        )
        assert result.success is False
        assert "not found" in result.output.lower()


# ═══════════════════════════════════════════════════════════════════
# ShellPlugin
# ═══════════════════════════════════════════════════════════════════


def test_shell_can_handle_run(shell_plugin: ShellPlugin) -> None:
    for task in [
        "run pytest",
        "execute ls -la",
        "shell: echo hello",
        "run command make test",
    ]:
        match = shell_plugin.can_handle(task)
        assert match is not None, f"should match: {task}"
        assert match.confidence >= 0.8


def test_shell_no_match_generic(shell_plugin: ShellPlugin) -> None:
    for task in [
        "explain the CAP theorem",
        "read file src/main.py",
        "what is 2+2?",
    ]:
        match = shell_plugin.can_handle(task)
        assert match is None, f"should not match: {task}"


def test_shell_blocklist(shell_plugin: ShellPlugin) -> None:
    match = shell_plugin.can_handle("run sudo rm -rf /")
    assert match is not None  # It matches, but is blocked
    assert "blocked" in match.args


async def test_shell_execute_echo(
    shell_plugin: ShellPlugin, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.chdir(tmp)
        result = await shell_plugin.execute(PluginContext(task="run echo hello"))
        assert result.success is True
        assert "hello" in result.output


async def test_shell_execute_fail(shell_plugin: ShellPlugin) -> None:
    result = await shell_plugin.execute(PluginContext(task="run nonexistent_command_xyz"))
    assert result.success is False


async def test_shell_blocklist_blocked_at_execute(shell_plugin: ShellPlugin) -> None:
    result = await shell_plugin.execute(PluginContext(task="run sudo rm -rf /"))
    assert result.success is False
    assert "Blocked" in result.output
