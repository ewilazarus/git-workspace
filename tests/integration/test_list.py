from io import StringIO

from pytest_mock import MockerFixture
from rich.console import Console

from git_workspace import ui
from git_workspace.cli.commands.list import list
from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace


def _render(renderable) -> str:
    buf = StringIO()
    Console(file=buf, highlight=False, theme=ui._theme).print(renderable)
    return buf.getvalue()


def test_returns_empty_before_any_up(workspace: Workspace) -> None:
    assert workspace.list_worktrees() == []


def test_lists_worktree_after_up(workspace: Workspace, mocker: MockerFixture) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    mock_print = mocker.patch.object(ui.console, "print")
    list(workspace_dir=str(workspace.dir))
    output = _render(mock_print.call_args[0][0])
    assert "main" in output


def test_lists_multiple_worktrees(workspace: Workspace, mocker: MockerFixture) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    up(branch="feature/second", base_branch="main", workspace_dir=str(workspace.dir))
    mock_print = mocker.patch.object(ui.console, "print")
    list(workspace_dir=str(workspace.dir))
    output = _render(mock_print.call_args[0][0])
    assert "main" in output
    assert "feature/second" in output
