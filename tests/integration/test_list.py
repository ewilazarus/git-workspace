import pytest

from git_workspace.cli.commands.list import list
from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace


def test_returns_empty_before_any_up(
    workspace: Workspace, capsys: pytest.CaptureFixture[str]
) -> None:
    worktrees = workspace.list_worktrees()
    assert worktrees == []


def test_lists_worktree_after_up(workspace: Workspace, capsys: pytest.CaptureFixture[str]) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    list(workspace_dir=str(workspace.dir))
    output = capsys.readouterr().err
    assert "main" in output


def test_lists_multiple_worktrees(workspace: Workspace, capsys: pytest.CaptureFixture[str]) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    up(
        branch="feature/second",
        base_branch="main",
        workspace_dir=str(workspace.dir),
    )
    list(workspace_dir=str(workspace.dir))
    output = capsys.readouterr().err
    assert "main" in output
    assert "feature/second" in output
