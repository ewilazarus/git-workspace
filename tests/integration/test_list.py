from io import StringIO

from pytest_mock import MockerFixture
from rich.console import Console

from git_workspace import ui
from git_workspace.cli.commands.list import list
from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace
from tests.helpers import make_context


def _render(renderable) -> str:
    buf = StringIO()
    Console(file=buf, highlight=False, theme=ui._theme).print(renderable)
    return buf.getvalue()


def test_returns_empty_before_any_up(workspace: Workspace) -> None:
    assert workspace.list_worktrees() == []


def test_lists_worktree_after_up(workspace: Workspace, mocker: MockerFixture) -> None:
    up(ctx=make_context(str(workspace.dir)), branch="main")
    mock_print = mocker.patch.object(ui.console, "print")
    list(ctx=make_context(str(workspace.dir)))
    output = _render(mock_print.call_args[0][0])
    assert "main" in output


def test_lists_multiple_worktrees(workspace: Workspace, mocker: MockerFixture) -> None:
    up(ctx=make_context(str(workspace.dir)), branch="main")
    up(ctx=make_context(str(workspace.dir)), branch="feature/second", base_branch="main")
    mock_print = mocker.patch.object(ui.console, "print")
    list(ctx=make_context(str(workspace.dir)))
    output = _render(mock_print.call_args[0][0])
    assert "main" in output
    assert "feature/second" in output
