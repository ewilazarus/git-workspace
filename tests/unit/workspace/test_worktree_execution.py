from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from git_workspace import workspace
from git_workspace.errors import WorktreeCreationError
from git_workspace.workspace import WorktreeResult

ROOT = Path("/workspace")
BRANCH = "feat/001"
BASE = "main"
WORKTREE_PATH = ROOT / "feat" / "001"


@pytest.fixture(autouse=True)
def git_mocks(mocker: MockerFixture):
    mocker.patch("git_workspace.git.add_worktree")
    mocker.patch("git_workspace.git.add_worktree_tracking_remote")
    mocker.patch("git_workspace.git.add_worktree_new_branch")


# --- resume_worktree ---

def test_resume_returns_worktree_result_with_is_new_false() -> None:
    result = workspace.resume_worktree(WORKTREE_PATH)

    assert result == WorktreeResult(path=WORKTREE_PATH, is_new=False)


def test_resume_does_not_call_git(mocker: MockerFixture) -> None:
    add_mock = mocker.patch("git_workspace.git.add_worktree")

    workspace.resume_worktree(WORKTREE_PATH)

    add_mock.assert_not_called()


# --- create_worktree_from_local ---

def test_create_from_local_returns_canonical_path() -> None:
    result = workspace.create_worktree_from_local(ROOT, BRANCH)

    assert result == WorktreeResult(path=WORKTREE_PATH, is_new=True)


def test_create_from_local_invokes_git_correctly(mocker: MockerFixture) -> None:
    add_mock = mocker.patch("git_workspace.git.add_worktree")

    workspace.create_worktree_from_local(ROOT, BRANCH)

    add_mock.assert_called_once_with(WORKTREE_PATH, BRANCH)


def test_create_from_local_propagates_worktree_creation_error(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.add_worktree", side_effect=WorktreeCreationError("fail"))

    with pytest.raises(WorktreeCreationError):
        workspace.create_worktree_from_local(ROOT, BRANCH)


# --- create_worktree_from_remote ---

def test_create_from_remote_returns_canonical_path() -> None:
    result = workspace.create_worktree_from_remote(ROOT, BRANCH)

    assert result == WorktreeResult(path=WORKTREE_PATH, is_new=True)


def test_create_from_remote_invokes_git_correctly(mocker: MockerFixture) -> None:
    add_mock = mocker.patch("git_workspace.git.add_worktree_tracking_remote")

    workspace.create_worktree_from_remote(ROOT, BRANCH)

    add_mock.assert_called_once_with(WORKTREE_PATH, BRANCH)


def test_create_from_remote_propagates_worktree_creation_error(mocker: MockerFixture) -> None:
    mocker.patch(
        "git_workspace.git.add_worktree_tracking_remote",
        side_effect=WorktreeCreationError("fail"),
    )

    with pytest.raises(WorktreeCreationError):
        workspace.create_worktree_from_remote(ROOT, BRANCH)


# --- create_worktree_from_base ---

def test_create_from_base_returns_canonical_path() -> None:
    result = workspace.create_worktree_from_base(ROOT, BRANCH, BASE)

    assert result == WorktreeResult(path=WORKTREE_PATH, is_new=True)


def test_create_from_base_invokes_git_correctly(mocker: MockerFixture) -> None:
    add_mock = mocker.patch("git_workspace.git.add_worktree_new_branch")

    workspace.create_worktree_from_base(ROOT, BRANCH, BASE)

    add_mock.assert_called_once_with(WORKTREE_PATH, BRANCH, BASE)


def test_create_from_base_propagates_worktree_creation_error(mocker: MockerFixture) -> None:
    mocker.patch(
        "git_workspace.git.add_worktree_new_branch",
        side_effect=WorktreeCreationError("fail"),
    )

    with pytest.raises(WorktreeCreationError):
        workspace.create_worktree_from_base(ROOT, BRANCH, BASE)
