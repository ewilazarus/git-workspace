from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from git_workspace import workspace
from git_workspace.errors import UnableToResolveBranchError

ROOT = Path("/workspace")
WORKTREE = ROOT / "feat" / "001"
BRANCH = "feat/001"


@pytest.fixture(autouse=True)
def git_mocks(mocker: MockerFixture):
    mocker.patch("git_workspace.git.get_worktree_root", return_value=WORKTREE)
    mocker.patch("git_workspace.git.get_current_branch", return_value=BRANCH)


def test_when_inside_worktree_then_returns_branch() -> None:
    result = workspace.resolve_branch(ROOT, cwd=WORKTREE)

    assert result == BRANCH


def test_when_inside_worktree_subdirectory_then_returns_branch() -> None:
    result = workspace.resolve_branch(ROOT, cwd=WORKTREE / "src" / "lib")

    assert result == BRANCH


def test_when_at_workspace_root_then_raises() -> None:
    with pytest.raises(UnableToResolveBranchError):
        workspace.resolve_branch(ROOT, cwd=ROOT)


def test_when_outside_workspace_then_raises() -> None:
    with pytest.raises(UnableToResolveBranchError):
        workspace.resolve_branch(ROOT, cwd=Path("/other/place"))


def test_when_inside_dot_workspace_then_raises() -> None:
    with pytest.raises(UnableToResolveBranchError):
        workspace.resolve_branch(ROOT, cwd=ROOT / ".workspace" / "hooks")


def test_when_inside_dot_git_then_raises() -> None:
    with pytest.raises(UnableToResolveBranchError):
        workspace.resolve_branch(ROOT, cwd=ROOT / ".git" / "refs")


def test_when_in_intermediate_directory_then_raises(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.get_worktree_root", return_value=None)

    with pytest.raises(UnableToResolveBranchError):
        workspace.resolve_branch(ROOT, cwd=ROOT / "feat")


def test_when_head_is_detached_then_raises(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.get_current_branch", return_value=None)

    with pytest.raises(UnableToResolveBranchError):
        workspace.resolve_branch(ROOT, cwd=WORKTREE)
