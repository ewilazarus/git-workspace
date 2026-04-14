"""
Tests that commands work when --root and/or --branch are omitted and resolved
from the current working directory.
"""

import pytest

from git_workspace.cli.commands.down import down
from git_workspace.cli.commands.edit import edit
from git_workspace.cli.commands.list import list
from git_workspace.cli.commands.remove import remove
from git_workspace.cli.commands.reset import reset
from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace


# ---------------------------------------------------------------------------
# No --root: cwd is the workspace directory
# ---------------------------------------------------------------------------


def test_up_without_root(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(workspace.directory)
    up(branch="main")
    assert (workspace.directory / "main").is_dir()


def test_down_without_root(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    up(branch="main", workspace_dir=str(workspace.directory))
    monkeypatch.chdir(workspace.directory)
    down(branch="main")


def test_reset_without_root(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    up(branch="main", workspace_dir=str(workspace.directory))
    monkeypatch.chdir(workspace.directory)
    reset(branch="main")
    assert (workspace.directory / "main").is_dir()


def test_remove_without_root(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    up(branch="main", workspace_dir=str(workspace.directory))
    monkeypatch.chdir(workspace.directory)
    remove(branch="main")
    assert not (workspace.directory / "main").exists()


def test_list_without_root(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    up(branch="main", workspace_dir=str(workspace.directory))
    monkeypatch.chdir(workspace.directory)
    list()


def test_edit_without_root(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EDITOR", "true")
    monkeypatch.setenv("VISUAL", "true")
    monkeypatch.chdir(workspace.directory)
    edit()


# ---------------------------------------------------------------------------
# No --branch: cwd is inside the worktree
# ---------------------------------------------------------------------------


def test_up_without_branch(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    up(branch="main", workspace_dir=str(workspace.directory))
    monkeypatch.chdir(workspace.directory / "main")
    up(workspace_dir=str(workspace.directory))
    assert (workspace.directory / "main").is_dir()


def test_down_without_branch(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    up(branch="main", workspace_dir=str(workspace.directory))
    monkeypatch.chdir(workspace.directory / "main")
    down(workspace_dir=str(workspace.directory))


def test_reset_without_branch(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    up(branch="main", workspace_dir=str(workspace.directory))
    monkeypatch.chdir(workspace.directory / "main")
    reset(workspace_dir=str(workspace.directory))
    assert (workspace.directory / "main").is_dir()


def test_remove_without_branch(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    up(branch="main", workspace_dir=str(workspace.directory))
    monkeypatch.chdir(workspace.directory / "main")
    remove(workspace_dir=str(workspace.directory))
    assert not (workspace.directory / "main").exists()


# ---------------------------------------------------------------------------
# No --root and no --branch: cwd is inside the worktree
# ---------------------------------------------------------------------------


def test_up_without_root_and_branch(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    up(branch="main", workspace_dir=str(workspace.directory))
    monkeypatch.chdir(workspace.directory / "main")
    up()
    assert (workspace.directory / "main").is_dir()


def test_down_without_root_and_branch(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    up(branch="main", workspace_dir=str(workspace.directory))
    monkeypatch.chdir(workspace.directory / "main")
    down()


def test_reset_without_root_and_branch(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    up(branch="main", workspace_dir=str(workspace.directory))
    monkeypatch.chdir(workspace.directory / "main")
    reset()
    assert (workspace.directory / "main").is_dir()


def test_remove_without_root_and_branch(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    up(branch="main", workspace_dir=str(workspace.directory))
    monkeypatch.chdir(workspace.directory / "main")
    remove()
    assert not (workspace.directory / "main").exists()
