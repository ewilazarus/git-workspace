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
    monkeypatch.chdir(workspace.dir)
    up(branch="main")
    assert (workspace.dir / "main").is_dir()


def test_down_without_root(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    monkeypatch.chdir(workspace.dir)
    down(branch="main")


def test_reset_without_root(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    monkeypatch.chdir(workspace.dir)
    reset(branch="main")
    assert (workspace.dir / "main").is_dir()


def test_remove_without_root(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    monkeypatch.chdir(workspace.dir)
    remove(branch="main")
    assert not (workspace.dir / "main").exists()


def test_list_without_root(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    monkeypatch.chdir(workspace.dir)
    list()


def test_edit_without_root(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EDITOR", "true")
    monkeypatch.setenv("VISUAL", "true")
    monkeypatch.chdir(workspace.dir)
    edit()


# ---------------------------------------------------------------------------
# No --branch: cwd is inside the worktree
# ---------------------------------------------------------------------------


def test_up_without_branch(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    monkeypatch.chdir(workspace.dir / "main")
    up(workspace_dir=str(workspace.dir))
    assert (workspace.dir / "main").is_dir()


def test_down_without_branch(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    monkeypatch.chdir(workspace.dir / "main")
    down(workspace_dir=str(workspace.dir))


def test_reset_without_branch(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    monkeypatch.chdir(workspace.dir / "main")
    reset(workspace_dir=str(workspace.dir))
    assert (workspace.dir / "main").is_dir()


def test_remove_without_branch(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    monkeypatch.chdir(workspace.dir / "main")
    remove(workspace_dir=str(workspace.dir))
    assert not (workspace.dir / "main").exists()


# ---------------------------------------------------------------------------
# No --root and no --branch: cwd is inside the worktree
# ---------------------------------------------------------------------------


def test_up_without_root_and_branch(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    monkeypatch.chdir(workspace.dir / "main")
    up()
    assert (workspace.dir / "main").is_dir()


def test_down_without_root_and_branch(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    monkeypatch.chdir(workspace.dir / "main")
    down()


def test_reset_without_root_and_branch(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    monkeypatch.chdir(workspace.dir / "main")
    reset()
    assert (workspace.dir / "main").is_dir()


def test_remove_without_root_and_branch(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    monkeypatch.chdir(workspace.dir / "main")
    remove()
    assert not (workspace.dir / "main").exists()
